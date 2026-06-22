import pytest


def test_request_exchange_records_transaction_and_marks_resource_exchanged(isolated_db):
    resource_id = isolated_db.add_resource(
        item_name="Engineering Mathematics Textbook",
        category="Textbook",
        department="Computer Science",
        semester=2,
        condition="Good",
        description="Clean copy",
        availability_status="Available",
        uploader_name="Aarav Sharma",
        estimated_value=650.0,
    )

    isolated_db.record_transaction(resource_id, "Test Student", 650.0)

    resource = isolated_db.get_resource_by_id(resource_id)
    transactions = isolated_db.get_all_transactions()

    assert resource["availability_status"] == "Exchanged"
    assert len(transactions) == 1
    assert transactions[0]["resource_id"] == resource_id
    assert transactions[0]["recipient_name"] == "Test Student"


def test_request_exchange_rejects_unavailable_resource_without_transaction(isolated_db):
    resource_id = isolated_db.add_resource(
        item_name="Reserved Lab Kit",
        category="Lab Kit",
        department="Electrical Engineering",
        semester=4,
        condition="Like New",
        description="Already reserved",
        availability_status="Reserved",
        uploader_name="Aarav Sharma",
        estimated_value=900.0,
    )

    with pytest.raises(ValueError, match="not available"):
        isolated_db.record_transaction(resource_id, "Test Student", 900.0)

    resource = isolated_db.get_resource_by_id(resource_id)
    assert resource["availability_status"] == "Reserved"
    assert isolated_db.get_all_transactions() == []
