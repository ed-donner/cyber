import os
import sys
from signal import raise_signal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
from agents import Agent, Runner, trace
from context import SECURITY_RESEARCHER_INSTRUCTIONS, get_analysis_prompt, enhance_summary
from mcp_servers import create_semgrep_server
import tempfile
from pathlib import Path
import logging

load_dotenv()



app = FastAPI(title="Cybersecurity Analyzer API")

# Configure CORS for development and production
cors_origins = [
    "http://localhost:3000",    # Local development
    "http://frontend:3000",     # Docker development
]

# In production, allow same-origin requests (static files served from same domain)
if os.getenv("ENVIRONMENT") == "production":
    cors_origins.append("*")  # Allow all origins in production since we serve frontend from same domain

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
root_logger.addHandler(handler)

'''
Semgrep made a recent change: 'path' is required to have an absolute path in 'code_files'.  Unfortunately, modern web framework, including React
does not allow us to access real path for security reasons.  The path need to be accessible to Semgrep and cannot be fake.  We changed codes to
pass the file_name from UI and create a temporary file in 'server.py' then pass it to 'context.py' then send a well-formatted json to 'semgrep_scan' to
get it working.  Thanks to the contribution from Akash, Sahil and Sonya.     
'''
class AnalyzeRequest(BaseModel):
    code: str
    file_name: str

class SecurityIssue(BaseModel):
    title: str = Field(description="Brief title of the security vulnerability")
    description: str = Field(
        description="Detailed description of the security issue and its potential impact"
    )
    code: str = Field(
        description="The specific vulnerable code snippet that demonstrates the issue"
    )
    fix: str = Field(description="Recommended code fix or mitigation strategy")
    cvss_score: float = Field(description="CVSS score from 0.0 to 10.0 representing severity")
    severity: str = Field(description="Severity level: critical, high, medium, or low")


class SecurityReport(BaseModel):
    summary: str = Field(description="Executive summary of the security analysis")
    issues: List[SecurityIssue] = Field(description="List of identified security vulnerabilities")


def validate_request(request: AnalyzeRequest) -> None:
    """Validate the analysis request."""
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="No code provided for analysis")


def check_api_keys() -> None:
    """Verify required API keys are configured."""
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")


def create_security_agent(semgrep_server) -> Agent:
    """Create and configure the security analysis agent."""
    # I will create instructions as a system prompt and Runner.run input as a user prompt
    return Agent(
        name="Security Researcher",
        instructions=SECURITY_RESEARCHER_INSTRUCTIONS,
        model="gpt-4.1-mini",
        mcp_servers=[semgrep_server],
        output_type=SecurityReport,
    )

async def run_security_analysis(request: AnalyzeRequest, temp_file_path: str) -> SecurityReport:
    """Execute the security analysis workflow."""
    
    with trace("Security Researcher"):
        async with create_semgrep_server() as semgrep:
            agent = create_security_agent(semgrep)
            result = await Runner.run(agent, input=get_analysis_prompt(request.code, temp_file_path))
            return result.final_output_as(SecurityReport)

def format_analysis_response(code: str, report: SecurityReport) -> SecurityReport:
    """Format the final analysis response."""
    enhanced_summary = enhance_summary(len(code), report.summary)
    return SecurityReport(summary=enhanced_summary, issues=report.issues)

@app.post("/api/analyze", response_model=SecurityReport)
async def analyze_code(request: AnalyzeRequest) -> SecurityReport:
    """
    Analyze Python code for security vulnerabilities using OpenAI Agents and Semgrep.

    This endpoint combines static analysis via Semgrep with AI-powered security analysis
    to provide comprehensive vulnerability detection and remediation guidance.
    """
    logging.info("##### START analyze_code")
    validate_request(request)
    check_api_keys()
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, prefix=f'{Path(request.file_name).stem}_')
    # Use Path().resolve() to get an OS-agnostic absolute path (fixes Windows \ vs /)
    tmp_path = Path(tmp.name).resolve() 
    try:
        logging.info(f"##### SAVING temp file") 
        tmp.write(request.code)
        tmp.close() 
 
        # 2. Ensure the Agent receives a clean string path
        # .as_posix() converts Windows \ to / which Semgrep prefers
        clean_path = tmp_path.as_posix() 
        logging.info(f"##### RUNNING security analysis with tmp file= {clean_path}....") 
        report = await run_security_analysis(request, clean_path) 
        return format_analysis_response(request.code, report)
    except Exception as e:
        logging.exception("##### Encounter error when nalyze_code")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        # 3. Clean up the physical file from the disk
        if tmp_path.exists():
            try:
                os.remove(tmp_path)
            except OSError:
                pass # Prevent cleanup errors from crashing the response

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"message": "Cybersecurity Analyzer API"}

@app.get("/network-test")
async def network_test():
    """Test network connectivity to Semgrep API."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://semgrep.dev/api/v1/")
            return {
                "semgrep_api_reachable": True,
                "status_code": response.status_code,
                "response_size": len(response.content)
            }
    except Exception as e:
        return {
            "semgrep_api_reachable": False,
            "error": str(e)
        }

@app.get("/semgrep-test")
async def semgrep_test():
    """Test if semgrep CLI can be installed and run."""
    import subprocess
    import tempfile
    import os
    
    try:
        # Test if we can install semgrep via pip
        result = subprocess.run(
            ["pip", "install", "semgrep"], 
            capture_output=True, 
            text=True, 
            timeout=60
        )
        
        if result.returncode != 0:
            return {
                "semgrep_install": False,
                "error": f"Install failed: {result.stderr}"
            }
        
        # Test if semgrep --version works
        version_result = subprocess.run(
            ["semgrep", "--version"], 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        return {
            "semgrep_install": True,
            "version_check": version_result.returncode == 0,
            "version_output": version_result.stdout,
            "version_error": version_result.stderr
        }
        
    except subprocess.TimeoutExpired:
        return {
            "semgrep_install": False,
            "error": "Timeout during semgrep installation or version check"
        }
    except Exception as e:
        return {
            "semgrep_install": False,
            "error": str(e)
        }

# Mount static files for frontend
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
