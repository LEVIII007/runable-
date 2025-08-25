# Trench AI - Setup & Running Guide

A comprehensive guide for setting up and running the Trench AI coding agent project.

## 📋 Prerequisites

- **Python 3.13+** (required by pyproject.toml)
- **uv** package manager (recommended) or pip
- **Docker** (for containerized deployment)
- **Google Gemini API Key** (for AI functionality)

## 🛠️ Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url> .
```

### 2. Install Dependencies with uv

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```bash
# Required API Keys
GOOGLE_API_KEY=your_actual_gemini_api_key_here

# Application Settings
DEBUG=true
API_PORT=3000
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_TO_CONSOLE=true
LOG_FORMAT=detailed
```

### 4. Run the Application

```bash
# Start the FastAPI server
uv run runable
```

The server will start on `http://localhost:3000`

### 5. Verify Installation

```bash
# Check if the server is running
curl http://localhost:3000/health
```

Expected response: `{"status": "healthy"}`

## 🐳 Docker Setup

### 1. Build the Docker Image

```bash
# Build the image
docker build -f Dockerfile -t runable .
```

### 2. Run the Container

```bash
# Run with default settings
docker run -d --name runable \
  -p 6080:6080 \
  -p 8888:8888 \
  -p 3000:3000 \
  runable
```

### 3. Run with Custom Environment Variables

```bash
# Override environment variables at runtime
docker run -d --name runable \
  -p 6080:6080 \
  -p 8888:8888 \
  -p 3000:3000 \
  -e GOOGLE_API_KEY="your_key" \
  -e DEBUG=true \
  runable
```

### 4. Access Services

- **API**: http://localhost:3000
- **VNC Desktop**: http://localhost:6080
- **Jupyter**: http://localhost:8888

## 🧪 Testing

### Run the Test Suite

```bash
# Make sure the server is running first
uv run runable

# In another terminal, run the tests
python test_coding_agent.py
```

### Test Coverage

The test suite covers:

1. **Task Scheduling**: Submit coding tasks to the AI agent
2. **Job Status Monitoring**: Track task execution progress
3. **Job Listing**: View all scheduled and completed jobs
4. **API Endpoints**: Verify all REST endpoints are functional

### Example Test Output

```
🚀 Starting Coding Agent Tests...

==================================================
API Tests (requires server running on localhost:3000)
==================================================

🔍 Testing task scheduling...
✅ Task scheduled successfully!
   Job ID: abc123
   Status: pending

🔍 Testing job status for abc123...
   Status: running (45%)
   Iteration: 3/10
✅ Job completed successfully!

🔍 Testing job listing...
✅ Jobs listed successfully!
   Total jobs: 5
   Jobs on this page: 3

==================================================
TEST SUMMARY
==================================================
Task Scheduling: ✅ PASS
Job Status: ✅ PASS
Job Listing: ✅ PASS

Overall: ✅ SUCCESS
```

## 📁 Project Structure

```
runable-ai/
├── src/
│   ├── ai/                    # AI components (LLMs, workflows)
│   ├── api/                   # FastAPI endpoints
│   ├── config/                # Configuration and logging
│   ├── helpers/               # Utility functions
│   ├── models/                # Data models
│   └── runable/               # Main application entry point
├── conf.d/                    # Supervisor configuration
├── workspace/                 # Development workspace
├── Dockerfile                 # Docker configuration
├── pyproject.toml            # Python project configuration
├── requirements.txt          # Python dependencies
├── test_coding_agent.py      # Test suite
└── supervisord.conf          # Process management
```

## 🔧 Configuration

### API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /api/coding-agent/schedule` - Schedule a coding task
- `GET /api/coding-agent/status/{job_id}` - Get job status
- `GET /api/coding-agent/jobs` - List all jobs

## 🎯 Quick Start Commands

### Local Development

```bash
# Setup
uv sync
echo "GOOGLE_API_KEY=your_key" > .env
echo "X_API_KEY=your_key" >> .env

# Run
uv run runable

# Test
python test_coding_agent.py
```

### Docker

```bash
# Build and run
docker build -f Dockerfile -t runable .
docker run -d --name runable -p 6080:6080 -p 8888:8888 -p 3000:3000 runable

# Test
python test_coding_agent.py
```

## 📚 Additional Resources

- **API Documentation**: http://localhost:3000/docs (when running)
- **VNC Access**: http://localhost:6080 (for desktop environment)
- **Jupyter Notebooks**: http://localhost:8888 (for interactive development)
