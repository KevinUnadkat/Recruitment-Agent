import os
import io
import re
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pdfplumber
import docx
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from google import genai

GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyCoU_9DYVPSwxMUr7JW9ISJSzGNh2nN4TE")
GEMINI_MODEL = "gemini-2.0-flash"  

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="Recruitment Agent",
              description="JD Generation, Resume Scoring, and Email Generation.",
              version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True)


class JDGenerateRequest(BaseModel):
    title: str
    experience: int
    skills: str
    company: str
    employment_type: Optional[str] = "Full-time"
    industry: Optional[str] = ""
    location: Optional[str] = ""

class EmailRequest(BaseModel):
    candidate_name: str
    job_title: str
    jd_text: str
    company: str
    status: str  
    interview_date: Optional[str] = None
    location: Optional[str] = None


def _read_upload_text(up: UploadFile) -> str:
    content = up.file.read()
    fname = (up.filename or "").lower()
    try:
        if fname.endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                texts = [p.extract_text() or "" for p in pdf.pages]
                return "\n".join(texts)
        elif fname.endswith((".docx", ".doc")):
            doc = docx.Document(io.BytesIO(content))
            return "\n".join([p.text for p in doc.paragraphs])
        else:
            return content.decode("utf-8", errors="ignore")
    finally:
        try:
            up.file.close()
        except Exception:
            pass

def _shorten(text: str, max_chars: int = 2500) -> str:
    text = text or ""
    if len(text) <= max_chars:
        return text
    
    return text[:max_chars].rsplit("\n", 1)[0]


def _gemini_generate(prompt: str, max_output_tokens: int = 512, temperature: float = 0.6) -> str:
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": max_output_tokens
            }
        )
        return (resp.text or "").strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {e}")


def _jd_prompt(req: JDGenerateRequest) -> str:
    return f"""
You are an expert HR recruiter and technical writer. Produce a polished, inclusive, SEO-friendly job description in Markdown.
Use the inputs below. The output MUST contain these headings in order: "## Company Overview", "## Role Overview", "## Key Responsibilities", "## Required Qualifications", "## Preferred Qualifications", "## Benefits".
Responsibilities: 6-10 bullet points. Required Qualifications: concrete skills and years. Tone: professional and engaging. Length: ~250-400 words.

Inputs:
Job Title: {req.title}
Experience (years): {req.experience}
Must-have Skills: {req.skills}
Company: {req.company}
Employment Type: {req.employment_type}
Industry: {req.industry}
Location: {req.location}

Write the job description now in Markdown using the required headings."""

def _scoring_prompt(jd_text: str, resume_text: str) -> str:
    # Ask Gemini to compare JD and resume and output JSON only
    jd_trim = _shorten(jd_text, 2500)
    res_trim = _shorten(resume_text, 2500)
    return f"""
You are an expert technical recruiter. Given the Job Description (JD) and a candidate's resume text, evaluate how well the candidate fits the JD.

Instructions:
- Read the JD and resume.
- Produce a JSON object ONLY (no extra commentary) with these keys:
  - "score": integer between 0 and 100 representing fit (100 = perfect fit).
  - "missing_skills": an array of strings listing important JD skills/requirements not found in the resume (max 20).
  - "remarks": a short string (1-2 sentences) summarizing strengths/weaknesses and suggested fit level.

Evaluation guidance:
- Consider technical skills, experience level, role fit, and relevant keywords.
- Be conservative: if something is not clearly present in the resume, consider it missing.
- Use the JD to determine "must-have" vs "nice-to-have".

Provide only valid JSON, example:
{{"score": 78, "missing_skills": ["aws sagemaker", "production monitoring"], "remarks": "Good ML background but lacks specific AWS MLOps experience."}}

JD:
\"\"\"{jd_trim}\"\"\"

Resume:
\"\"\"{res_trim}\"\"\"
"""

def _email_prompt(req: EmailRequest) -> str:
    if req.status == "accept":
        return f"""
Write a short professional interview invitation email. Output only the email text; first line should be the subject.
Candidate: {req.candidate_name}
Role: {req.job_title} at {req.company}
Context: Use the provided JD for context but do not repeat it.
Interview date/time (user-provided): {req.interview_date or 'TBD'}
Location/mode: {req.location or 'Online'}

Tone: Warm, professional, concise. Include what to expect in interview and ask for confirmation. Keep under 180 words."""

    else:
        return f"""
Write a short, empathetic rejection email. Output only the email text; first line should be the subject.
Candidate: {req.candidate_name}
Role: {req.job_title} at {req.company}

Tone: Respectful and encouraging. Thank them for their time; brief reason (e.g., stronger match) and encouragement to apply in future. Keep under 130 words.

"""

@app.get("/health")
def health():
    return {"status": "ok", "gemini_model": GEMINI_MODEL}

@app.post("/generate_jd")
def generate_jd(req: JDGenerateRequest):
    prompt = _jd_prompt(req)
    jd_text = _gemini_generate(prompt, max_output_tokens=900, temperature=0.6)
    return {"job_description": jd_text, "model": GEMINI_MODEL}

@app.post("/match_resumes")
async def match_resumes(
    jd_mode: str = Form(..., description="Either 'file' or 'text'"),
    jd_file: Optional[UploadFile] = File(None),
    jd_text: Optional[str] = Form(None),
    resumes: List[UploadFile] = File(...),
):
    if jd_mode not in {"file", "text"}:
        raise HTTPException(status_code=400, detail="jd_mode must be 'file' or 'text'")
    if jd_mode == "file":
        if not jd_file:
            raise HTTPException(status_code=400, detail="JD file required when jd_mode='file'")
        jd_raw = _read_upload_text(jd_file)
    else:
        if not jd_text or not jd_text.strip():
            raise HTTPException(status_code=400, detail="jd_text is required when jd_mode='text'")
        jd_raw = jd_text

    if not resumes:
        raise HTTPException(status_code=400, detail="At least one resume must be uploaded")
    if len(resumes) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 resumes allowed")

    results = []
    for up in resumes:
        res_text = _read_upload_text(up)
        prompt = _scoring_prompt(jd_raw, res_text)
        try:
            resp_text = _gemini_generate(prompt, max_output_tokens=400, temperature=0.0)
            import json, re

            m = re.search(r"(\{.*\})", resp_text, re.S)
            if not m:
                parsed = json.loads(resp_text)
            else:
                parsed = json.loads(m.group(1))
            score = int(parsed.get("score", 0))
            missing_skills = parsed.get("missing_skills", [])
            remarks = parsed.get("remarks", "") or ""
            
            if not isinstance(missing_skills, list):
                missing_skills = [str(missing_skills)]
        except Exception as e:
            
            score = 0
            missing_skills = []
            remarks = f"Scoring failed: {e}"

        results.append({
            "filename": up.filename,
            "score": score,
            "missing_skills": missing_skills,
            "remarks": remarks
        })


    results.sort(key=lambda x: x["score"], reverse=True)
    best = results[0] if results else None
    return {"matches": results, "best_candidate": best}

@app.post("/generate_email")
def generate_email(req: EmailRequest):
    if req.status not in {"accept", "reject"}:
        raise HTTPException(status_code=400, detail="status must be 'accept' or 'reject'")
    prompt = _email_prompt(req)
    email_text = _gemini_generate(prompt, max_output_tokens=400, temperature=0.6)
    return {"email": email_text, "model": GEMINI_MODEL}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)