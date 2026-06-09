"""Real-time presence: two WebSocket clients on one document see each other,
and a save broadcasts a 'document_updated' signal.

Driven via Starlette's TestClient WebSocket support, which exercises the real async
server (the ConnectionManager runs in the app's event loop)."""
from tests.conftest import auth_header, create_doc


def _token(client, username):
    return client.post(
        "/api/auth/login", json={"identifier": username, "password": "password123"}
    ).json()["access_token"]


def test_two_clients_see_each_other_and_update_signal(client):
    owner = auth_header(client, "alice")
    doc = create_doc(client, owner, html="<p>rt</p>")
    did = doc["id"]
    client.post(f"/api/documents/{did}/shares", headers=owner, json={"identifier": "bob", "role": "editor"})

    alice_token = _token(client, "alice")
    bob_token = _token(client, "bob")

    with client.websocket_connect(f"/ws/documents/{did}?token={alice_token}") as wa:
        snap = wa.receive_json()
        assert snap["type"] == "presence"
        assert any(u["username"] == "alice" for u in snap["users"])

        with client.websocket_connect(f"/ws/documents/{did}?token={bob_token}") as wb:
            bsnap = wb.receive_json()
            # bob's first message is a presence snapshot listing both users
            assert {u["username"] for u in bsnap["users"]} == {"alice", "bob"}

            # alice is notified bob joined
            types = {wa.receive_json()["type"], wa.receive_json()["type"]}
            assert "user_joined" in types

            # alice saves -> bob receives a 'document_updated' event
            client.put(f"/api/documents/{did}", headers=owner, json={"content_html": "<p>changed</p>"})
            got_update = False
            for _ in range(6):
                msg = wb.receive_json()
                if msg["type"] == "document_updated":
                    assert msg["by"]["username"] == "alice"
                    got_update = True
                    break
            assert got_update


def test_ws_rejects_without_token(client):
    owner = auth_header(client, "alice")
    doc = create_doc(client, owner)
    did = doc["id"]
    with client.websocket_connect(f"/ws/documents/{did}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
