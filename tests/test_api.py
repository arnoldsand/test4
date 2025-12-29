"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Soccer Team": {
            "description": "Join our varsity soccer team and compete in regional tournaments",
            "schedule": "Mondays, Wednesdays, Fridays, 4:00 PM - 6:00 PM",
            "max_participants": 25,
            "participants": ["alex@mergington.edu", "sarah@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": []
        }
    })


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_success(self, client):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Soccer Team" in data
        assert "Programming Class" in data
        assert len(data["Chess Club"]["participants"]) == 2

    def test_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Programming Class/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Programming Class" in data["message"]

        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Programming Class"]["participants"]

    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Non Existent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_already_registered(self, client):
        """Test signup when student is already registered"""
        # First signup
        client.post("/activities/Programming Class/signup?email=duplicate@mergington.edu")
        
        # Try to signup again
        response = client.post(
            "/activities/Programming Class/signup?email=duplicate@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_with_special_characters_in_name(self, client):
        """Test signup with URL encoded activity name"""
        # Activity name with spaces should work
        response = client.post(
            "/activities/Chess%20Club/signup?email=newchess@mergington.edu"
        )
        assert response.status_code == 200

    def test_signup_multiple_students(self, client):
        """Test multiple students signing up for the same activity"""
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(f"/activities/Programming Class/signup?email={email}")
            assert response.status_code == 200

        # Verify all were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        participants = activities_data["Programming Class"]["participants"]
        for email in emails:
            assert email in participants


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""

    def test_remove_participant_success(self, client):
        """Test successful removal of a participant"""
        response = client.delete(
            "/activities/Chess Club/participants/michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Removed" in data["message"]
        assert "michael@mergington.edu" in data["message"]

        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in activities_data["Chess Club"]["participants"]

    def test_remove_participant_activity_not_found(self, client):
        """Test removing participant from non-existent activity"""
        response = client.delete(
            "/activities/Non Existent/participants/test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_remove_participant_not_registered(self, client):
        """Test removing participant that is not registered"""
        response = client.delete(
            "/activities/Chess Club/participants/notregistered@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Participant not found" in data["detail"]

    def test_remove_all_participants(self, client):
        """Test removing all participants from an activity"""
        # Remove both participants
        client.delete("/activities/Chess Club/participants/michael@mergington.edu")
        client.delete("/activities/Chess Club/participants/daniel@mergington.edu")

        # Verify all removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert len(activities_data["Chess Club"]["participants"]) == 0


class TestRootEndpoint:
    """Tests for root endpoint"""

    def test_root_redirects(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert "/static/index.html" in response.headers["location"]


class TestIntegration:
    """Integration tests combining multiple operations"""

    def test_signup_and_remove_workflow(self, client):
        """Test complete workflow: signup and then remove"""
        email = "workflow@mergington.edu"
        activity = "Programming Class"

        # Signup
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200

        # Verify signup
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity]["participants"]

        # Remove
        remove_response = client.delete(f"/activities/{activity}/participants/{email}")
        assert remove_response.status_code == 200

        # Verify removal
        activities_response = client.get("/activities")
        assert email not in activities_response.json()[activity]["participants"]

    def test_multiple_activities_per_student(self, client):
        """Test that a student can sign up for multiple activities"""
        email = "multitask@mergington.edu"
        activities_to_join = ["Chess Club", "Soccer Team", "Programming Class"]

        for activity in activities_to_join:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200

        # Verify student is in all activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        for activity in activities_to_join:
            assert email in activities_data[activity]["participants"]
