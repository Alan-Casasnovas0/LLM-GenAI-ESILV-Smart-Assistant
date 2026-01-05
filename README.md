

# ESILV Academic Assistant

A local, privacy-focused academic assistant for ESILV students. It retrieves real-time data from the De Vinci Moodle platform and answers student queries using a local LLM (Ollama).

## Features

*   **Course Overview**: Retrieves the complete list of enrolled courses, categories, and progress percentages from the Moodle dashboard. The local LLM then filters and summarizes this data based on student queries.
*   **Deadline Tracking**: Fetches upcoming assignment deadlines directly from the Moodle timeline.
*   **ReAct Agent**: Uses a reasoning loop (LangChain) to decide whether to call scraping tools or answer from general knowledge.
*   **Local Inference**: Runs entirely on your machine using Ollama, ensuring no data is sent to third-party APIs.

## Installation

### 1. Prerequisites
*   **Python 3.8+**
*   **Ollama**: Download from [ollama.com](https://ollama.com/download).

### 2. Setup the Environment

Clone the repository and create a virtual environment if desired:

```bash
# Clone or download the project files
git clone https://github.com/Alan-Casasnovas0/LLM-GenAI-ESILV-Smart-Assistant
cd LLM-GenAI-ESILV-Smart-Assistant

# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

Install the required Python packages and the Playwright browser binaries:

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Setup Ollama

Start the Ollama server in a terminal:

```bash
ollama serve
```

In a separate terminal, pull the recommended model (see *Recommended Models* section below):

```bash
ollama pull mistral
```

## Usage

### 1. Configure Credentials
Launch the application:

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`. You will be prompted to enter your De Vinci credentials in the sidebar. 
These are stored locally in your browser session and are not uploaded.

### 2. Select a Model
In the sidebar, select your preferred model from the dropdown menu. The agent will be re-initialized automatically when you change models.

### 3. Interact
Ask natural language questions such as:
*   "List all my courses related to Data science."
*   "When is my next deadline?"
*   "Which courses do I still have to work on?"

## Architecture

The application follows a **ReAct (Reasoning + Acting)** pattern:

1.  **Input**: The user asks a question (e.g., "What courses do I have?").
2.  **Thought**: The Agent analyzes the question.
3.  **Action**: The Agent calls the relevant tools:
    *   `get_courses()`: Scrapes the Moodle dashboard in **Summary View** to retrieve all enrolled courses.
    *   `get_deadlines()`: Scrapes the Moodle timeline for assignments.
4.  **Observation**: The tools return raw data (Course Name, Category, Progress, Deadline dates).
5.  **Thought**: The Agent processes the raw data to find matches (e.g., filtering courses by keyword).
6.  **Output**: The Agent generates a natural language response based *only* on the retrieved data.

## Configuration

### Changing the Ollama Server
By default, the app connects to `http://localhost:11434`. To change this, modify the `OLLAMA_BASE_URL` variable at the top of `app.py` or set the `OLLAMA_HOST` environment variable.

### Updating Selectors
Moodle updates frequently. If the scraper returns no courses, the CSS selectors in `scraper.py` (specifically inside `get_course_list`) may need to be updated to match the new Moodle layout.

## Project Structure

```text
.
├── app.py              # Streamlit web interface and session management
├── agent.py            # LangChain ReAct Agent and LLM initialization
├── tools.py            # Python functions for the Agent (get_courses, get_deadlines)
├── scraper.py          # Playwright logic for scraping Moodle (forces Course Summary View)
├── requirements.txt    # Python dependencies
└── README.md           
```

## License

Project for ESILV A5 - LLM & GenAI