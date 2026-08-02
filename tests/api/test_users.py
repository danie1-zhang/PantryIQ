def test_get_current_user_excludes_password(client, api_user) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 200
    assert response.json()["id"] == str(api_user.id)
    assert "password_hash" not in response.json()


def test_partial_user_update(client, api_user) -> None:
    response = client.patch("/api/v1/users/me", json={"name": "Updated", "protein_goal": 120})

    assert response.status_code == 200
    assert response.json()["name"] == "Updated"
    assert response.json()["protein_goal"] == 120


def test_invalid_user_updates_are_rejected(client, api_user) -> None:
    for payload in (
        {"age": 0},
        {"height_inches": 0},
        {"weight_pounds": -1},
        {"calorie_goal": 0},
        {"name": "   "},
        {"protein_goal": None},
    ):
        assert client.patch("/api/v1/users/me", json=payload).status_code == 422
