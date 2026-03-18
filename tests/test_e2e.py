"""End-to-end tests for the deployed application.

These tests run against a live deployment and require the BACKEND_URL
environment variable to be set.
"""

import os
import time

import httpx
import pytest

BACKEND_URL = os.getenv("BACKEND_URL", "")

pytestmark = pytest.mark.skipif(
    not BACKEND_URL,
    reason="BACKEND_URL not set - skipping e2e tests",
)


@pytest.fixture(scope="module")
def api_client():
    """Create an httpx client for the deployed backend."""
    with httpx.Client(base_url=BACKEND_URL, timeout=180.0) as client:
        yield client


@pytest.fixture(scope="module")
def sample_image_path():
    """Path to a sample test image."""
    path = os.path.join(os.path.dirname(__file__), "..", "dataset", "simple_circuit.png")
    if not os.path.exists(path):
        pytest.skip("Sample image not found - run dataset/generate_samples.py first")
    return path


def analyze_with_retry(client, filepath, filename, retries=3, delay=10):
    """Call /analyze with retries to handle transient failures."""
    for attempt in range(retries):
        with open(filepath, "rb") as f:
            response = client.post(
                "/analyze",
                files={"file": (filename, f, "image/png")},
            )
        if response.status_code == 200:
            return response
        time.sleep(delay)
    return response


@pytest.fixture(scope="module")
def analyzed_image(api_client, sample_image_path):
    """Analyze a sample image once and share the result across chat tests."""
    response = analyze_with_retry(api_client, sample_image_path, "simple_circuit.png")
    assert response.status_code == 200, f"Analyze failed: {response.status_code} {response.text}"
    return response.json()


class TestE2EHealth:
    """End-to-end health check tests."""

    def test_health_endpoint(self, api_client):
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestE2EAnalysis:
    """End-to-end analysis tests."""

    def test_upload_and_analyze(self, api_client, sample_image_path):
        response = analyze_with_retry(api_client, sample_image_path, "simple_circuit.png")

        assert response.status_code == 200, f"Analyze failed: {response.status_code} {response.text}"
        data = response.json()

        assert "image_id" in data
        assert "description" in data
        assert len(data["description"]) > 0
        assert "bounding_boxes" in data
        assert "issues_found" in data

    def test_analyze_all_samples(self, api_client):
        """Test analysis with all sample images."""
        dataset_dir = os.path.join(os.path.dirname(__file__), "..", "dataset")
        image_files = [f for f in os.listdir(dataset_dir) if f.endswith(".png")]

        for image_file in image_files:
            path = os.path.join(dataset_dir, image_file)
            response = analyze_with_retry(api_client, path, image_file)

            assert response.status_code == 200, f"Failed for {image_file}: {response.status_code} {response.text}"
            data = response.json()
            assert data["description"], f"No description for {image_file}"


class TestE2EChat:
    """End-to-end chat tests."""

    def test_chat_about_schema(self, api_client, analyzed_image):
        image_id = analyzed_image["image_id"]

        chat_response = api_client.post(
            "/chat",
            json={
                "message": "What issues did you find in this electrical schema?",
                "image_id": image_id,
                "conversation_history": [],
            },
        )

        assert chat_response.status_code == 200
        data = chat_response.json()
        assert "reply" in data
        assert len(data["reply"]) > 0

    def test_chat_request_fix(self, api_client, analyzed_image):
        """Test requesting the agent to produce an updated schema."""
        image_id = analyzed_image["image_id"]

        chat_response = api_client.post(
            "/chat",
            json={
                "message": "Please produce an updated schema that fixes all the issues you found.",
                "image_id": image_id,
                "conversation_history": [],
            },
        )

        assert chat_response.status_code == 200
        data = chat_response.json()
        assert "reply" in data
        assert len(data["reply"]) > 50  # Should be a substantial response
        # Should contain a fix suggestion
        assert data["suggested_fix"] is not None
