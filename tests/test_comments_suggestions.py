"""Comments + suggestion-mode tests (role-enforced, body never silently mutated)."""
from tests.conftest import auth_header, create_doc


def _share_all(client, owner, did):
    client.post(f"/api/documents/{did}/shares", headers=owner, json={"identifier": "bob", "role": "editor"})
    client.post(f"/api/documents/{did}/shares", headers=owner, json={"identifier": "carol", "role": "commenter"})
    client.post(f"/api/documents/{did}/shares", headers=owner, json={"identifier": "dave", "role": "viewer"})


def test_comment_permissions_and_resolve(client):
    owner = auth_header(client, "alice")
    doc = create_doc(client, owner, html="<p>original text</p>")
    did = doc["id"]
    _share_all(client, owner, did)
    carol = auth_header(client, "carol")
    dave = auth_header(client, "dave")

    # commenter can comment on a range
    res = client.post(
        f"/api/documents/{did}/comments",
        headers=carol,
        json={"body": "typo", "anchor_start": 0, "anchor_end": 8, "quoted_text": "original"},
    )
    assert res.status_code == 201
    cid = res.json()["id"]
    assert res.json()["author"]["username"] == "carol"

    # viewer cannot comment
    assert client.post(
        f"/api/documents/{did}/comments",
        headers=dave,
        json={"body": "x", "anchor_start": 0, "anchor_end": 1},
    ).status_code == 403

    # resolve
    res = client.patch(f"/api/documents/{did}/comments/{cid}/resolve?resolved=true", headers=carol)
    assert res.json()["resolved"] is True


def test_suggestion_does_not_mutate_body_until_accepted(client):
    owner = auth_header(client, "alice")
    doc = create_doc(client, owner, html="<p>original body</p>")
    did = doc["id"]
    _share_all(client, owner, did)
    carol = auth_header(client, "carol")
    bob = auth_header(client, "bob")

    # commenter proposes a change
    res = client.post(
        f"/api/documents/{did}/suggestions",
        headers=carol,
        json={"summary": "reword", "proposed_html": "<p>improved body</p>"},
    )
    assert res.status_code == 201
    sid = res.json()["id"]
    assert res.json()["status"] == "pending"

    # body is unchanged while pending
    body = client.get(f"/api/documents/{did}", headers=owner).json()["content_html"]
    assert "original body" in body

    # commenter cannot accept
    assert client.post(f"/api/documents/{did}/suggestions/{sid}/accept", headers=carol).status_code == 403

    # editor accepts -> body becomes proposed
    res = client.post(f"/api/documents/{did}/suggestions/{sid}/accept", headers=bob)
    assert res.status_code == 200
    assert "improved body" in res.json()["content_html"]

    # accepting again is a conflict
    assert client.post(f"/api/documents/{did}/suggestions/{sid}/accept", headers=bob).status_code == 409


def test_rejected_suggestion_keeps_body(client):
    owner = auth_header(client, "alice")
    doc = create_doc(client, owner, html="<p>keep me</p>")
    did = doc["id"]
    res = client.post(
        f"/api/documents/{did}/suggestions",
        headers=owner,
        json={"summary": "bad", "proposed_html": "<p>WRONG</p>"},
    )
    sid = res.json()["id"]
    assert client.post(f"/api/documents/{did}/suggestions/{sid}/reject", headers=owner).json()["status"] == "rejected"
    assert "WRONG" not in client.get(f"/api/documents/{did}", headers=owner).json()["content_html"]
