# AI-Powered CRM 

CRM lead management with AI help, built with Python, FastAPI, SQLAlchemy, PyMySQL, Streamlit and Groq.


# Streamlit Using Fro Frontend.

## Project structure

# ai crm lead assistant

backend:- 
main.py          # FastAPI routes, error handling
database.py      # MySQL engine, sessions, connection check
models.py        # Lead ORM model
schemas.py       # Pydantic create / update / response schemas
crud.py          # all database operations
ai_service.py    # Groq calls (unchanged)

frontend:- 
app.py

database:-
schema.sql       # creates database + table (safe to re-run)
sample.sql       # OPTIONAL manual demo data (10 leads, idempotent)

.env             # Databases Connection and LLM API

requirements.txt # All Requirements 

README.md



# Step 1  Create Conda environment 
cmd:- 
1. Conda Create -p Crmvenv python=3.12 -y
2. Conda activated CRMvenv/

# Step 2  Install dependencies
cmd:- pip install -r requirements.txt


# Step 3 Create the database
Open MySQL Workbench, or in VS code Connect MySQL with VS code Using MySQL Extenction.


# Step 4 Insert sample leads 
In MySQL Workbench execute of my sample.sql and schema.sql


# Step 5 Configure credentials
.env, set DB_PASSWORD and GROQ_API_KEY

# Step 6 Start the backend

uvicorn backend.main:app --reload


# Step 7 Start the Streamlit frontend

streamlit run frontend/app.py


# Step 8 click to this link when generate after code run
http://127.0.0.1:8000/docs 
http://localhost:8501

