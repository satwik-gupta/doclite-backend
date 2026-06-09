"""Version history: restore yields old content while keeping history intact."""
from tests.conftest import auth_header, create_doc


def test_restore_is_non_destructive(client):
    header = auth_header(client, "alice")
    doc = create_doc(client, header, html="<p>v1</p>")
    did = doc["id"]

    # two more saves -> versions v1(created), v2, v3
    client.put(f"/api/documents/{did}", headers=header, json={"content_html": "<p>v2</p>", "create_version": True})
    client.put(f"/api/documents/{did}", headers=header, json={"content_html": "<h1>v3</h1>", "create_version": True})

    versions = client.get(f"/api/documents/{did}/versions", headers=header).json()
    assert len(versions) == 3
    # current body is v3
    assert "v3" in client.get(f"/api/documents/{did}", headers=header).json()["content_html"]

    # restore the oldest version (v1)
    oldest = min(versions, key=lambda v: v["version_number"])
    preview = client.get(f"/api/documents/{did}/versions/{oldest['id']}", headers=header).json()
    assert "v1" in preview["content_html"]

    restored = client.post(f"/api/documents/{did}/versions/{oldest['id']}/restore", headers=header)
    assert restored.status_code == 200
    assert "v1" in restored.json()["content_html"]  # old content is back

    # history GREW (restore appended a version); nothing was destroyed
    versions_after = client.get(f"/api/documents/{did}/versions", headers=header).json()
    assert len(versions_after) == 4
    assert any("restore" in v["label"] for v in versions_after)


def test_viewer_cannot_restore(client):
    owner = auth_header(client, "alice")
    doc = create_doc(client, owner)
    did = doc["id"]
    client.post(f"/api/documents/{did}/shares", headers=owner, json={"identifier": "dave", "role": "viewer"})
    dave = auth_header(client, "dave")

    versions = client.get(f"/api/documents/{did}/versions", headers=dave).json()
    assert len(versions) >= 1  # viewer can SEE history
    vid = versions[0]["id"]
    # but cannot restore
    assert client.post(f"/api/documents/{did}/versions/{vid}/restore", headers=dave).status_code == 403
