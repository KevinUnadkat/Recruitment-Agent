# Recruitment AI Agent

This project implements a Recruitment AI Agent using FastAPI for the backend and Streamlit for the frontend. It helps HR professionals streamline the hiring process by automating job description generation, resume matching, and email communication.

# Features
Job Description Input:

Generate JDs using Gemini based on job title, experience, skills, company, employment type, industry, and location.

Upload JD files (PDF, DOCX, TXT).

Paste JD text directly.

Resume Upload & Candidate Matching:

Upload multiple resumes (PDF, DOCX, TXT).

AI-powered scoring (0-100) comparing resumes to the JD.

Display of score, missing skills, and remarks for each candidate.

Highlights the best-matched candidate.

Automated Email Generation:

Generates personalized interview invitation emails for accepted candidates (based on a configurable score threshold).

Generates empathetic rejection emails for other candidates.

🔧 Setup Instructions
Clone the repository:

git clone https://github.com/KevinUnadkat/recruitment-agent.git

Create a virtual environment and activate it (recommended):

python -m venv venv
# On Windows
.\venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

Install dependencies:
pip install -r requirements.txt

Set up Google Gemini API Key:

Obtain your API key from Google AI Studio.

Set it as an environment variable:

export GOOGLE_API_KEY="YOUR_GEMINI_API_KEY"
# For Windows
use `set GOOGLE_API_KEY=YOUR_GEMINI_API_KEY`

Alternatively, you can directly set GEMINI_API_KEY in main.py, but using environment variables is recommended for security.

🚀 How to Run Locally
Start the FastAPI Backend:
Open your terminal, navigate to the project directory, and run:

uvicorn main:app --reload --host 0.0.0.0 --port 8000

The backend will be accessible at http://127.0.0.1:8000. You can view the API documentation at http://127.0.0.1:8000/docs.

Start the Streamlit Frontend:
Open another terminal, navigate to the project directory, and run:

streamlit run app.py

The Streamlit app will open in your web browser, typically at http://localhost:8501.

🔍 AI Logic and Model Choices
This project leverages Google Gemini for its core AI functionalities, specifically using the gemini-2.0-flash model.

Job Description Generation:

The _jd_prompt function in main.py crafts a detailed prompt for Gemini, instructing it to act as an expert HR recruiter and technical writer.

It specifies the required headings, tone, length, and incorporates all user-provided inputs (job title, experience, skills, etc.).

Why Gemini-2.0-Flash? Chosen for its balance of performance (fast response times suitable for interactive generation), cost-effectiveness, and strong text generation capabilities to produce coherent and professionally formatted job descriptions.

Resume Matching and Scoring:

The _scoring_prompt function in main.py takes both the Job Description and the resume text.

It guides Gemini to act as an expert technical recruiter and output a JSON object containing a score (0-100), missing_skills, and remarks.

A regular expression is used to robustly extract the JSON object from Gemini's response.

Why Gemini-2.0-Flash? Its ability to follow strict JSON output instructions and accurately compare two substantial text inputs (JD and resume) is crucial. The model's accuracy in identifying skill matches and gaps directly impacts the quality of the candidate evaluation.

Email Generation (Acceptance/Rejection):

The _email_prompt function in main.py dynamically creates prompts based on whether an acceptance or rejection email is needed.

It provides context such as candidate name, role, company, interview details (for invites), and specifies the desired tone and length.

Why Gemini-2.0-Flash? Its versatility in generating natural, empathetic, or professional text, combined with the ability to adhere to length constraints and specific instructions, makes it ideal for crafting personalized and appropriate emails.

🧪 Example JD and Resume Files
To test the application, you can use:

Example JD:
You can use the "Generate JD (Gemini)" option in the Streamlit frontend with sample inputs like:

Job Title: Machine Learning Engineer

Years of Experience: 3

Must-have Skills: Python, PyTorch, AWS, Docker, Kubernetes

Company: Tech Innovations Inc.

Example Resumes:
You will need to provide sample PDF, DOCX, or TXT resume files. For quick testing, you can create simple .txt files containing relevant skills and experience.

Example candidate_a.txt (strong match):

Kevin Unadkat
Experience: 3 years as AI/ML Engineer. Proficient in Python, PyTorch, and TensorFlow.
Hands-on experience with AWS services like S3, EC2, and SageMaker.
Successfully deployed models using Docker and Kubernetes.

Example candidate_b.txt (weak match):

K.Unadkat
Experience: 1 years as Data Analyst. Skilled in SQL, Excel, and Tableau.
Basic Python knowledge. No experience with cloud platforms or model deployment.
