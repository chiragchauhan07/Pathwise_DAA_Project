from fastapi.testclient import TestClient

from backend.core_engine.main import app

client = TestClient(app)


def test_app_imports_and_initializes():
    assert app is not None
    assert app.title == "DAA Course Registration Assistant API"


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "daa-course-registration-api"
    assert data["version"] == "2.0.0"


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "daa-course-registration-api"
    assert "docs_url" in data
    assert "health_url" in data
    assert "courses_url" in data
    assert "learning_path_url" in data


def test_openapi_schema_accessible():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "DAA Course Registration Assistant API"
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/courses" in schema["paths"]
    assert "/api/v1/learning-path" in schema["paths"]


def test_health_alias_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_courses_catalog_endpoints():
    res_v1 = client.get("/api/v1/courses")
    assert res_v1.status_code == 200
    courses_v1 = res_v1.json()
    assert len(courses_v1) == 100

    res_alias = client.get("/api/courses")
    assert res_alias.status_code == 200
    courses_alias = res_alias.json()
    assert len(courses_alias) == 100


def test_learning_path_alias_endpoint():
    payload = {
        "courses": ["Programming Fundamentals", "Data Structures"],
    }
    response = client.post("/api/learning-path", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["selected_courses"]) == 2
    assert len(data["ordered_courses"]) == 2
    assert data["ai_proposals_used"] is False
