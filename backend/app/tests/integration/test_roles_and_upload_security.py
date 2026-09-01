from io import BytesIO


def test_team_roles_enforce_read_only_access_immediately(auth_client, client) -> None:
    owner = auth_client.get("/api/auth/me").json()
    created = auth_client.post(
        "/api/auth/users",
        json={
            "email": "viewer@test.ru",
            "password": "password",
            "full_name": "Наблюдатель",
            "role": "viewer",
        },
    )
    assert created.status_code == 201
    viewer = created.json()

    users = auth_client.get("/api/auth/users")
    assert users.status_code == 200
    assert {user["email"] for user in users.json()} == {"user@test.ru", "viewer@test.ru"}

    viewer_token = client.post(
        "/api/auth/login",
        json={"email": "viewer@test.ru", "password": "password"},
    ).json()["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
    assert client.get("/api/cards", headers=viewer_headers).status_code == 200
    assert client.post(
        "/api/cards",
        json={"name": "Нельзя изменить"},
        headers=viewer_headers,
    ).status_code == 403
    assert client.get("/api/auth/users", headers=viewer_headers).status_code == 403

    last_owner = auth_client.patch(
        f"/api/auth/users/{owner['id']}/role",
        json={"role": "viewer"},
    )
    assert last_owner.status_code == 409

    promoted = auth_client.patch(
        f"/api/auth/users/{viewer['id']}/role",
        json={"role": "editor"},
    )
    assert promoted.status_code == 200
    assert client.post(
        "/api/cards",
        json={"name": "Редактор может", "vendor_code": "EDIT-1"},
        headers=viewer_headers,
    ).status_code == 201


def test_import_rejects_unapproved_and_damaged_file_types(auth_client) -> None:
    unsupported = auth_client.post(
        "/api/import/preview",
        files={"file": ("payload.exe", BytesIO(b"binary"), "application/octet-stream")},
    )
    assert unsupported.status_code == 400
    assert unsupported.json()["error"]["code"] == "UPLOAD_TYPE_NOT_ALLOWED"

    damaged_excel = auth_client.post(
        "/api/import/preview",
        files={
            "file": (
                "payload.xlsx",
                BytesIO(b"not-a-zip"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert damaged_excel.status_code == 400
    assert damaged_excel.json()["error"]["code"] == "IMPORT_PARSE_ERROR"
