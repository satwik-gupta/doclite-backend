"""Document lifecycle: create -> rename -> save -> reload returns saved rich content."""
from tests.conftest import auth_header, create_doc


def test_create_rename_save_reload(client):
    header = auth_header(client, "alice")

    # create
    doc = create_doc(client, header, title="Draft", html="<p>initial</p>")
    did = doc["id"]
    assert doc["my_role"] == "owner"

    # rename
    res = client.patch(f"/api/documents/{did}/title", headers=header, json={"title": "Final Title"})
    assert res.status_code == 200
    assert res.json()["title"] == "Final Title"

    # save rich content
    rich = "<h1>Heading</h1><p>Body with <strong>bold</strong> and <em>italic</em>.</p><ul><li>x</li></ul>"
    res = client.put(f"/api/documents/{did}", headers=header, json={"content_html": rich, "create_version": True})
    assert res.status_code == 200

    # reload returns the saved formatting intact
    reloaded = client.get(f"/api/documents/{did}", headers=header).json()
    assert reloaded["title"] == "Final Title"
    assert "<h1>" in reloaded["content_html"]
    assert "<strong>" in reloaded["content_html"]
    assert "<ul>" in reloaded["content_html"]


def test_empty_title_rejected(client):
    header = auth_header(client, "alice")
    doc = create_doc(client, header)
    res = client.patch(f"/api/documents/{doc['id']}/title", headers=header, json={"title": ""})
    assert res.status_code == 422


def test_xss_sanitized_on_save(client):
    header = auth_header(client, "alice")
    doc = create_doc(client, header)
    malicious = '<p>ok</p><script>alert(1)</script><img src=x onerror=alert(2)>'
    client.put(f"/api/documents/{doc['id']}", headers=header, json={"content_html": malicious})
    html = client.get(f"/api/documents/{doc['id']}", headers=header).json()["content_html"]
    assert "<script>" not in html
    assert "onerror" not in html
