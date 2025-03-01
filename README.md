# CDP Support Agent Chatbot

## Overview

The CDP Support Agent Chatbot is an intelligent assistant designed to help users with questions about Customer Data Platforms (CDPs) such as Segment, mParticle, Lytics, Zeotap, Tealium, and RudderStack. It answers "how-to" questions by retrieving information from the official documentation of these platforms and generating concise, helpful responses.

The chatbot is built using a FastAPI backend and a JavaScript-based frontend. The backend integrates with the Ollama Llama2 language model to process user queries and generate answers. The frontend provides a simple, interactive chat interface where users can ask questions and receive responses.

## Key Features

- **How-to Question Answering**: Understands and responds to user questions about specific tasks within each CDP.
- **Documentation Extraction**: Fetches and parses relevant sections from the official CDP documentation.
- **Cross-CDP Comparisons**: Handles questions comparing processes or features across different CDPs.
- **Error Handling and Caching**: Includes robust error handling and in-memory caching for faster responses.
- **User-friendly Interface**: A clean, interactive chat interface with conversation history and timestamps.

## Project Structure

```
backend/
├── app.py          # FastAPI backend script
├── cdp_tasks.json  # Predefined tasks and documentation URLs for each CDP
├── requirements.txt # Python dependencies
└── static/         # Frontend files
    ├── index.html  # Chat interface structure
    ├── style.css   # Chat styling
    └── script.js   # Chat interactivity
```

## Data Structures Used and Why

The project leverages several data structures to manage information efficiently. Here's a breakdown of each, along with the reasoning behind their selection:

### 1. JSON (JavaScript Object Notation)
- **Where**: `cdp_tasks.json`
- **Purpose**: Stores predefined tasks and their corresponding documentation URLs for each CDP (e.g., `"Segment": { "set up a new source": { "url": "..." } }`).
- **Why**: JSON is lightweight, human-readable, and ideal for hierarchical data. It's easy to parse in Python and integrates seamlessly with FastAPI's JSON handling, making it perfect for configuration data that maps CDPs to tasks and URLs.

### 2. Dictionaries
- **Where**: In `app.py` for `cdp_tasks`, `doc_cache`, and various mappings.
- **Purpose**: Used for fast lookups, such as retrieving a task's URL (`cdp_tasks[cdp][task]`) or caching documentation content (`doc_cache[url]`).
- **Why**: Dictionaries provide O(1) access time for key-value pairs, making them highly efficient for associating CDPs with tasks, URLs with cached content, or other mappings. Their flexibility and performance are critical for quick response generation.

### 3. Tuples
- **Where**: In `doc_cache` to store content and timestamps.
- **Purpose**: Pairs fetched documentation content with a timestamp (e.g., `doc_cache[url] = (content, timestamp)`).
- **Why**: Tuples are immutable, ensuring cache entries remain consistent once created. They're lightweight and well-suited for bundling two related values (content and expiration time) without the overhead of a more complex structure.

### 4. Lists
- **Where**: For storing supported CDPs, available tasks, and content elements.
- **Purpose**: Holds ordered collections, like the list of valid CDPs (`VALID_CDPS = list(cdp_tasks.keys())`) or HTML elements to extract content (`content_elements = [soup.find('main'), ...]`).
- **Why**: Lists are versatile and easy to iterate over. They're used when order matters (e.g., trying multiple HTML selectors) or when a simple, dynamic collection is needed (e.g., supported CDPs).

### 5. Pydantic Models
- **Where**: `QuestionRequest(BaseModel)` in `app.py`.
- **Purpose**: Defines and validates the structure of incoming API requests (e.g., `question: str`).
- **Why**: Pydantic ensures type safety and automatic validation for FastAPI endpoints, reducing errors from malformed inputs. It's a clean, maintainable way to enforce data structure in a web application.

### 6. In-Memory Cache (Dictionary)
- **Where**: `doc_cache` for storing fetched documentation content.
- **Purpose**: Caches documentation with a TTL (Time To Live) to avoid redundant web requests.
- **Why**: Using a dictionary for caching provides fast lookups (O(1)) with URLs as keys and tuples (content, timestamp) as values. This improves performance by reusing previously fetched data, especially for frequent queries.

## Setup Instructions

### Prerequisites
- Python 3.8+
- Ollama Llama2 running locally at http://localhost:11434 (or adjust the `OLLAMA_HOST` environment variable).
- Virtual Environment (recommended for managing dependencies).

### Installation

1. **Clone the Repository**:
```bash
git clone https://github.com/yourusername/cdp-chatbot.git
cd cdp-chatbot/backend
```

2. **Create a Virtual Environment**:
```bash
python -m venv venv
```

3. **Activate the Virtual Environment**:

On Windows:
```bash
venv\Scripts\activate
```

On macOS/Linux:
```bash
source venv/bin/activate
```

4. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

5. **Run the Application**:
```bash
uvicorn app:app --reload
```

6. **Access the Chatbot**:
Open a browser and navigate to http://localhost:8000/ to use the chatbot.

## Usage

- **Ask Questions**: Type a question like "How do I create an audience in Segment?" in the chat input and press "Send."
- **View Responses**: The chatbot fetches relevant documentation and generates a concise answer.
- **Compare CDPs**: Ask comparative questions like "How does Segment's audience creation compare to Lytics'?" for side-by-side explanations.

## API Endpoints

- **POST /ask**: Submit a question and receive a response.
  - Request Body: `{ "question": "your question here" }`
  - Response: `{ "answer": "response text", "cdp": "identified CDP", "task": "identified task" }`
- **GET /supported-cdps**: Retrieve a list of supported CDPs.
- **GET /health**: Check the application's health status.

## Error Handling and Logging

- **Global Exception Handler**: Catches unexpected errors, logs them, and returns a user-friendly message.
- **Logging**: Generates detailed logs for debugging, including identified CDPs, tasks, and errors during documentation fetching or answer generation.

## Why These Data Structures?

The chosen data structures balance efficiency, readability, and maintainability:

- JSON is perfect for configuration files like `cdp_tasks.json` due to its simplicity and compatibility.
- Dictionaries excel at fast lookups and caching, critical for performance in a real-time chatbot.
- Tuples provide an immutable, lightweight way to pair cache content with timestamps.
- Lists offer flexibility for ordered or dynamic collections.
- Pydantic Models ensure robust API input handling.

This combination makes the chatbot performant, scalable, and easy to extend.
