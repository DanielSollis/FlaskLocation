from suggestions import app
import pytest
import json

@pytest.fixture()
def client():
    return app.test_client()

def test_suggestions(client):
    # Test the endpoint without latitude and longitude
    response = client.get("/suggestions/London")
    suggestions = json.loads(response.data)["suggestions"]
    assert len(suggestions) == 4
    assert suggestions[0]["name"] == 'London, 08, CA'

    # Test the endpoint with a single letter to generate
    # a large number of suggestions
    response = client.get("/suggestions/L")
    suggestions = json.loads(response.data)["suggestions"]
    assert len(suggestions) == 316

    # Test the suggestions endpoint with latitude and longitude
    response = client.get("/suggestions/London/43.70011/-79.4163")
    suggestions = json.loads(response.data)["suggestions"]
    assert len(suggestions) == 4
    assert suggestions[0]["score"] == 0.7
    assert suggestions[1]["score"] == 0.6
    assert suggestions[2]["score"] == 0.5
    assert suggestions[3]["score"] == 0.4