from fastapi.testclient import TestClient

from backend.core_engine.main import app

client = TestClient(app)


def test_app_imports_and_initializes():
    assert app is not None
    assert app.title == "DAA Course Learning Path API"


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "healthy",
        "service": "daa-learning-path-api",
        "version": "1.0.0",
    }


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "daa-learning-path-api"
    assert "docs_url" in data
    assert "health_url" in data


def test_openapi_schema_accessible():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "DAA Course Learning Path API"
    assert "/api/v1/health" in schema["paths"]


def test_health_alias_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_courses_catalog_endpoints():
    res_v1 = client.get("/api/v1/courses")
    assert res_v1.status_code == 200
    courses_v1 = res_v1.json()
    assert len(courses_v1) == 70

    res_alias = client.get("/api/courses")
    assert res_alias.status_code == 200
    courses_alias = res_alias.json()
    assert len(courses_alias) == 70


def test_learning_path_alias_endpoint():
    payload = {
        "courses": ["Programming Fundamentals", "Data Structures"],
        "use_ai": False,
    }
    response = client.post("/api/learning-path", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["selected_courses"]) == 2
    assert len(data["ordered_courses"]) == 2


def test_ai_status_endpoint():
    res = client.get("/api/v1/ai/status")
    assert res.status_code == 200
    data = res.json()
    assert "configured" in data
    assert "key_present" in data
    assert "key_empty" in data
    assert "key_source" in data
    assert "model" in data
    assert "timeout_seconds" in data
    assert "max_retries" in data
    assert "client_initializable" in data
    # Ensure raw secret is never present in response keys or values
    assert "api_key" not in data
    assert "gemini_api_key" not in data
    for val in data.values():
        if isinstance(val, str):
            assert not val.startswith("AIza")

    # Alias check
    res_alias = client.get("/api/ai/status")
    assert res_alias.status_code == 200
    assert res_alias.json()["model"] == data["model"]

