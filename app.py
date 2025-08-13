import os
import requests
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Recruitment Agent", layout="wide")

BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.title("Recruitment Agent")

with st.expander("Backend status"):
    st.write("Backend:", BACKEND)
    try:
        r = requests.get(f"{BACKEND}/health", timeout=3)
        st.json(r.json())
    except Exception as e:
        st.error(f"Backend not reachable: {e}")

st.markdown("---")


st.header("1) Job Description")
jd_choice = st.radio("Create or provide Job Description", ["Generate JD (Gemini)", "Upload JD file", "Paste JD text"])

if "jd_text" not in st.session_state:
    st.session_state["jd_text"] = ""

if jd_choice == "Generate JD (Gemini)":
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Job Title", "Machine Learning Engineer")
        company = st.text_input("Company", "E2M")
        emp_type = st.text_input("Employment Type", "Full-time")
    with col2:
        experience = st.number_input("Years of Experience", min_value=0, max_value=50, value=2)
        skills = st.text_input("Must-have Skills (comma-separated)", "Python, FastAPI, ML, NLP, Transformers, AWS")
        location = st.text_input("Location", "Ahmedabad, IN")

    if st.button("Generate JD"):
        payload = {
            "title": title,
            "experience": int(experience),
            "skills": skills,
            "company": company,
            "employment_type": emp_type,
            "industry": "",
            "location": location
        }
        try:
            r = requests.post(f"{BACKEND}/generate_jd", json=payload, timeout=180)
            r.raise_for_status()
            st.session_state["jd_text"] = r.json().get("job_description", "")
            st.success("JD generated successfully.")
        except Exception as e:
            st.error(f"JD generation failed: {e}")

    st.subheader("Generated Job Description")
    st.session_state["jd_text"] = st.text_area(
        "You can edit this before matching resumes",
        value=st.session_state.get("jd_text", ""),
        height=350
    )

elif jd_choice == "Upload JD file":
    jd_file = st.file_uploader("Upload JD (.pdf/.docx/.txt)", type=["pdf", "docx", "txt"])
    if jd_file:
        try:
            txt = jd_file.getvalue().decode("utf-8", errors="ignore")
            st.session_state["jd_text"] = txt
            st.text_area("JD preview (editable)", txt, height=350)
        except Exception:
            st.info("JD file uploaded; it will be sent to backend when you match resumes.")

else:  
    st.session_state["jd_text"] = st.text_area(
        "Paste Job Description here",
        value=st.session_state.get("jd_text", ""),
        height=350
    )


st.header("2) Match Resumes to JD")
st.markdown("Upload resumes (PDF/DOCX/TXT). The system will use Gemini to score each resume (0-100).")
resumes = st.file_uploader("Upload resumes (up to 10)", type=["pdf", "docx", "txt"], accept_multiple_files=True)

if st.button("Match Resumes"):
    if not st.session_state.get("jd_text") and jd_choice != "Upload JD file":
        st.error("No JD available. Generate, upload, or paste a JD first.")
    elif jd_choice == "Upload JD file" and (not 'jd_file' in locals() or not jd_file):
        st.error("You selected 'Upload JD file' — please upload a JD file first.")
    elif not resumes:
        st.error("Upload at least one resume.")
    else:
        files = []
        data = {}
        if jd_choice == "Upload JD file":
            data["jd_mode"] = "file"
            files.append(("jd_file", (jd_file.name, jd_file.getvalue(), jd_file.type or "application/octet-stream")))
        else:
            data["jd_mode"] = "text"
            data["jd_text"] = st.session_state.get("jd_text", "")

        for r in resumes:
            files.append(("resumes", (r.name, r.getvalue(), r.type or "application/octet-stream")))

        try:
            with st.spinner("Scoring resumes with Gemini..."):
                resp = requests.post(f"{BACKEND}/match_resumes", data=data, files=files, timeout=600)
                resp.raise_for_status()
                out = resp.json()
        except Exception as e:
            st.error(f"Matching failed: {e}")
            out = None

        if out:
            matches = out.get("matches", [])
            if not matches:
                st.warning("No matches returned.")
            else:
                df = pd.DataFrame(matches)
                st.subheader("Matches (sorted by score)")
                st.dataframe(df[["filename", "score", "missing_skills", "remarks"]].sort_values("score", ascending=False), use_container_width=True)
                st.session_state["last_matches"] = matches
                best = out.get("best_candidate")
                if best:
                    st.success(f"Best candidate: {best['filename']} — Score: {best['score']}")

st.markdown("---")


st.header("3) Generate Email (based on score threshold)")
threshold = st.number_input("Interview threshold (score >= )", min_value=0, max_value=100, value=70)
interview_date = st.text_input("Interview Date/time (for invites)", "")
location = st.text_input("Interview Location / Mode", "Online")

if st.button("Generate Emails for last matches"):
    matches = st.session_state.get("last_matches")
    if not matches:
        st.error("No matching results found. Run matching first.")
    else:
        for m in matches:
            name = m.get("filename", "Candidate")
            score = int(m.get("score", 0))
            status = "accept" if score >= threshold else "reject"
            payload = {
                "candidate_name": name,
                "job_title": " (from JD) ",
                "jd_text": st.session_state.get("jd_text", ""),
                "company": "",
                "status": status,
                "interview_date": interview_date,
                "location": location
            }
            try:
                r = requests.post(f"{BACKEND}/generate_email", json=payload, timeout=180)
                r.raise_for_status()
                email_text = r.json().get("email", "")
                st.subheader(f"{'INVITE' if status=='accept' else 'REJECT'} — {name} (score: {score})")
                st.text_area(f"Email: {name}", value=email_text, height=180)
            except Exception as e:
                st.error(f"Failed to generate email for {name}: {e}")