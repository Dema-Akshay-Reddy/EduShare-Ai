"""
constants.py
Shared reference data used across the platform: departments, resource
categories, condition levels, and the department-progression map used by
the AI matching engine (e.g. who "comes after" whom for hand-me-down items).
"""

DEPARTMENTS = [
    "Mechanical Engineering",
    "Civil Engineering",
    "Electrical Engineering",
    "Electronics & Communication",
    "Computer Science",
    "Information Technology",
    "Chemical Engineering",
    "General / First-Year",
]

CATEGORIES = [
    "Textbook",
    "Calculator",
    "Lab Kit",
    "Drawing Instrument",
    "Stationery",
    "Lab Coat / Apron",
    "Other",
]

CONDITIONS = ["New", "Like New", "Good", "Fair", "Worn"]

SEMESTERS = list(range(1, 9))

AVAILABILITY_STATUSES = ["Available", "Reserved", "Exchanged"]

# Average new-purchase price per category (INR) used to estimate money saved
AVERAGE_PRICE = {
    "Textbook": 650,
    "Calculator": 1200,
    "Lab Kit": 900,
    "Drawing Instrument": 450,
    "Stationery": 150,
    "Lab Coat / Apron": 500,
    "Other": 300,
}

# Approximate physical weight per category (kg) used for waste-reduction estimates
AVERAGE_WEIGHT_KG = {
    "Textbook": 0.6,
    "Calculator": 0.2,
    "Lab Kit": 1.5,
    "Drawing Instrument": 0.4,
    "Stationery": 0.1,
    "Lab Coat / Apron": 0.3,
    "Other": 0.3,
}

# kg of CO2 emissions avoided per kg of material not newly manufactured
# (rough illustrative factor for paper/plastic/mixed educational goods)
CO2_PER_KG = 2.1

# Categories most relevant to first-year / foundation students regardless
# of specific department (drawing kits, basic calculators, foundation texts)
FIRST_YEAR_RELEVANT_CATEGORIES = {"Drawing Instrument", "Calculator", "Lab Coat / Apron", "Stationery"}

# Departments that commonly share first-year engineering drawing / workshop content
SHARED_FIRST_YEAR_DEPARTMENTS = [
    "Mechanical Engineering",
    "Civil Engineering",
    "Electrical Engineering",
    "Electronics & Communication",
]
