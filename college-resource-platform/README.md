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
├── app.py              # Streamlit UI — all 7 pages
├── database.py         # SQLite schema + CRUD (resources, students, transactions, search history, demand history)
├── data_generator.py   # Seeds synthetic students/resources/demand history; exports data/resources.csv
├── ml_engine.py         # AI core: demand forecasting, AI matching, recommendation engine
├── sustainability.py     # Sustainability impact calculations
├── constants.py          # Shared reference data (departments, categories, pricing, weights)
├── requirements.txt
└── data/
    ├── resource_platform.db   # SQLite database (auto-created)
    └── resources.csv          # CSV snapshot of resource listings
```

## How Each Objective Is Implemented

**Resource Upload Module** — `app.py` → "Upload Resource" page. Captures item
name, category, department, semester, condition, description, and
availability status, and writes them to the `resources` table.

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
