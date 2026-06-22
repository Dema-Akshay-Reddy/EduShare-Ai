from test_exchange_button import build_mailto_link


def test_complete_exchange_flow_uses_isolated_database(isolated_db):
    student_id = isolated_db.add_student(
        name="Aarav Sharma",
        department="Computer Science",
        semester=2,
        interests="Textbook",
    )
    isolated_db.create_user(
        username="aarav",
        email="aarav@example.com",
        password_hash="hash",
        salt="00",
        full_name="Aarav Sharma",
        department="Computer Science",
        semester=2,
        interests="Textbook",
        student_id=student_id,
    )
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
    uploader = isolated_db.get_user_by_full_name("Aarav Sharma")
    link = build_mailto_link(
        uploader_email=uploader["email"],
        uploader_name="Aarav Sharma",
        item_name="Engineering Mathematics Textbook",
        category="Textbook",
        requester_email="student@example.com",
    )

    assert isolated_db.get_resource_by_id(resource_id)["availability_status"] == "Exchanged"
    assert isolated_db.get_all_transactions()[0]["money_saved"] == 650.0
    assert link.startswith("mailto:aarav@example.com")
