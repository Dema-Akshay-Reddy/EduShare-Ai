"""
app.py
AI-Powered College Resource Sharing Platform
Streamlit front-end wiring together the database, ML engine, and
sustainability calculator modules.

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
from datetime import date

import database as db
import ml_engine as ml
import sustainability as sus
import auth
from data_generator import seed_database, refresh_resources_csv
from constants import DEPARTMENTS, CATEGORIES, CONDITIONS, SEMESTERS, AVERAGE_PRICE

st.set_page_config(
    page_title="EduShare AI | College Resource Sharing Platform",
    page_icon="🎓",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Setup (runs once per session start; idempotent)
# ---------------------------------------------------------------------------
db.init_db()
seed_database()

@st.cache_resource
def get_demand_predictor():
    predictor = ml.DemandPredictor()
    predictor.train()
    return predictor

predictor = get_demand_predictor()

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None
if "current_student" not in st.session_state:
    st.session_state.current_student = None
if "search_terms" not in st.session_state:
    st.session_state.search_terms = []
if "flash" not in st.session_state:
    st.session_state.flash = None

# Browse filter state — stored explicitly so we can programmatically reset them
# (e.g. after an upload) rather than relying on Streamlit's auto-keyed widget state.
if "browse_filter_category" not in st.session_state:
    st.session_state.browse_filter_category = "All"
if "browse_filter_department" not in st.session_state:
    st.session_state.browse_filter_department = "All"
if "browse_filter_semester" not in st.session_state:
    st.session_state.browse_filter_semester = "All"
if "browse_search_query" not in st.session_state:
    st.session_state.browse_search_query = ""
# ID of the most recently uploaded resource so Browse can highlight it
if "last_uploaded_id" not in st.session_state:
    st.session_state.last_uploaded_id = None


def log_in_user(user_row):
    """Populate session state for a successfully authenticated user."""
    st.session_state.auth_user = user_row
    st.session_state.current_student = db.get_student_by_id(user_row["student_id"])


def log_out_user():
    st.session_state.auth_user = None
    st.session_state.current_student = None
    st.session_state.search_terms = []


# ---------------------------------------------------------------------------
# Authentication gate — nothing below renders until the user signs in
# ---------------------------------------------------------------------------
if st.session_state.auth_user is None:
    st.title("🎓 EduShare AI")
    st.markdown(
        "##### AI-Powered College Resource Sharing Platform\n"
        "Sign in to share, find, and reuse textbooks, calculators, lab kits, "
        "and more with fellow students."
    )

    if st.session_state.flash:
        kind, message = st.session_state.flash
        getattr(st, kind)(message)
        st.session_state.flash = None

    left, mid, right = st.columns([1, 2, 1])
    with mid:
        with st.container(border=True):
            tab_signin, tab_signup = st.tabs(["🔑 Sign In", "📝 Sign Up"])

            # ----------------------------- SIGN IN -----------------------------
            with tab_signin:
                st.caption("Welcome back — enter your credentials to continue.")
                with st.form("signin_form"):
                    si_username = st.text_input("Username")
                    si_password = st.text_input("Password", type="password")
                    si_submit = st.form_submit_button("Sign In", width='stretch')

                if si_submit:
                    if not si_username or not si_password:
                        st.error("Please enter both your username and password.")
                    else:
                        user = db.get_user_by_username(si_username.strip())
                        if user is None:
                            # Generic message — never reveal whether the
                            # username exists, to prevent account enumeration.
                            st.error("Invalid username or password.")
                        else:
                            locked, lock_msg = auth.is_locked(user)
                            if locked:
                                st.error(lock_msg)
                            elif auth.verify_password(si_password, user["password_hash"], user["salt"]):
                                db.record_login_success(user["id"])
                                log_in_user(db.get_user_by_username(si_username.strip()))
                                st.session_state.flash = ("success", f"Welcome back, {user['full_name']}!")
                                st.rerun()
                            else:
                                new_count = (user["failed_attempts"] or 0) + 1
                                if new_count >= auth.MAX_FAILED_ATTEMPTS:
                                    db.record_login_failure(user["id"], lock_until=auth.compute_lockout_until())
                                    st.error(
                                        f"Invalid username or password. Account locked for "
                                        f"{auth.LOCKOUT_MINUTES} minutes after too many failed attempts."
                                    )
                                else:
                                    db.record_login_failure(user["id"])
                                    st.error("Invalid username or password.")

            # ----------------------------- SIGN UP -----------------------------
            with tab_signup:
                st.caption("Create an account to start sharing and finding resources.")
                with st.form("signup_form"):
                    su_full_name = st.text_input("Full Name", placeholder="e.g. Aarav Sharma")
                    su_username = st.text_input("Username", placeholder="3-20 characters: letters, numbers, underscore")
                    su_email = st.text_input("Email", placeholder="you@college.edu")
                    c1, c2 = st.columns(2)
                    with c1:
                        su_password = st.text_input("Password", type="password")
                    with c2:
                        su_confirm = st.text_input("Confirm Password", type="password")
                    su_dept = st.selectbox("Department", DEPARTMENTS)
                    su_sem = st.selectbox("Semester", SEMESTERS)
                    su_interests = st.multiselect("Interests (helps with matching & recommendations)", CATEGORIES)
                    st.caption("Password must be at least 8 characters and include a letter and a number.")
                    su_submit = st.form_submit_button("Create Account", width='stretch')

                if su_submit:
                    errors = []
                    ok, msg = auth.validate_full_name(su_full_name)
                    if not ok:
                        errors.append(msg)
                    username_clean = su_username.strip()
                    ok, msg = auth.validate_username(username_clean)
                    if not ok:
                        errors.append(msg)
                    email_clean = su_email.strip().lower()
                    ok, msg = auth.validate_email(email_clean)
                    if not ok:
                        errors.append(msg)
                    ok, msg = auth.validate_password_strength(su_password)
                    if not ok:
                        errors.append(msg)
                    if su_password != su_confirm:
                        errors.append("Passwords do not match.")
                    if not errors and db.get_user_by_username(username_clean):
                        errors.append("That username is already taken.")
                    if not errors and db.get_user_by_email(email_clean):
                        errors.append("An account with that email already exists.")

                    if errors:
                        for e in errors:
                            st.error(e)
                    else:
                        try:
                            interests_str = ", ".join(su_interests)
                            student_id = db.add_student(su_full_name.strip(), su_dept, su_sem, interests_str)
                            pw_hash, salt = auth.hash_password(su_password)
                            db.create_user(
                                username_clean, email_clean, pw_hash, salt, su_full_name.strip(),
                                su_dept, su_sem, interests_str, student_id
                            )
                            new_user = db.get_user_by_username(username_clean)
                            db.record_login_success(new_user["id"])
                            log_in_user(new_user)
                            st.session_state.flash = ("success", f"Account created — welcome, {su_full_name.strip()}!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("That username or email is already registered. Please sign in instead.")

    st.stop()

current_user = st.session_state.auth_user

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.title("🎓 EduShare AI")
st.sidebar.caption("Sustainable reuse of educational resources")

page = st.sidebar.radio(
    "Navigate",
    [
        "🏠 Home",
        "📤 Upload Resource",
        "🔎 Browse & AI Matching",
        "✨ Recommendations",
        "📈 Demand Prediction",
        "🌱 Sustainability Impact",
        "📊 Analytics Dashboard",
    ],
)

st.sidebar.divider()
st.sidebar.subheader("Your Profile")
st.sidebar.markdown(f"**{current_user['full_name']}**")
st.sidebar.caption(f"@{current_user['username']} · {current_user['department']} · Sem {current_user['semester']}")
if st.sidebar.button("Log Out", width='stretch'):
    log_out_user()
    st.rerun()

st.sidebar.divider()

if st.session_state.flash:
    kind, message = st.session_state.flash
    getattr(st, kind)(message)
    st.session_state.flash = None
st.sidebar.caption("Flow: Upload → DB → AI Matching → Recommendation → "
                    "Demand Prediction → Notification → Exchange → Impact")


# ===========================================================================
# PAGE: HOME
# ===========================================================================
if page == "🏠 Home":
    st.title("AI-Powered College Resource Sharing Platform")
    st.markdown(
        "##### Promoting Sustainable Reuse of Educational Resources\n"
        "Connecting students with reusable textbooks, calculators, lab kits, "
        "drawing instruments, and stationery — reducing waste and educational "
        "expenses through AI-driven matching and demand forecasting."
    )

    resources = db.get_all_resources()
    transactions = db.get_all_transactions()
    impact = sus.compute_impact_metrics()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Resources Listed", len(resources))
    col2.metric("Currently Available", sum(1 for r in resources if r["availability_status"] == "Available"))
    col3.metric("Resources Reused", impact["total_reused"])
    col4.metric("Money Saved (₹)", f"{impact['total_money_saved']:,.0f}")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("How it works")
        st.markdown(
            "1. **Upload** an unused resource with category, department, and semester.\n"
            "2. The **AI Matching Engine** instantly identifies likely recipients.\n"
            "3. The **Recommendation Engine** surfaces relevant items to students browsing.\n"
            "4. The **Demand Prediction Module** forecasts which items will be needed next.\n"
            "5. Completed exchanges feed the **Sustainability Impact Calculator**."
        )
    with c2:
        st.subheader("Recently listed")
        recent = resources[:6]
        if recent:
            df = pd.DataFrame(recent)[["item_name", "category", "department", "semester", "availability_status"]]
            st.dataframe(df, hide_index=True, width='stretch')
        else:
            st.info("No resources listed yet — be the first to upload one!")


# ===========================================================================
# PAGE: UPLOAD RESOURCE
# ===========================================================================
elif page == "📤 Upload Resource":
    st.title("📤 Resource Upload Module")
    st.caption(f"Posting as **{current_user['full_name']}** (@{current_user['username']})")

    with st.form("upload_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            item_name = st.text_input("Item Name", placeholder="e.g. Engineering Drawing Kit")
            category = st.selectbox("Category", CATEGORIES)
            department = st.selectbox("Department", DEPARTMENTS)
            semester = st.selectbox("Semester", SEMESTERS)
        with col2:
            condition = st.selectbox("Condition", CONDITIONS)
            availability_status = st.selectbox("Availability Status", ["Available", "Reserved"])
            suggested_value = AVERAGE_PRICE.get(category, 300)
            estimated_value = st.number_input(
                "Estimated Value (₹)", min_value=0.0, value=float(suggested_value), step=50.0
            )
        description = st.text_area("Description", placeholder="Condition details, accessories included, etc.")
        submitted = st.form_submit_button("Upload Resource", width='stretch')

    uploader_name = current_user["full_name"]

    if submitted:
        if not item_name:
            st.error("Please enter an item name.")
        else:
            new_id = db.add_resource(
                item_name, category, department, semester, condition,
                description, availability_status, uploader_name, estimated_value
            )

            # ── FIX 1: Refresh the CSV so it stays in sync with the DB ──────
            refresh_resources_csv()

            # ── FIX 2: Reset Browse filters so the new upload is visible ─────
            # Without this, stale filter state (e.g. Category = Drawing Instrument)
            # persists in session and hides newly uploaded resources of other types.
            st.session_state.browse_filter_category = "All"
            st.session_state.browse_filter_department = "All"
            st.session_state.browse_filter_semester = "All"
            st.session_state.browse_search_query = ""
            st.session_state.last_uploaded_id = new_id

            st.success(f"✅ '{item_name}' uploaded successfully (Resource ID #{new_id}).")

            resource = db.get_resource_by_id(new_id)
            matches = ml.match_students_for_resource(resource, top_n=8)
            segments = ml.summarize_recipient_segments(matches)

            st.subheader("🤖 AI Matching Engine — Potential Recipients")
            if segments:
                st.write("Likely recipient segments identified:")
                for seg_name, count in segments:
                    st.markdown(f"- **{seg_name}** ({count} matched student{'s' if count != 1 else ''})")
                st.write("Top individually matched students:")
                match_df = pd.DataFrame(matches)[["name", "department", "semester", "match_score"]]
                match_df.columns = ["Student", "Department", "Semester", "Match Score (%)"]
                st.dataframe(match_df, hide_index=True, width='stretch')
                st.info(f"📣 Notification simulated: {len(matches)} matched students would be notified about this listing.")
            else:
                st.warning("No strong matches found yet — add more student profiles to improve matching.")
            st.info("💡 Your listing is live — head to **Browse & AI Matching** to see it at the top.")


# ===========================================================================
# PAGE: BROWSE & AI MATCHING
# ===========================================================================
elif page == "🔎 Browse & AI Matching":
    st.title("🔎 Browse Resources")
    st.caption("Search available resources and request an exchange.")

    # ── Filter bar ────────────────────────────────────────────────────────────
    # Filters are backed by st.session_state so we can programmatically reset
    # them (e.g. after an upload clears them so the new listing is visible).
    filters_active = (
        st.session_state.browse_filter_category != "All"
        or st.session_state.browse_filter_department != "All"
        or st.session_state.browse_filter_semester != "All"
        or st.session_state.browse_search_query != ""
    )

    f1, f2, f3, f4, f5 = st.columns([2, 2, 1, 2, 1])
    with f1:
        filter_category = st.selectbox(
            "Category", ["All"] + CATEGORIES,
            index=(["All"] + CATEGORIES).index(st.session_state.browse_filter_category),
            key="browse_filter_category",
        )
    with f2:
        filter_department = st.selectbox(
            "Department", ["All"] + DEPARTMENTS,
            index=(["All"] + DEPARTMENTS).index(st.session_state.browse_filter_department),
            key="browse_filter_department",
        )
    with f3:
        filter_semester = st.selectbox(
            "Semester", ["All"] + SEMESTERS,
            index=(["All"] + SEMESTERS).index(st.session_state.browse_filter_semester),
            key="browse_filter_semester",
        )
    with f4:
        search_query = st.text_input(
            "Search keyword",
            value=st.session_state.browse_search_query,
            placeholder="e.g. drawing, calculator...",
            key="browse_search_query",
        )
    with f5:
        st.write("")  # vertical align
        if filters_active:
            if st.button("✖ Clear", help="Reset all filters and show all available resources"):
                st.session_state.browse_filter_category = "All"
                st.session_state.browse_filter_department = "All"
                st.session_state.browse_filter_semester = "All"
                st.session_state.browse_search_query = ""
                st.rerun()

    if filters_active:
        active = []
        if filter_category != "All":
            active.append(f"Category = **{filter_category}**")
        if filter_department != "All":
            active.append(f"Department = **{filter_department}**")
        if filter_semester != "All":
            active.append(f"Semester = **{filter_semester}**")
        if search_query:
            active.append(f"Keyword = **\"{search_query}\"**")
        st.warning(f"⚠️ Filters active: {', '.join(active)}. Recently uploaded resources outside these filters won't appear. Click **✖ Clear** to reset.")

    # ── Fetch and filter ──────────────────────────────────────────────────────
    resources = db.get_all_resources(only_available=True)
    if filter_category != "All":
        resources = [r for r in resources if r["category"] == filter_category]
    if filter_department != "All":
        resources = [r for r in resources if r["department"] == filter_department]
    if filter_semester != "All":
        resources = [r for r in resources if r["semester"] == filter_semester]
    if search_query:
        q = search_query.lower()
        resources = [r for r in resources if q in r["item_name"].lower() or q in (r["description"] or "").lower()]
        db.log_search(current_user["full_name"], search_query)
        st.session_state.search_terms.append(search_query)

    count_label = f"**{len(resources)}** resource(s) found"
    if st.session_state.last_uploaded_id:
        new_visible = any(r["id"] == st.session_state.last_uploaded_id for r in resources)
        if new_visible:
            count_label += " · 🆕 Your new listing is shown below"
        else:
            count_label += " · ⚠️ Your recent upload is hidden by the active filters — click **✖ Clear** to see it"
    st.write(count_label)

    today = date.today().strftime("%Y-%m-%d")

    for r in resources:
        is_new = r["id"] == st.session_state.last_uploaded_id
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                badge = " 🆕 **NEW**" if is_new else ""
                st.markdown(f"**{r['item_name']}**{badge} · {r['category']} · {r['department']} · Sem {r['semester']}")
                st.caption(f"Condition: {r['condition']} | Est. value: ₹{r['estimated_value']:.0f} | Uploaded by {r['uploader_name']} | {r['upload_date']}")
                st.write(r["description"])
            with c2:
                if st.button("View AI Matches", key=f"match_{r['id']}"):
                    st.session_state[f"show_matches_{r['id']}"] = True
                if r["uploader_name"] == current_user["full_name"]:
                    st.caption("This is your own listing.")
                elif st.button("Request Exchange", key=f"exchange_{r['id']}"):
                    db.record_transaction(r["id"], current_user["full_name"], r["estimated_value"])
                    # Keep CSV in sync: status changes Available → Exchanged
                    refresh_resources_csv()
                    st.success(f"Exchange recorded — you get the {r['item_name']}! Money saved: ₹{r['estimated_value']:.0f}")
                    st.rerun()

            if st.session_state.get(f"show_matches_{r['id']}"):
                matches = ml.match_students_for_resource(r, top_n=5)
                segments = ml.summarize_recipient_segments(matches)
                st.markdown("**AI-identified potential recipients:**")
                for seg_name, count in segments:
                    st.markdown(f"- {seg_name} ({count})")


# ===========================================================================
# PAGE: RECOMMENDATIONS
# ===========================================================================
elif page == "✨ Recommendations":
    st.title("✨ Personalized Recommendation Engine")
    st.caption("Content-based filtering using department, semester, interests, and search history.")

    student = st.session_state.current_student
    st.write(f"Showing recommendations for **{student['name']}** "
             f"({student['department']}, Semester {student['semester']}, "
             f"interests: {student['interests'] or 'none set'})")

    history = db.get_search_history(student["name"])
    past_queries = [h["query"] for h in history]

    recs = ml.recommend_resources_for_student(student, search_queries=past_queries, top_n=8)

    if recs:
        df = pd.DataFrame(recs)[["item_name", "category", "department", "semester", "condition", "relevance_score"]]
        df.columns = ["Item", "Category", "Department", "Semester", "Condition", "Relevance (%)"]
        st.dataframe(df, hide_index=True, width='stretch')
    else:
        st.warning("No available resources to recommend right now.")


# ===========================================================================
# PAGE: DEMAND PREDICTION
# ===========================================================================
elif page == "📈 Demand Prediction":
    st.title("📈 Demand Prediction Module")
    st.caption("Random Forest model trained on 12 months of historical request data, forecasting next month's demand.")

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    next_month = (date.today().month % 12) + 1
    st.write(f"Forecast target: **{month_names[next_month - 1]}**")

    cat_forecast = predictor.predict_next_month_by_category(next_month)

    if not cat_forecast.empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            fig, ax = plt.subplots(figsize=(7, 4))
            colors = {"High": "#d62728", "Medium": "#ff7f0e", "Low": "#2ca02c"}
            bar_colors = [colors[lvl] for lvl in cat_forecast["demand_level"]]
            ax.barh(cat_forecast["category"], cat_forecast["predicted_requests"], color=bar_colors)
            ax.set_xlabel("Predicted Requests")
            ax.set_title(f"Predicted Demand by Category — {month_names[next_month - 1]}")
            ax.invert_yaxis()
            st.pyplot(fig)
        with c2:
            st.subheader("Predicted High Demand")
            high = cat_forecast[cat_forecast["demand_level"] == "High"]
            for _, row in high.iterrows():
                st.markdown(f"🔴 **{row['category']}** — ~{row['predicted_requests']} requests")
            st.subheader("Medium Demand")
            med = cat_forecast[cat_forecast["demand_level"] == "Medium"]
            for _, row in med.iterrows():
                st.markdown(f"🟠 {row['category']} — ~{row['predicted_requests']} requests")

        st.divider()
        st.subheader("Department-level breakdown")
        dept_forecast = predictor.predict_by_department(next_month)
        pivot = dept_forecast.pivot_table(index="department", columns="category", values="predicted_requests", aggfunc="sum")
        st.dataframe(pivot, width='stretch')
    else:
        st.warning("Not enough historical data to train the demand model yet.")


# ===========================================================================
# PAGE: SUSTAINABILITY IMPACT
# ===========================================================================
elif page == "🌱 Sustainability Impact":
    st.title("🌱 Sustainability Impact Calculator")

    impact = sus.compute_impact_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Resources Reused", impact["total_reused"])
    c2.metric("Money Saved (₹)", f"{impact['total_money_saved']:,.0f}")
    c3.metric("Waste Reduced (kg)", f"{impact['total_waste_kg']:,.1f}")
    c4.metric("CO₂ Avoided (kg)", f"{impact['total_co2_kg']:,.1f}")

    st.caption(
        "Waste and CO₂ figures are illustrative estimates based on average material "
        "weight per resource category and standard emission factors for manufacturing "
        "avoided goods."
    )

    st.divider()
    by_category = sus.compute_impact_by_category()
    if by_category:
        cat_df = pd.DataFrame([
            {"Category": k, "Items Reused": v["count"], "Money Saved (₹)": round(v["money_saved"], 0),
             "Waste Reduced (kg)": round(v["waste_kg"], 1)}
            for k, v in by_category.items()
        ]).sort_values("Items Reused", ascending=False)
        st.subheader("Impact by Category")
        st.dataframe(cat_df, hide_index=True, width='stretch')
    else:
        st.info("No exchanges recorded yet — impact metrics will populate as resources are exchanged.")


# ===========================================================================
# PAGE: ANALYTICS DASHBOARD
# ===========================================================================
elif page == "📊 Analytics Dashboard":
    st.title("📊 Analytics Dashboard")

    resources = db.get_all_resources()
    transactions = db.get_all_transactions()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Items Listed", len(resources))
    c2.metric("Total Items Exchanged", len(transactions))
    c3.metric("Active Listings", sum(1 for r in resources if r["availability_status"] == "Available"))

    st.divider()
    g1, g2 = st.columns(2)

    with g1:
        st.subheader("Most Demanded Resources")
        if transactions:
            tx_df = pd.DataFrame(transactions)
            top_items = tx_df["item_name"].value_counts().head(8)
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.barh(top_items.index[::-1], top_items.values[::-1], color="#1f77b4")
            ax.set_xlabel("Times Exchanged")
            st.pyplot(fig)
        else:
            st.info("No exchange data yet.")

    with g2:
        st.subheader("Department-wise Usage")
        if transactions:
            dept_counts = pd.DataFrame(transactions)["department"].value_counts()
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.pie(dept_counts.values, labels=dept_counts.index, autopct="%1.0f%%", startangle=90,
                    textprops={"fontsize": 8})
            ax2.axis("equal")
            st.pyplot(fig2)
        else:
            st.info("No exchange data yet.")

    st.divider()
    st.subheader("Exchanges Over Time")
    if transactions:
        tx_df = pd.DataFrame(transactions)
        tx_df["exchange_date"] = pd.to_datetime(tx_df["exchange_date"])
        timeline = tx_df.groupby(tx_df["exchange_date"].dt.to_period("M")).size()
        fig3, ax3 = plt.subplots(figsize=(10, 3.5))
        timeline.plot(kind="bar", ax=ax3, color="#2ca02c")
        ax3.set_ylabel("Items Exchanged")
        ax3.set_xlabel("Month")
        st.pyplot(fig3)
    else:
        st.info("No exchange data yet.")

    st.divider()
    st.subheader("All Listings")
    st.dataframe(pd.DataFrame(resources), hide_index=True, width='stretch')
