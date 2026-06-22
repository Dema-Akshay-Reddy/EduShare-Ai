"""
data_generator.py
Generates a realistic synthetic dataset to seed the platform on first run:
- student profiles across departments/semesters
- resource listings (textbooks, calculators, lab kits, etc.)
- a demand_history table covering the past 12 months, used to train the
  ML demand-forecasting model
- a handful of past transactions, so the sustainability dashboard has data
  to show immediately

This also exports a CSV snapshot of resources (data/resources.csv) since the
spec calls for CSV as a dataset format alongside SQLite.
"""

import random
import os
import csv
from datetime import date

import database as db
from constants import (
    DEPARTMENTS, CATEGORIES, CONDITIONS, AVERAGE_PRICE,
)

random.seed(42)

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Ananya", "Diya", "Saanvi", "Aadhya", "Myra", "Anika",
    "Riya", "Kavya", "Ira", "Navya", "Rohan", "Karthik", "Meera", "Sneha",
    "Pooja", "Rahul", "Sanjay", "Divya", "Nikhil", "Priya",
]
LAST_NAMES = [
    "Sharma", "Verma", "Iyer", "Gupta", "Patel", "Reddy", "Nair", "Rao",
    "Singh", "Mehta", "Joshi", "Kumar", "Das", "Pillai", "Chatterjee", "Bose",
]

ITEM_NAMES_BY_CATEGORY = {
    "Textbook": [
        "Engineering Mathematics Textbook", "Engineering Physics Textbook",
        "Basic Electronics Textbook", "Data Structures Textbook",
        "Thermodynamics Textbook", "Strength of Materials Textbook",
        "Digital Logic Design Textbook", "Surveying Textbook",
        "Circuit Theory Textbook", "Object Oriented Programming Textbook",
    ],
    "Calculator": [
        "Scientific Calculator (fx-991ES)", "Graphing Calculator",
        "Basic Scientific Calculator",
    ],
    "Lab Kit": [
        "Basic Electronics Lab Kit", "Digital Electronics Lab Kit",
        "Chemistry Lab Kit", "Physics Lab Kit", "Surveying Instrument Kit",
        "Microcontroller Lab Kit",
    ],
    "Drawing Instrument": [
        "Engineering Drawing Kit", "Drafter & Drawing Board Set",
        "Geometry Compass Set",
    ],
    "Stationery": [
        "Graph Sheets Pack", "Lab Record Notebook Set", "Drawing Sheets Pack",
        "Stationery Combo Pack",
    ],
    "Lab Coat / Apron": [
        "Lab Coat (Size M)", "Lab Coat (Size L)", "Chemistry Apron",
    ],
    "Other": [
        "USB Drive 16GB", "Drafting Table Lamp", "Lab Safety Goggles",
    ],
}

DESCRIPTION_TEMPLATES = [
    "Used for one semester, {condition_phrase}. No missing pages/parts.",
    "Barely used, {condition_phrase}. Selling/donating as I no longer need it.",
    "{condition_phrase}, all accessories included. Great for incoming students.",
    "Inherited from a senior, now passing it on. {condition_phrase}.",
    "Bought new but switched electives, {condition_phrase} and unused since.",
]

CONDITION_PHRASES = {
    "New": "still in original packaging",
    "Like New": "looks practically unused",
    "Good": "minor cosmetic wear only",
    "Fair": "functional with some visible wear",
    "Worn": "well used but fully functional",
}


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def generate_students(n=60):
    students = []
    for _ in range(n):
        name = random_name()
        dept = random.choice(DEPARTMENTS)
        sem = random.randint(1, 8)
        interests = random.sample(
            [c for c in CATEGORIES], k=random.randint(1, 3)
        )
        students.append((name, dept, sem, ", ".join(interests)))
    return students


def generate_resources(n=90):
    resources = []
    today = date.today()
    for _ in range(n):
        category = random.choice(CATEGORIES)
        item_name = random.choice(ITEM_NAMES_BY_CATEGORY[category])
        department = random.choice(DEPARTMENTS)
        semester = random.randint(1, 8)
        condition = random.choices(
            CONDITIONS, weights=[10, 25, 35, 20, 10]
        )[0]
        condition_phrase = CONDITION_PHRASES[condition]
        description = random.choice(DESCRIPTION_TEMPLATES).format(condition_phrase=condition_phrase)
        availability_status = random.choices(
            ["Available", "Reserved", "Exchanged"], weights=[65, 10, 25]
        )[0]
        uploader_name = random_name()
        base_price = AVERAGE_PRICE.get(category, 300)
        condition_factor = {"New": 1.0, "Like New": 0.9, "Good": 0.75, "Fair": 0.55, "Worn": 0.35}[condition]
        estimated_value = round(base_price * condition_factor, 2)
        resources.append((
            item_name, category, department, semester, condition, description,
            availability_status, uploader_name, estimated_value,
        ))
    return resources


def generate_demand_history():
    """
    Builds 12 months of historical 'request counts' per category/department,
    with realistic seasonal spikes around semester start (Jan/Feb and Jul/Aug)
    so the ML model has genuine signal to learn from.
    """
    records = []
    months = list(range(1, 13))
    year = date.today().year - 1
    for category in CATEGORIES:
        base_popularity = {
            "Textbook": 40, "Calculator": 25, "Lab Kit": 20,
            "Drawing Instrument": 15, "Stationery": 30,
            "Lab Coat / Apron": 10, "Other": 8,
        }[category]
        for department in DEPARTMENTS:
            dept_factor = random.uniform(0.6, 1.3)
            for month in months:
                seasonal_factor = 1.8 if month in (1, 2, 7, 8) else 1.0
                noise = random.uniform(0.8, 1.2)
                count = max(0, int(base_popularity * dept_factor * seasonal_factor * noise / len(DEPARTMENTS) * 3))
                records.append((category, department, month, year, count))
    return records


def export_resources_csv(resources_with_ids, path):
    """Export resources to CSV file with error handling and validation."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "item_name", "category", "department", "semester", "condition",
                "description", "availability_status", "uploader_name",
                "estimated_value", "upload_date"
            ])
            for r in resources_with_ids:
                writer.writerow([
                    r["id"], r["item_name"], r["category"], r["department"], r["semester"],
                    r["condition"], r["description"], r["availability_status"],
                    r["uploader_name"], r["estimated_value"], r["upload_date"]
                ])
        print(f"✅ CSV exported successfully to {path} ({len(resources_with_ids)} resources)")
        return True
    except IOError as e:
        print(f"❌ CSV export failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during CSV export: {e}")
        return False


def refresh_resources_csv():
    """Re-export ALL resources from the DB to the CSV file.
    Call this whenever the resources table changes (upload, exchange status
    update, etc.) so the CSV stays in sync with SQLite at all times."""
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "resources.csv")
    resources = db.get_all_resources()
    if resources:
        export_resources_csv(resources, csv_path)
    else:
        print("⚠️  No resources to export to CSV")


def seed_database():
    """Populate the DB with synthetic data only if it's currently empty."""
    db.init_db()
    if db.is_db_seeded():
        return False

    for name, dept, sem, interests in generate_students(60):
        db.add_student(name, dept, sem, interests)

    for item_name, category, department, semester, condition, description, status, uploader, value in generate_resources(90):
        db.add_resource(item_name, category, department, semester, condition,
                         description, status, uploader, value)

    for category, department, month, year, count in generate_demand_history():
        db.add_demand_record(category, department, month, year, count)

    # Seed a handful of past transactions for exchanged resources so the
    # sustainability dashboard has real history to display immediately.
    all_resources = db.get_all_resources()
    students = db.get_all_students()
    for r in all_resources:
        if r["availability_status"] == "Exchanged":
            recipient = random.choice(students)["name"]
            db.record_transaction(r["id"], recipient, r["estimated_value"])

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "resources.csv")
    export_resources_csv(db.get_all_resources(), csv_path)

    return True


if __name__ == "__main__":
    seeded = seed_database()
    print("Database seeded." if seeded else "Database already had data; skipped seeding.")
