"""
sustainability.py
Computes the platform's sustainability impact metrics from completed
transactions: money saved, resources reused, waste reduced (kg), and
estimated CO2 emissions avoided.
"""

import database as db
from constants import AVERAGE_WEIGHT_KG, CO2_PER_KG


def compute_impact_metrics():
    transactions = db.get_all_transactions()

    total_reused = len(transactions)
    total_money_saved = sum(t["money_saved"] for t in transactions)

    total_waste_kg = 0.0
    for t in transactions:
        weight = AVERAGE_WEIGHT_KG.get(t["category"], 0.3)
        total_waste_kg += weight

    total_co2_kg = total_waste_kg * CO2_PER_KG

    return {
        "total_reused": total_reused,
        "total_money_saved": round(total_money_saved, 2),
        "total_waste_kg": round(total_waste_kg, 2),
        "total_co2_kg": round(total_co2_kg, 2),
    }


def compute_impact_by_category():
    transactions = db.get_all_transactions()
    summary = {}
    for t in transactions:
        cat = t["category"]
        if cat not in summary:
            summary[cat] = {"count": 0, "money_saved": 0.0, "waste_kg": 0.0}
        summary[cat]["count"] += 1
        summary[cat]["money_saved"] += t["money_saved"]
        summary[cat]["waste_kg"] += AVERAGE_WEIGHT_KG.get(cat, 0.3)
    return summary


def compute_impact_by_department():
    transactions = db.get_all_transactions()
    summary = {}
    for t in transactions:
        dept = t["department"]
        if dept not in summary:
            summary[dept] = {"count": 0, "money_saved": 0.0}
        summary[dept]["count"] += 1
        summary[dept]["money_saved"] += t["money_saved"]
    return summary
