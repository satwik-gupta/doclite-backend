"""Export tests: Markdown and PDF produce non-empty, well-formed output."""
from tests.conftest import auth_header, create_doc

FORMATTED = (
    "<h1>Title</h1><p>Some <strong>bold</strong> and <em>italic</em> text.</p>"
    "<ul><li>alpha</li><li>beta</li></ul><ol><li>one</li></ol>"
)


def test_markdown_export(client):
    header = auth_header(client, "alice")
    doc = create_doc(client, header, title="Export Me", html=FORMATTED)
    res = client.get(f"/api/documents/{doc['id']}/export/md", headers=header)
    assert res.status_code == 200
    text = res.content.decode("utf-8")
    assert len(text) > 0
    assert "#" in text  # heading
    assert "**bold**" in text
    assert "attachment" in res.headers["content-disposition"]
    assert res.headers["content-disposition"].endswith('.md"')


def test_pdf_export(client):
    header = auth_header(client, "alice")
    doc = create_doc(client, header, title="Export Me", html=FORMATTED)
    res = client.get(f"/api/documents/{doc['id']}/export/pdf", headers=header)
    assert res.status_code == 200
    assert res.content[:4] == b"%PDF"  # valid PDF signature
    assert len(res.content) > 800
    assert res.headers["content-type"] == "application/pdf"


def test_export_access_controlled(client):
    owner = auth_header(client, "alice")
    doc = create_doc(client, owner, html=FORMATTED)
    bob = auth_header(client, "bob")  # not shared
    assert client.get(f"/api/documents/{doc['id']}/export/md", headers=bob).status_code == 404


def test_bad_export_format(client):
    header = auth_header(client, "alice")
    doc = create_doc(client, header)
    assert client.get(f"/api/documents/{doc['id']}/export/rtf", headers=header).status_code == 422
