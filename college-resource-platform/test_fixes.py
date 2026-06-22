import csv

from data_generator import export_resources_csv


def test_resource_export_writes_csv_snapshot(tmp_path):
    csv_path = tmp_path / "resources.csv"
    resources = [
        {
            "id": 1,
            "item_name": "Python Programming Textbook",
            "category": "Textbook",
            "department": "Computer Science",
            "semester": 2,
            "condition": "Good",
            "description": "Clean copy",
            "availability_status": "Available",
            "uploader_name": "Test User",
            "estimated_value": 500.0,
            "upload_date": "2026-06-22",
        }
    ]

    assert export_resources_csv(resources, csv_path) is True

    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows[0]["item_name"] == "Python Programming Textbook"
    assert rows[0]["availability_status"] == "Available"
