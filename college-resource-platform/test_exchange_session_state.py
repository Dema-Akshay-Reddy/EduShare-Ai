def test_exchange_state_for_registered_uploader_contains_contact_link():
    exchange = {
        "item_name": "Engineering Mathematics Textbook",
        "uploader_name": "Aarav Sharma",
        "uploader_email": "aarav@example.com",
        "money_saved": 650.00,
        "mailto_link": "mailto:aarav@example.com?subject=Re%3A%20Engineering",
        "sent": True,
        "email_msg": "",
        "has_account": True,
    }

    assert exchange["has_account"] is True
    assert exchange["mailto_link"].startswith("mailto:")
    assert exchange["uploader_email"] in exchange["mailto_link"]


def test_exchange_state_for_seeded_uploader_has_no_contact_link():
    exchange = {
        "item_name": "Lab Kit",
        "money_saved": 900.00,
        "has_account": False,
    }

    assert exchange["has_account"] is False
    assert "uploader_email" not in exchange
    assert "mailto_link" not in exchange
