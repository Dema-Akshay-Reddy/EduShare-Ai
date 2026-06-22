from urllib.parse import quote


def build_mailto_link(uploader_email, uploader_name, item_name, category, requester_email):
    subject = f"Re: {item_name} on EduShare AI"
    body = (
        f"Hi {uploader_name},\n\n"
        f"I am interested in your listing: {item_name} ({category}).\n\n"
        f"Please contact me at {requester_email} to arrange the exchange.\n\n"
        "Thanks!"
    )
    return f"mailto:{uploader_email}?subject={quote(subject)}&body={quote(body)}"


def test_mailto_link_is_encoded_for_exchange_request():
    link = build_mailto_link(
        uploader_email="testuploader@example.com",
        uploader_name="Aarav Sharma",
        item_name="Engineering Mathematics Textbook",
        category="Textbook",
        requester_email="student@college.edu",
    )

    assert link.startswith("mailto:testuploader@example.com?")
    assert "subject=Re%3A%20Engineering%20Mathematics%20Textbook%20on%20EduShare%20AI" in link
    assert "body=Hi%20Aarav%20Sharma" in link
    assert "\n" not in link
