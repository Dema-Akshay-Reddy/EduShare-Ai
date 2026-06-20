"""
ml_engine.py
The AI core of the platform:

1. Demand Prediction Module
   - Trains a RandomForestRegressor on historical demand_history records
     (category, department, month, seasonality) to forecast next-month
     request volume per category/department, and gives a Low/Medium/High
     demand label.

2. AI-Based Matching System
   - For a newly-uploaded resource, scores every student profile against
     it (department match, semester proximity, first-year-shared-category
     rules, and text similarity between the resource description and the
     student's stated interests) to surface the most likely recipients.

3. Recommendation Engine (content-based filtering)
   - Builds a TF-IDF representation of every available resource's text
     (item name + category + description) and recommends resources to a
     given student profile based on cosine similarity with their
     interests/department/semester/search history.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import database as db
from constants import FIRST_YEAR_RELEVANT_CATEGORIES, SHARED_FIRST_YEAR_DEPARTMENTS


# ---------------------------------------------------------------------------
# 1. Demand Prediction Module
# ---------------------------------------------------------------------------
class DemandPredictor:
    def __init__(self):
        self.model = None
        self.cat_encoder = LabelEncoder()
        self.dept_encoder = LabelEncoder()
        self.is_trained = False

    def _build_features(self, df):
        df = df.copy()
        df["category_enc"] = self.cat_encoder.transform(df["category"])
        df["department_enc"] = self.dept_encoder.transform(df["department"])
        df["is_peak_season"] = df["month"].isin([1, 2, 7, 8]).astype(int)
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
        return df[["category_enc", "department_enc", "month_sin", "month_cos", "is_peak_season"]]

    def train(self):
        records = db.get_demand_history()
        if not records:
            self.is_trained = False
            return
        df = pd.DataFrame(records)

        self.cat_encoder.fit(df["category"].unique())
        self.dept_encoder.fit(df["department"].unique())

        X = self._build_features(df)
        y = df["requests_count"]

        self.model = RandomForestRegressor(n_estimators=150, max_depth=8, random_state=42)
        self.model.fit(X, y)
        self.is_trained = True

    def predict_next_month_by_category(self, next_month):
        """Aggregate predicted demand per category (summed across departments)."""
        if not self.is_trained:
            return pd.DataFrame(columns=["category", "predicted_requests", "demand_level"])

        rows = []
        for category in self.cat_encoder.classes_:
            for department in self.dept_encoder.classes_:
                rows.append({"category": category, "department": department, "month": next_month})
        df = pd.DataFrame(rows)
        X = self._build_features(df)
        df["predicted_requests"] = self.model.predict(X)

        agg = df.groupby("category", as_index=False)["predicted_requests"].sum()
        agg = agg.sort_values("predicted_requests", ascending=False).reset_index(drop=True)
        agg["predicted_requests"] = agg["predicted_requests"].round(0).astype(int)

        # Label demand tiers using simple quantile cuts
        if len(agg) >= 3:
            q1, q2 = agg["predicted_requests"].quantile([0.33, 0.66])
            agg["demand_level"] = agg["predicted_requests"].apply(
                lambda v: "High" if v >= q2 else ("Medium" if v >= q1 else "Low")
            )
        else:
            agg["demand_level"] = "Medium"
        return agg

    def predict_by_department(self, next_month):
        if not self.is_trained:
            return pd.DataFrame(columns=["department", "category", "predicted_requests"])
        rows = []
        for category in self.cat_encoder.classes_:
            for department in self.dept_encoder.classes_:
                rows.append({"category": category, "department": department, "month": next_month})
        df = pd.DataFrame(rows)
        X = self._build_features(df)
        df["predicted_requests"] = self.model.predict(X).round(0).astype(int)
        return df


# ---------------------------------------------------------------------------
# 2. AI-Based Matching System
# ---------------------------------------------------------------------------
def match_students_for_resource(resource, top_n=8):
    """
    Scores each student profile against a newly uploaded resource using a
    blend of rule-based academic relevance and text similarity, returning
    the most likely recipients.

    Scoring components:
      - Department match (same department gets a strong boost)
      - Semester proximity (students one semester behind/at the same level
        are more likely to need the item than students who already passed it)
      - "Shared first-year" rule: foundational items (drawing kits, basic
        calculators, lab coats) are relevant across all first/second-year
        engineering departments regardless of branch
      - Text similarity between resource description/category and the
        student's stated interests (TF-IDF + cosine similarity)
    """
    students = db.get_all_students()
    if not students:
        return []

    texts = [resource["category"] + " " + (resource.get("description") or "") for _ in [0]]
    student_texts = [s.get("interests", "") + " " + s["department"] for s in students]
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        all_text_matrix = vectorizer.fit_transform(texts + student_texts)
        resource_vec = all_text_matrix[0:1]
        student_vecs = all_text_matrix[1:]
        sim_scores = cosine_similarity(resource_vec, student_vecs).flatten()
    except ValueError:
        sim_scores = np.zeros(len(students))

    scored = []
    for student, text_sim in zip(students, sim_scores):
        score = 0.0
        if student["department"] == resource["department"]:
            score += 0.45
        elif resource["category"] in FIRST_YEAR_RELEVANT_CATEGORIES and \
                student["department"] in SHARED_FIRST_YEAR_DEPARTMENTS and \
                resource["department"] in SHARED_FIRST_YEAR_DEPARTMENTS:
            score += 0.30

        sem_diff = student["semester"] - resource["semester"]
        if sem_diff == 0:
            score += 0.25
        elif sem_diff == 1:
            score += 0.20  # the very next cohort to need this material
        elif sem_diff == -1:
            score += 0.05
        else:
            score += max(0, 0.10 - 0.02 * abs(sem_diff))

        score += 0.30 * float(text_sim)

        scored.append({**student, "match_score": round(min(score, 1.0) * 100, 1)})

    scored.sort(key=lambda s: s["match_score"], reverse=True)
    return scored[:top_n]


def summarize_recipient_segments(matched_students):
    """Turns individual matches into the human-readable 'segment' style shown
    in the spec example (e.g. 'First-Year Mechanical Engineering Students')."""
    segments = {}
    for s in matched_students:
        year_label = {1: "First-Year", 2: "First-Year", 3: "Second-Year", 4: "Second-Year",
                      5: "Third-Year", 6: "Third-Year", 7: "Final-Year", 8: "Final-Year"}.get(s["semester"], "")
        key = f"{year_label} {s['department']} Students".strip()
        segments[key] = segments.get(key, 0) + 1
    return sorted(segments.items(), key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------------------------
# 3. Recommendation Engine (content-based filtering)
# ---------------------------------------------------------------------------
def recommend_resources_for_student(student, search_queries=None, top_n=8):
    """
    Content-based filtering: builds a TF-IDF profile of the student
    (department, semester context, interests, recent search queries) and
    matches it against the text of all currently available resources.
    """
    resources = db.get_all_resources(only_available=True)
    if not resources:
        return []

    resource_texts = [
        f"{r['item_name']} {r['category']} {r['department']} {r['description'] or ''}"
        for r in resources
    ]

    search_text = " ".join(search_queries) if search_queries else ""
    student_profile_text = f"{student['interests']} {student['department']} {search_text}"

    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        matrix = vectorizer.fit_transform(resource_texts + [student_profile_text])
        resource_vecs = matrix[:-1]
        student_vec = matrix[-1:]
        sims = cosine_similarity(student_vec, resource_vecs).flatten()
    except ValueError:
        sims = np.zeros(len(resources))

    scored = []
    for r, sim in zip(resources, sims):
        score = 0.5 * float(sim)
        if r["department"] == student["department"]:
            score += 0.3
        sem_diff = abs(r["semester"] - student["semester"])
        score += max(0, 0.2 - 0.04 * sem_diff)
        scored.append({**r, "relevance_score": round(min(score, 1.0) * 100, 1)})

    scored.sort(key=lambda r: r["relevance_score"], reverse=True)
    return scored[:top_n]
