"""Azure Document Intelligence + OpenAI Demo Backend."""

import base64
import io
import json
import logging
import os
import uuid
from typing import Optional

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentAnalysisFeature
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from openai import AzureOpenAI
from PIL import Image
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Electrical Schema Analyzer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from environment
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "uploads")
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

credential = DefaultAzureCredential()


def get_blob_service_client() -> BlobServiceClient:
    """Create a BlobServiceClient using managed identity."""
    account_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
    return BlobServiceClient(account_url=account_url, credential=credential)


def get_document_intelligence_client() -> DocumentIntelligenceClient:
    """Create a DocumentIntelligenceClient using managed identity."""
    return DocumentIntelligenceClient(
        endpoint=AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        credential=credential,
    )


def get_openai_client() -> AzureOpenAI:
    """Create an AzureOpenAI client using managed identity."""
    token_provider = credential.get_token("https://cognitiveservices.azure.com/.default")
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_ad_token=token_provider.token,
        api_version="2024-10-21",
    )


class AnalysisResult(BaseModel):
    """Result of image analysis."""
    image_id: str
    description: str
    bounding_boxes: list[dict]
    issues_found: list[str]
    blob_url: Optional[str] = None


class ChatRequest(BaseModel):
    """Chat request from the user."""
    message: str
    image_id: str
    analysis_context: Optional[str] = None
    conversation_history: list[dict] = []


class ChatResponse(BaseModel):
    """Chat response from the agent."""
    reply: str
    suggested_fix: Optional[str] = None


# In-memory store for analysis results (use Redis/DB in production)
analysis_store: dict[str, AnalysisResult] = {}


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend."""
    # Check deployed path first (frontend copied during packaging), then dev path
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    if not os.path.exists(frontend_path):
        frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return HTMLResponse("<h1>Electrical Schema Analyzer API</h1><p>Visit /docs for API docs.</p>")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/analyze", response_model=AnalysisResult)
async def analyze_image(file: UploadFile = File(...)):
    """
    Upload and analyze an electrical schema image.

    Returns bounding boxes of relevant components and a description.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    if len(image_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    image_id = str(uuid.uuid4())

    # Upload to blob storage
    blob_url = None
    try:
        blob_client = get_blob_service_client()
        container_client = blob_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
        blob_name = f"{image_id}/{file.filename}"
        container_client.upload_blob(name=blob_name, data=image_bytes, overwrite=True)
        blob_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_STORAGE_CONTAINER_NAME}/{blob_name}"
        logger.info("Uploaded image to blob: %s", blob_url)
    except Exception as e:
        logger.warning("Failed to upload to blob storage: %s", e)

    # Analyze with Document Intelligence
    bounding_boxes = []
    try:
        doc_client = get_document_intelligence_client()
        poller = doc_client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=AnalyzeDocumentRequest(bytes_source=image_bytes),
            features=[DocumentAnalysisFeature.KEY_VALUE_PAIRS],
        )
        result = poller.result()

        # Extract bounding boxes from pages, tables, and key-value pairs
        if result.pages:
            for page in result.pages:
                if page.lines:
                    for line in page.lines:
                        if line.polygon:
                            bounding_boxes.append({
                                "type": "text",
                                "content": line.content,
                                "polygon": [p for p in line.polygon],
                                "page": page.page_number,
                            })
                if page.selection_marks:
                    for mark in page.selection_marks:
                        if mark.polygon:
                            bounding_boxes.append({
                                "type": "selection_mark",
                                "state": mark.state,
                                "polygon": [p for p in mark.polygon],
                                "page": page.page_number,
                            })

        if result.tables:
            for table in result.tables:
                if table.bounding_regions:
                    for region in table.bounding_regions:
                        if region.polygon:
                            bounding_boxes.append({
                                "type": "table",
                                "row_count": table.row_count,
                                "column_count": table.column_count,
                                "polygon": [p for p in region.polygon],
                                "page": region.page_number,
                            })

        logger.info("Document Intelligence found %d regions", len(bounding_boxes))
    except Exception as e:
        logger.warning("Document Intelligence analysis failed: %s", e)

    # Describe with OpenAI GPT-4o Vision
    description = ""
    issues_found = []
    try:
        openai_client = get_openai_client()
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Determine mime type
        mime_type = file.content_type or "image/png"

        response = openai_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert electrical engineer analyzing electrical schematics. "
                        "Analyze the provided image and: "
                        "1) Describe what the electrical schema shows. "
                        "2) Identify any issues, errors, or problems in the schema. "
                        "3) For each issue, describe its approximate location in the image. "
                        "Return your response as JSON with keys: "
                        '"description" (string), "issues" (array of {"issue": str, "location": str, "severity": str}).'
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this electrical schema image. Identify all components, connections, and any issues.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_image}",
                            },
                        },
                    ],
                },
            ],
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        ai_result = json.loads(response.choices[0].message.content)
        description = ai_result.get("description", "No description available")
        raw_issues = ai_result.get("issues", [])
        issues_found = [
            f"[{issue.get('severity', 'info').upper()}] {issue.get('issue', '')} (Location: {issue.get('location', 'unknown')})"
            for issue in raw_issues
        ]

        # Add AI-identified issue locations as bounding boxes
        for issue in raw_issues:
            bounding_boxes.append({
                "type": "issue",
                "content": issue.get("issue", ""),
                "location": issue.get("location", "unknown"),
                "severity": issue.get("severity", "info"),
            })

        logger.info("OpenAI analysis complete: %d issues found", len(issues_found))
    except Exception as e:
        logger.warning("OpenAI analysis failed: %s", e)
        description = "Analysis unavailable - OpenAI service error"

    result = AnalysisResult(
        image_id=image_id,
        description=description,
        bounding_boxes=bounding_boxes,
        issues_found=issues_found,
        blob_url=blob_url,
    )

    analysis_store[image_id] = result
    return result


@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Chat with the AI agent about an analyzed schema.

    The agent can suggest fixes and generate updated schema descriptions.
    """
    # Retrieve previous analysis context
    context = request.analysis_context or ""
    if request.image_id in analysis_store:
        stored = analysis_store[request.image_id]
        context = (
            f"Previous analysis of the electrical schema:\n"
            f"Description: {stored.description}\n"
            f"Issues found: {json.dumps(stored.issues_found)}\n"
            f"Bounding boxes: {json.dumps(stored.bounding_boxes[:10])}\n"  # Limit for context
        )

    try:
        openai_client = get_openai_client()

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert electrical engineer assistant. You help users understand "
                    "and fix issues in electrical schematics. You can:\n"
                    "1) Explain issues found in the schema\n"
                    "2) Suggest specific fixes for identified problems\n"
                    "3) Describe how an updated schema should look to resolve issues\n"
                    "4) Provide step-by-step instructions for making corrections\n\n"
                    "When suggesting fixes, be specific about component values, connections, "
                    "and wiring changes. Format your suggestions clearly.\n\n"
                    "If asked to produce an updated schema, describe it textually with specific "
                    "changes needed, component placements, and connection modifications.\n\n"
                    f"Context from image analysis:\n{context}"
                ),
            },
        ]

        # Add conversation history
        for msg in request.conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Add current message
        messages.append({"role": "user", "content": request.message})

        response = openai_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=messages,
            max_tokens=2000,
        )

        reply = response.choices[0].message.content

        # Check if the response contains a fix suggestion
        suggested_fix = None
        fix_keywords = ["updated schema", "fix", "correction", "modified", "change"]
        if any(kw in reply.lower() for kw in fix_keywords):
            suggested_fix = reply

        return ChatResponse(reply=reply, suggested_fix=suggested_fix)

    except Exception as e:
        logger.error("Chat failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Chat service error: {e}")


@app.get("/analysis/{image_id}", response_model=AnalysisResult)
async def get_analysis(image_id: str):
    """Retrieve a previous analysis result."""
    if image_id not in analysis_store:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis_store[image_id]


# Mount static files for frontend - check deployed path first, then dev path
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if not os.path.isdir(frontend_dir):
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
