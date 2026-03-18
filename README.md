# Electrical Schema Analyzer

An AI-powered application that analyzes electrical schematics using Azure Document Intelligence and Azure OpenAI (GPT-4o with vision). Upload an electrical schema image to detect components, identify issues, and chat with an AI agent to get fix suggestions.

## Features

- **Image Upload**: Upload electrical schema images (PNG, JPEG) via drag-and-drop or file picker
- **Document Analysis**: Azure Document Intelligence extracts text, tables, and bounding boxes from the schema
- **AI Description**: GPT-4o vision model describes the schema and identifies issues with severity levels
- **Bounding Box Visualization**: Detected regions and issues are highlighted on a canvas overlay
- **Chat Agent**: Conversational AI agent that can explain issues and produce updated schema descriptions to fix problems

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────┐
│   Frontend   │────▶│  FastAPI      │────▶│  Azure Document         │
│  (HTML/JS)   │     │  Backend      │     │  Intelligence           │
└─────────────┘     │              │     └─────────────────────────┘
                    │              │     ┌─────────────────────────┐
                    │              │────▶│  Azure OpenAI (GPT-4o)  │
                    │              │     │  Vision + Chat           │
                    │              │     └─────────────────────────┘
                    │              │     ┌─────────────────────────┐
                    │              │────▶│  Azure Blob Storage     │
                    └──────────────┘     └─────────────────────────┘
```

## Prerequisites

- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- [Python 3.11+](https://www.python.org/downloads/)
- An Azure subscription

## Quick Start

### 1. Clone and Set Up

```bash
git clone <repo-url>
cd doc-intelligence-demo
```

### 2. Deploy to Azure

```bash
azd auth login
azd up
```

When prompted:
- **Environment name**: `doc-intelligence-demo`
- **Azure location**: `swedencentral`

This provisions all Azure resources and deploys the application.

### 3. Local Development

```bash
cd src/backend
pip install -r requirements.txt

# Set environment variables
export AZURE_STORAGE_ACCOUNT_NAME=<your-storage-account>
export AZURE_STORAGE_CONTAINER_NAME=uploads
export AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=<your-endpoint>
export AZURE_OPENAI_ENDPOINT=<your-openai-endpoint>
export AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Run the server
uvicorn app:app --reload --port 8000
```

### 4. Generate Test Dataset

```bash
python dataset/generate_samples.py
```

### 5. Run Tests

```bash
# Unit tests (mocked Azure services)
cd src/backend
pip install pytest httpx
python -m pytest ../../tests/test_api.py -v

# End-to-end tests (requires deployed backend)
BACKEND_URL=https://<your-app>.azurewebsites.net python -m pytest tests/test_e2e.py -v
```

## Project Structure

```
├── azure.yaml                    # AZD project configuration
├── infra/
│   ├── main.bicep               # Main infrastructure template
│   ├── main.parameters.json     # Template parameters
│   ├── abbreviations.json       # Resource naming abbreviations
│   └── modules/
│       ├── storage.bicep        # Azure Blob Storage
│       ├── document-intelligence.bicep  # Azure Document Intelligence
│       ├── openai.bicep         # Azure OpenAI Service
│       ├── app-service-plan.bicep       # App Service Plan
│       ├── app-service.bicep    # App Service (backend)
│       └── role-assignment.bicep        # RBAC role assignments
├── src/
│   ├── backend/
│   │   ├── app.py               # FastAPI application
│   │   ├── requirements.txt     # Python dependencies
│   │   └── startup.sh           # App Service startup script
│   └── frontend/
│       ├── index.html           # Main HTML page
│       ├── style.css            # Styles
│       └── app.js               # Frontend JavaScript
├── dataset/
│   ├── generate_samples.py      # Sample image generator
│   └── *.png                    # Generated sample images
├── tests/
│   ├── test_api.py              # Unit tests with mocked services
│   └── test_e2e.py              # End-to-end tests
└── .github/
    └── workflows/
        └── deploy.yml           # CI/CD pipeline
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/analyze` | Upload and analyze an electrical schema image |
| `POST` | `/chat` | Chat with the AI agent about analyzed schemas |
| `GET` | `/analysis/{image_id}` | Retrieve a previous analysis result |

## Azure Resources

The following resources are provisioned by the Bicep templates:

- **Azure Document Intelligence** (S0) - Extracts layout, text, and bounding boxes from schema images
- **Azure OpenAI** (S0, GPT-4o deployment) - Vision analysis and chat agent
- **Azure Storage Account** - Blob storage for uploaded images
- **Azure App Service** (Linux, Python 3.11) - Hosts the FastAPI backend and frontend
- **RBAC Role Assignments** - Managed identity access for all services

## CI/CD

The GitHub Actions workflow (`.github/workflows/deploy.yml`) runs:

1. **Unit Tests** - On every push/PR, runs mocked tests
2. **Deploy** - On main branch, provisions infrastructure and deploys with `azd up`
3. **E2E Tests** - After deployment, runs end-to-end tests against the live service
