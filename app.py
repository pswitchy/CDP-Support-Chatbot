from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import json
import os
from ollama import Client
import difflib
import logging
from typing import Dict, Tuple, Optional
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="CDP Support Agent", 
              description="An assistant for Customer Data Platform (CDP) questions")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory to serve frontend files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Ollama client
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama2")
ollama_client = Client(host=OLLAMA_HOST)

# Load predefined tasks and URLs
try:
    with open('cdp_tasks.json', 'r') as f:
        cdp_tasks = json.load(f)
    logger.info(f"Loaded CDP tasks: {len(cdp_tasks)} platforms")
except (FileNotFoundError, json.JSONDecodeError) as e:
    logger.error(f"Error loading cdp_tasks.json: {e}")
    cdp_tasks = {}

# Get valid CDPs from the loaded JSON
VALID_CDPS = list(cdp_tasks.keys())
logger.info(f"Valid CDPs: {VALID_CDPS}")

# Pydantic model for request body
class QuestionRequest(BaseModel):
    question: str

# Cache for documentation with TTL (24 hours)
doc_cache: Dict[str, Tuple[str, float]] = {}
CACHE_TTL = 24 * 60 * 60  # 24 hours in seconds

def identify_cdp_and_task(question: str) -> Tuple[str, str]:
    """
    Use LLM to identify the CDP and task from the user's question
    """
    cdp_list_str = ", ".join(VALID_CDPS)
    prompt = f"""Extract the CDP platform and specific task from this question: '{question}'.
    
Valid CDPs: {cdp_list_str}
    
Reply with ONLY two lines:
CDP: [name of CDP or None if unclear]
Task: [specific task or None if unclear]
"""
    try:
        response = ollama_client.generate(model=OLLAMA_MODEL, prompt=prompt)
        lines = response['response'].strip().split('\n')
        
        cdp = "None"
        task = "None"
        
        for line in lines:
            if line.startswith("CDP:"):
                cdp = line.split("CDP:")[1].strip()
            elif line.startswith("Task:"):
                task = line.split("Task:")[1].strip()
                
        # Validate CDP is in our list
        if cdp != "None" and cdp in VALID_CDPS:
            # Find closest matching task if available
            if task != "None" and cdp in cdp_tasks:
                available_tasks = list(cdp_tasks[cdp].keys())
                closest_matches = difflib.get_close_matches(
                    task.lower(), 
                    [t.lower() for t in available_tasks], 
                    n=1, 
                    cutoff=0.6
                )
                if closest_matches:
                    # Find the original case-sensitive task
                    idx = [t.lower() for t in available_tasks].index(closest_matches[0])
                    task = available_tasks[idx]
        else:
            cdp = "None"
            
        logger.info(f"Identified CDP: {cdp}, Task: {task}")
        return cdp, task
    except Exception as e:
        logger.error(f"Error identifying CDP/task: {e}", exc_info=True)
        return "None", "None"

def fetch_documentation(cdp: str, task: Optional[str] = None) -> str:
    """
    Fetch documentation from the appropriate URL based on CDP and task
    """
    if task and cdp in cdp_tasks and task in cdp_tasks[cdp]:
        task_data = cdp_tasks[cdp][task]
        if isinstance(task_data, dict):
            url = task_data["url"]
            logger.info(f"Fetching specific documentation for {cdp}/{task}: {url}")
        elif isinstance(task_data, str):
            url = task_data
            logger.info(f"Fetching specific documentation (string URL) for {cdp}/{task}: {url}")
        else:
            url = ""
            logger.warning(f"Unexpected type for task data: {type(task_data)}")
    else:
        # Default to root documentation URL if specific task not found
        root_urls = {
            "Segment": "https://segment.com/docs/",
            "mParticle": "https://docs.mparticle.com/",
            "Lytics": "https://docs.lytics.com/",
            "Zeotap": "https://docs.zeotap.com/home/en-us/",
            "Tealium": "https://docs.tealium.com/",
            "RudderStack": "https://www.rudderstack.com/docs/"
        }
        url = root_urls.get(cdp, "")
        if not url:
            return f"No documentation URL available for {cdp}"
        logger.info(f"Fetching general documentation for {cdp}: {url}")
    
    # Check cache first with TTL
    current_time = time.time()
    if url in doc_cache:
        content, timestamp = doc_cache[url]
        if current_time - timestamp < CACHE_TTL:
            logger.info(f"Using cached documentation for {url}")
            return content
    
    # Fetch if not in cache or expired
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find main content elements
        content_elements = [
            soup.find('main'),
            soup.find('article'),
            soup.find('div', class_='documentation'),
            soup.find('div', class_='content'),
            soup.find('div', id='content'),
            soup.find('div', class_='docs-content')
        ]
        
        # Use the first valid element found
        content_element = next((el for el in content_elements if el), soup.body)
        
        if content_element:
            # Extract text with better formatting
            text = content_element.get_text(separator='\n', strip=True)
            
            # Clean up the text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)
            
            # Cache the result with timestamp
            doc_cache[url] = (text, current_time)
            return text
        else:
            error_msg = "No content found on the page"
            logger.error(f"{error_msg}: {url}")
            return error_msg
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP Error: {e.response.status_code} - {e.response.reason}"
        logger.error(f"{error_msg} for URL: {url}")
        return error_msg
    except requests.exceptions.ConnectionError:
        error_msg = f"Connection Error: Could not connect to {url}"
        logger.error(error_msg)
        return error_msg
    except requests.exceptions.Timeout:
        error_msg = f"Timeout Error: Request to {url} timed out"
        logger.error(error_msg)
        return error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching documentation: {str(e)}"
        logger.error(f"{error_msg} for URL: {url}")
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"{error_msg} for URL: {url}", exc_info=True)
        return error_msg

def generate_answer(question: str, content: str, cdp: str, task: Optional[str] = None) -> str:
    """
    Generate answer using LLM based on the documentation content
    """
    context = f"CDP: {cdp}"
    if task != "None":
        context += f", Task: {task}"
        
    # Limit content length to prevent token issues
    max_content_length = 3000
    content_summary = content[:max_content_length]
    if len(content) > max_content_length:
        content_summary += "... [content truncated for length]"
    
    prompt = f"""You are a helpful CDP (Customer Data Platform) support agent.
    
CONTEXT INFORMATION:
{context}

DOCUMENTATION:
{content_summary}

USER QUESTION:
{question}

Please provide a helpful, accurate, and concise response based only on the documentation provided. 
If you don't know or the information isn't in the documentation, say so clearly.
Be specific and cite relevant details from the documentation when possible.
"""
    
    try:
        response = ollama_client.generate(
            model=OLLAMA_MODEL, 
            prompt=prompt,
            options={"temperature": 0.3}  # Lower temperature for more factual responses
        )
        return response['response']
    except Exception as e:
        logger.error(f"Error generating answer: {e}", exc_info=True)
        return "I'm sorry, I encountered an error while generating an answer. Please try again later."

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    """
    Process a question and return an answer
    """
    question = request.question
    
    # Identify the CDP and task from the question
    cdp, task = identify_cdp_and_task(question)
    
    if cdp == "None":
        return {
            "answer": f"I can only help with questions about the following CDPs: {', '.join(VALID_CDPS)}. Could you please specify which platform you're asking about?",
            "cdp": None,
            "task": None
        }
    
    # Fetch documentation content
    content = fetch_documentation(cdp, task)
    
    if content.startswith("Error") or content.startswith("HTTP Error") or content.startswith("Connection Error"):
        return {
            "answer": f"I'm having trouble accessing the documentation for {cdp}. {content}",
            "cdp": cdp,
            "task": task
        }
    
    # Generate answer
    answer = generate_answer(question, content, cdp, task)
    
    return {
        "answer": answer,
        "cdp": cdp,
        "task": task
    }

@app.get("/supported-cdps")
async def get_supported_cdps():
    """Return list of supported CDPs"""
    return {"cdps": VALID_CDPS}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

# Serve the frontend at root
@app.get("/")
async def read_root():
    try:
        return FileResponse("static/index.html")
    except Exception as e:
        logger.error(f"Error serving index.html: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail="Index file not found")

# Healthcheck endpoint
@app.get("/health")
async def health_check():
    """Return health status of the application"""
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)