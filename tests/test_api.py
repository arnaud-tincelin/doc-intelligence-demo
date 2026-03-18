"""Unit tests for the backend API with mocked Azure services."""

import io
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture
def client():
    """Create a test client."""
    from app import app

    return TestClient(app)


@pytest.fixture
def sample_image_bytes():
    """Create a simple test image in memory."""
    img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestAnalyzeEndpoint:
    """Tests for the /analyze endpoint."""

    def test_reject_non_image_file(self, client):
        response = client.post(
            "/analyze",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert response.status_code == 400
        assert "image" in response.json()["detail"].lower()

    @patch("app.get_inference_client")
    @patch("app.get_document_intelligence_client")
    @patch("app.get_blob_service_client")
    def test_analyze_returns_result(
        self,
        mock_blob,
        mock_doc_intel,
        mock_inference,
        client,
        sample_image_bytes,
    ):
        # Mock blob storage
        mock_container = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_client.get_container_client.return_value = mock_container
        mock_blob.return_value = mock_blob_client

        # Mock Document Intelligence
        mock_doc_client = MagicMock()
        mock_poller = MagicMock()
        mock_result = MagicMock()
        mock_result.pages = []
        mock_result.tables = []
        mock_poller.result.return_value = mock_result
        mock_doc_client.begin_analyze_document.return_value = mock_poller
        mock_doc_intel.return_value = mock_doc_client

        # Mock AI Foundry inference client
        mock_inf_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(
            {
                "description": "A simple electrical circuit with a battery and resistor.",
                "issues": [
                    {
                        "issue": "Missing ground connection",
                        "location": "bottom of circuit",
                        "severity": "high",
                    }
                ],
            }
        )
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_inf_client.complete.return_value = mock_response
        mock_inference.return_value = mock_inf_client

        response = client.post(
            "/analyze",
            files={"file": ("test.png", sample_image_bytes, "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert "image_id" in data
        assert "description" in data
        assert "bounding_boxes" in data
        assert "issues_found" in data
        assert "simple electrical circuit" in data["description"].lower()
        assert len(data["issues_found"]) == 1
        assert "Missing ground connection" in data["issues_found"][0]

    @patch("app.get_inference_client")
    @patch("app.get_document_intelligence_client")
    @patch("app.get_blob_service_client")
    def test_analyze_handles_service_errors(
        self,
        mock_blob,
        mock_doc_intel,
        mock_inference,
        client,
        sample_image_bytes,
    ):
        """Test that the endpoint returns gracefully when Azure services fail."""
        mock_blob.side_effect = Exception("Storage unavailable")
        mock_doc_intel.return_value.begin_analyze_document.side_effect = Exception(
            "Doc Intel unavailable"
        )
        mock_inference.return_value.complete.side_effect = Exception(
            "AI Foundry unavailable"
        )

        response = client.post(
            "/analyze",
            files={"file": ("test.png", sample_image_bytes, "image/png")},
        )

        # Should still return 200 with degraded results
        assert response.status_code == 200
        data = response.json()
        assert "image_id" in data
        assert "unavailable" in data["description"].lower() or data["description"] != ""


class TestChatEndpoint:
    """Tests for the /chat endpoint."""

    @patch("app.get_inference_client")
    def test_chat_returns_reply(self, mock_inference, client):
        # Mock AI Foundry inference client
        mock_inf_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = (
            "The missing ground connection should be added at the bottom of the circuit. "
            "Here is the fix: connect a wire from the negative terminal to ground."
        )
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_inf_client.complete.return_value = mock_response
        mock_inference.return_value = mock_inf_client

        response = client.post(
            "/chat",
            json={
                "message": "How do I fix the ground connection?",
                "image_id": "test-id",
                "analysis_context": "Previous analysis found missing ground.",
                "conversation_history": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "ground" in data["reply"].lower()
        # Should detect fix suggestion
        assert data["suggested_fix"] is not None

    @patch("app.get_inference_client")
    def test_chat_with_conversation_history(self, mock_inference, client):
        mock_inf_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Yes, you should use a 10kΩ resistor for the pull-down."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_inf_client.complete.return_value = mock_response
        mock_inference.return_value = mock_inf_client

        response = client.post(
            "/chat",
            json={
                "message": "What resistor value should I use?",
                "image_id": "test-id",
                "conversation_history": [
                    {"role": "user", "content": "What is wrong with the circuit?"},
                    {"role": "assistant", "content": "The pull-down resistor is missing."},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "reply" in data

    @patch("app.get_inference_client")
    def test_chat_handles_inference_error(self, mock_inference, client):
        mock_inference.return_value.complete.side_effect = Exception(
            "Service error"
        )

        response = client.post(
            "/chat",
            json={
                "message": "Hello",
                "image_id": "test-id",
            },
        )

        assert response.status_code == 500


class TestGetAnalysis:
    """Tests for the /analysis/{image_id} endpoint."""

    def test_get_missing_analysis_returns_404(self, client):
        response = client.get("/analysis/nonexistent-id")
        assert response.status_code == 404

    @patch("app.get_inference_client")
    @patch("app.get_document_intelligence_client")
    @patch("app.get_blob_service_client")
    def test_get_analysis_after_upload(
        self,
        mock_blob,
        mock_doc_intel,
        mock_inference,
        client,
        sample_image_bytes,
    ):
        # Setup mocks (same as analyze test)
        mock_container = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_client.get_container_client.return_value = mock_container
        mock_blob.return_value = mock_blob_client

        mock_doc_client = MagicMock()
        mock_poller = MagicMock()
        mock_result = MagicMock()
        mock_result.pages = []
        mock_result.tables = []
        mock_poller.result.return_value = mock_result
        mock_doc_client.begin_analyze_document.return_value = mock_poller
        mock_doc_intel.return_value = mock_doc_client

        mock_inf_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(
            {"description": "Test circuit", "issues": []}
        )
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_inf_client.complete.return_value = mock_response
        mock_inference.return_value = mock_inf_client

        # Upload and analyze
        upload_response = client.post(
            "/analyze",
            files={"file": ("test.png", sample_image_bytes, "image/png")},
        )
        image_id = upload_response.json()["image_id"]

        # Retrieve analysis
        get_response = client.get(f"/analysis/{image_id}")
        assert get_response.status_code == 200
        assert get_response.json()["image_id"] == image_id
