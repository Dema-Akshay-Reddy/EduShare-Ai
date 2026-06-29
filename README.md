# EduShare AI — College Resource Sharing Platform

An AI-powered platform that helps college students share, exchange, donate,
and reuse educational resources (textbooks, calculators, lab kits, drawing
instruments, stationery), using AI to match resources to students, forecast
demand, and quantify sustainability impact.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the URL Streamlit prints (typically `http://localhost:8501`). The
database is created and seeded with realistic synthetic data automatically
on first run — no manual setup required.

## Project Structure

```
.
├── app.py              # Streamlit UI — auth gate + all 7 pages
├── auth.py              # Password hashing, validation, brute-force lockout logic
├── database.py         # SQLite schema + CRUD (resources, students, transactions, search history, demand history, users)
├── data_generator.py   # Seeds synthetic students/resources/demand history; exports data/resources.csv
├── ml_engine.py         # AI core: demand forecasting, AI matching, recommendation engine
├── sustainability.py     # Sustainability impact calculations
├── constants.py          # Shared reference data (departments, categories, pricing, weights)
├── requirements.txt
└── data/
    ├── resource_platform.db   # SQLite database (auto-created)
    └── resources.csv          # CSV snapshot of resource listings
```

## Authentication

The platform is gated behind a sign-in/sign-up screen (`app.py`, rendered via
`auth.py`). Security measures implemented:

- **Password hashing**: PBKDF2-HMAC-SHA256 with 260,000 iterations and a
  unique random 16-byte salt per user (no plaintext passwords are ever
  stored). Verification uses `hmac.compare_digest` for constant-time
  comparison, avoiding timing side-channel attacks.
- **Input validation**: usernames (3-20 chars, alphanumeric + underscore),
  email format, password strength (8+ chars, letter + number required),
  password-confirmation matching, and required-field checks — all enforced
  before any database write, with specific, actionable error messages.
- **Duplicate protection**: `username` and `email` have `UNIQUE` constraints
  at the database level (defense in depth alongside the app-level check),
  and database writes are wrapped in a context manager that guarantees the
  connection closes even on error — so a failed signup attempt can never
  leave the database locked for other users.
- **Brute-force mitigation**: after 5 consecutive failed login attempts,
  an account is locked for 5 minutes. Failed-attempt counts reset on a
  successful login.
- **No username enumeration**: login failures always show a generic
  "Invalid username or password" message, whether the username doesn't
  exist or the password is wrong, so attackers can't probe which usernames
  are registered.
- **SQL injection protection**: every database query uses parameterized
  placeholders (`?`), never string-formatted SQL.

On sign-up, a matching row is also created in the `students` table, so new
users are automatically included as candidates in the AI matching and
recommendation engines.

**Note on scope**: this is demo/project-grade authentication suitable for a
college assignment or internal tool. For a production deployment you would
additionally want: HTTPS everywhere, email verification on signup, a
password-reset flow, server-side session tokens instead of relying solely
on Streamlit's in-memory session state, and a managed database with regular
backups instead of a local SQLite file.

## How Each Objective Is Implemented

**Resource Upload Module** — `app.py` → "Upload Resource" page. Captures item
name, category, department, semester, condition, description, and
availability status, and writes them to the `resources` table. The uploader
is automatically attributed to the signed-in account.

**AI-Based Matching System** — `ml_engine.match_students_for_resource()`.
When a resource is uploaded, every student profile is scored using a blend
of: department match, semester proximity (next-cohort students score
highest), a "shared first-year" rule for foundational items like drawing
kits across engineering branches, and TF-IDF text similarity between the
resource description and student interests. Results are grouped into
human-readable segments (e.g. "First-Year Mechanical Engineering Students").

**Recommendation Engine** — `ml_engine.recommend_resources_for_student()`.
Content-based filtering: builds a TF-IDF vector for every available
resource (name + category + department + description) and for the
student's profile (department + interests + recent searches), then ranks
resources by cosine similarity plus department/semester relevance.

**Demand Prediction Module** — `ml_engine.DemandPredictor`. A
`RandomForestRegressor` trained on 12 months of synthetic historical
request counts per category/department (with realistic semester-start
seasonality) forecasts next month's request volume per category, labeled
Low/Medium/High using quantile cuts.

**Sustainability Impact Calculator** — `sustainability.py`. Aggregates
completed transactions into money saved, resources reused, waste reduced
(kg, via per-category average weight), and estimated CO₂ avoided (kg).

**Analytics Dashboard** — `app.py` → "Analytics Dashboard" page. Matplotlib
charts for most-demanded resources, department-wise usage, and exchange
volume over time, plus a full listings table.

## Notes on the Data

Since this is a fresh platform with no real transaction history yet, a
synthetic but realistic dataset (`data_generator.py`) seeds: 60 student
profiles across 8 departments/semesters, 90 resource listings across all
categories and conditions, 12 months of historical demand records (used
purely to train the forecasting model), and ~24 completed transactions so
the Sustainability and Analytics pages have real data to display
immediately. The database only seeds once — your own uploads and exchanges
persist normally after that. Delete `data/resource_platform.db` to reset
and reseed.

## Extending This Project

- **NLP on descriptions**: swap the TF-IDF vectorizer for sentence
  embeddings (e.g. `sentence-transformers`) for stronger semantic matching.
- **Generative AI assistant**: add a chat page that calls an LLM API with
  the resource catalog as context to answer "where can I find X" questions.
- **Real notifications**: replace the simulated notification message with
  actual email/SMS integration once user accounts exist.
- **Power BI**: export `data/resources.csv` and a transactions CSV for use
  as a Power BI data source, per the optional visualization stack.
