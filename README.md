# Pitch Deck Analyzer

A powerful web application built with FastAPI and crewAI for analyzing startup pitch decks using AI agents. This tool helps investors and analysts evaluate pitch decks by providing comprehensive analysis, industry research, and due diligence reports.

## Features

- **Modern Web Interface**
  - Responsive design with Tailwind CSS
  - Real-time progress tracking
  - Drag-and-drop file upload
  - Interactive progress visualization
  - Toast notifications
  - Beautiful animated UI elements

- **Document Analysis**
  - Support for PDF and PPT/PPTX files
  - Automatic text extraction
  - Smart content analysis

- **Multi-Agent Analysis**
  - Pitch Deck Analyst: Evaluates business model, financials, and team
  - Industry Researcher: Analyzes market trends and competition
  - Due Diligence Analyst: Validates claims and identifies risks

- **Real-time Updates**
  - WebSocket-based progress tracking
  - Detailed task progress logging
  - Elapsed time monitoring
  - Status notifications

## Installation

1. Ensure you have Python >=3.10 <3.13 installed.

2. Clone the repository and set up your virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install uv
   uv pip install -e .
   ```

4. Set up environment variables:
   - Create a `.env` file in the project root
   - Add your OpenAI API key:
     ```
     OPENAI_API_KEY=your_key_here
     ```

## Usage

1. Start the server:
   ```bash
   uvicorn pitch.api:app --reload --host 0.0.0.0 --port 8000
   ```

2. Open your browser and navigate to `http://localhost:8000`

3. Enter your startup name and upload your pitch deck (PDF/PPT/PPTX)

4. Monitor the analysis progress in real-time

5. View and download the comprehensive analysis report

## Project Structure

```
src/pitch/
├── api.py          # FastAPI application and endpoints
├── crew.py         # AI agents configuration and crew setup
├── status_manager.py # WebSocket-based status updates
├── config/         # YAML configurations for agents and tasks
├── static/         # Web interface files (HTML, CSS, JS)
└── tools/          # Analysis tools and utilities
```

## Configuration

- Modify `src/pitch/config/agents.yaml` to customize agent behaviors
- Adjust `src/pitch/config/tasks.yaml` to define analysis tasks
- Update `src/pitch/crew.py` to add custom tools or modify agent logic
- Fine-tune the UI in `src/pitch/static/`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For questions or feedback:
- Check out [crewAI documentation](https://docs.crewai.com)
