from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 3,
        "participants": ["alex@mergington.edu"],
    },
    "Soccer Club": {
        "description": "Practice soccer skills and compete in friendly matches",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 2,
        "participants": [],
    },
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "activities", deepcopy(ACTIVITIES))
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_root_redirects_to_activities_page(client):
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_get_activities_returns_current_data(client):
    # Arrange
    expected_activities = deepcopy(ACTIVITIES)

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected_activities


def test_signup_adds_participant(client):
    # Arrange
    email = "sam@mergington.edu"

    # Act
    response = client.post("/activities/Chess%20Club/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for Chess Club"}
    assert email in app_module.activities["Chess Club"]["participants"]


def test_signup_rejects_duplicate_participant(client):
    # Arrange
    email = "alex@mergington.edu"

    # Act
    response = client.post("/activities/Chess%20Club/signup", params={"email": email})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student is already signed up for this activity"
    assert app_module.activities["Chess Club"]["participants"].count(email) == 1


def test_signup_accepts_last_spot_and_rejects_next_participant(client):
    # Arrange
    activity = app_module.activities["Soccer Club"]
    activity["participants"] = ["alex@mergington.edu"]
    last_participant = "sam@mergington.edu"
    rejected_participant = "lee@mergington.edu"

    # Act
    accepted_response = client.post(
        "/activities/Soccer%20Club/signup", params={"email": last_participant}
    )
    rejected_response = client.post(
        "/activities/Soccer%20Club/signup", params={"email": rejected_participant}
    )

    # Assert
    assert accepted_response.status_code == 200
    assert rejected_response.status_code == 400
    assert rejected_response.json()["detail"] == "Activity is full"
    assert activity["participants"] == ["alex@mergington.edu", last_participant]


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_signup_and_unregister_require_email(client, method):
    # Arrange
    participants_before_request = deepcopy(app_module.activities["Chess Club"]["participants"])

    # Act
    response = client.request(method, "/activities/Chess%20Club/signup")

    # Assert
    assert response.status_code == 422
    assert app_module.activities["Chess Club"]["participants"] == participants_before_request


def test_signup_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Robotics Club"

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": "sam@mergington.edu"})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_full_activity(client):
    # Arrange
    activity = app_module.activities["Soccer Club"]
    activity["participants"] = ["alex@mergington.edu", "lee@mergington.edu"]
    email = "sam@mergington.edu"

    # Act
    response = client.post("/activities/Soccer%20Club/signup", params={"email": email})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Activity is full"
    assert email not in activity["participants"]


def test_unregister_removes_participant(client):
    # Arrange
    email = "alex@mergington.edu"

    # Act
    response = client.delete("/activities/Chess%20Club/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from Chess Club"}
    assert email not in app_module.activities["Chess Club"]["participants"]


def test_unregistered_participant_can_sign_up_again(client):
    # Arrange
    email = "alex@mergington.edu"

    # Act
    unregister_response = client.delete(
        "/activities/Chess%20Club/signup", params={"email": email}
    )
    signup_response = client.post(
        "/activities/Chess%20Club/signup", params={"email": email}
    )

    # Assert
    assert unregister_response.status_code == 200
    assert signup_response.status_code == 200
    assert app_module.activities["Chess Club"]["participants"].count(email) == 1


def test_unregister_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Robotics Club"

    # Act
    response = client.delete(
        f"/activities/{activity_name}/signup", params={"email": "sam@mergington.edu"}
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_rejects_nonparticipant(client):
    # Arrange
    email = "sam@mergington.edu"

    # Act
    response = client.delete("/activities/Chess%20Club/signup", params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"
    assert email not in app_module.activities["Chess Club"]["participants"]