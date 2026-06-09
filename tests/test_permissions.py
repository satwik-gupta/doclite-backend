"""Role-based permission tests: the PermissionPolicy AND route-level enforcement."""
from types import SimpleNamespace

import pytest

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.domain.enums import Action, Role
from app.domain.policy import PermissionPolicy
from tests.conftest import auth_header, create_doc


# ---- unit: the central policy matrix ----------------------------------------

@pytest.fixture()
def policy():
    return PermissionPolicy()


def test_matrix_edit_body(policy):
    assert policy.role_allows(Role.OWNER, Action.EDIT_BODY)
    assert policy.role_allows(Role.EDITOR, Action.EDIT_BODY)
    assert not policy.role_allows(Role.COMMENTER, Action.EDIT_BODY)
    assert not policy.role_allows(Role.VIEWER, Action.EDIT_BODY)


def test_matrix_comment(policy):
    assert policy.role_allows(Role.COMMENTER, Action.COMMENT)
    assert not policy.role_allows(Role.VIEWER, Action.COMMENT)


def test_matrix_manage_and_export(policy):
    assert policy.role_allows(Role.OWNER, Action.MANAGE_SHARING)
    assert not policy.role_allows(Role.EDITOR, Action.MANAGE_SHARING)
    # everyone with access may export
    for role in (Role.OWNER, Role.EDITOR, Role.COMMENTER, Role.VIEWER):
        assert policy.role_allows(role, Action.EXPORT)


def test_matrix_resolve_suggestion(policy):
    assert policy.role_allows(Role.OWNER, Action.RESOLVE_SUGGESTION)
    assert policy.role_allows(Role.EDITOR, Action.RESOLVE_SUGGESTION)
    assert not policy.role_allows(Role.COMMENTER, Action.RESOLVE_SUGGESTION)


def test_authorize_owner_and_stranger(policy):
    owner = SimpleNamespace(id=1)
    stranger = SimpleNamespace(id=2)
    viewer = SimpleNamespace(id=3)
    doc = SimpleNamespace(id=10, owner_id=1)

    # owner can edit
    assert policy.authorize(owner, Action.EDIT_BODY, doc, None) == Role.OWNER
    # stranger (no share) -> NotFound (existence hidden)
    with pytest.raises(NotFoundError):
        policy.authorize(stranger, Action.VIEW, doc, None)
    # viewer share -> can view but not edit
    assert policy.authorize(viewer, Action.VIEW, doc, Role.VIEWER) == Role.VIEWER
    with pytest.raises(PermissionDeniedError):
        policy.authorize(viewer, Action.EDIT_BODY, doc, Role.VIEWER)


# ---- integration: enforcement at the HTTP boundary --------------------------

def test_route_enforcement(client):
    owner = auth_header(client, "alice")
    doc = create_doc(client, owner, html="<p>secret</p>")
    did = doc["id"]

    # share dave as viewer
    client.post(f"/api/documents/{did}/shares", headers=owner, json={"identifier": "dave", "role": "viewer"})
    dave = auth_header(client, "dave")
    bob = auth_header(client, "bob")  # not shared on THIS doc

    # viewer can read but not edit
    assert client.get(f"/api/documents/{did}", headers=dave).status_code == 200
    assert client.put(f"/api/documents/{did}", headers=dave, json={"content_html": "<p>x</p>"}).status_code == 403

    # non-collaborator gets 404 (existence hidden)
    assert client.get(f"/api/documents/{did}", headers=bob).status_code == 404

    # unauthenticated -> 401
    assert client.get(f"/api/documents/{did}").status_code == 401

    # only owner manages sharing
    assert client.post(
        f"/api/documents/{did}/shares", headers=dave, json={"identifier": "bob", "role": "viewer"}
    ).status_code == 403
