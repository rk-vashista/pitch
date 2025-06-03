from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List, Callable, Any
from langchain_openai import ChatOpenAI
import asyncio
from datetime import datetime
from .tools.document_tools import DocumentParserTool
from .tools.serper_tool import WebResearchTool
from .tools.knowledge_base import KnowledgeBaseTool
from .status_manager import status_manager

@CrewBase
class Pitch():
    """Pitch crew for analyzing startup pitch decks"""

    agents: List[BaseAgent]
    tasks: List[Task]

    def __init__(self):
        super().__init__()
        self.llm = ChatOpenAI(
            model_name="gpt-4-turbo-preview",
            temperature=0.7,
        )

    @agent
    def pitch_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['pitch_analyzer'],
            llm=self.llm,
            verbose=True,
            tools=[DocumentParserTool(), KnowledgeBaseTool()]
        )

    @agent 
    def market_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['market_researcher'],
            llm=self.llm,
            verbose=True,
            tools=[WebResearchTool(), KnowledgeBaseTool()]
        )

    @agent
    def financial_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['financial_analyst'],
            llm=self.llm,
            verbose=True,
            tools=[KnowledgeBaseTool()]
        )

    @agent
    def website_social_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['website_social_analyst'],
            llm=self.llm,
            verbose=True,
            tools=[WebResearchTool(), KnowledgeBaseTool()]
        )

    @agent
    def investment_strategist(self) -> Agent:
        return Agent(
            config=self.agents_config['investment_strategist'],
            llm=self.llm,
            verbose=True,
            tools=[KnowledgeBaseTool()]
        )

    @agent
    def due_diligence_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['due_diligence_analyst'],
            llm=self.llm,
            verbose=True,
            tools=[KnowledgeBaseTool(), WebResearchTool()]
        )

    @task
    def pitch_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['pitch_analysis_task'],
            context_format=True
        )

    @task
    def market_research_task(self) -> Task:
        return Task(
            config=self.tasks_config['market_research_task'],
            context_format=True
        )

    @task
    def financial_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['financial_analysis_task'],
            context_format=True
        )

    @task
    def website_social_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['website_social_analysis_task'],
            context_format=True
        )

    @task
    def investment_strategy_task(self) -> Task:
        return Task(
            config=self.tasks_config['investment_strategy_task'],
            context_format=True
        )

    @task
    def due_diligence_task(self) -> Task:
        return Task(
            config=self.tasks_config['due_diligence_task'],
            context_format=True,
            output_file='report.md'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Pitch crew for analyzing pitch decks"""
        async def status_callback(event_type: str, event_data: dict):
            if 'job_id' in event_data:
                # Convert any non-serializable output to string
                output = event_data.get('output', '')
                if output and not isinstance(output, (str, int, float, bool, list, dict)):
                    output = str(output)

                status_data = {
                    "status": "in_progress",
                    "type": event_type,
                    "message": str(event_data.get('message', 'Processing...')),
                    "progress": event_data.get('progress'),
                    "timestamp": event_data.get('timestamp', ''),
                    "agent": str(event_data.get('agent', '')),
                    "task": str(event_data.get('task', '')),
                    "output": output
                }
                await status_manager.broadcast_status(event_data['job_id'], status_data)

        def task_started(task: Task) -> None:
            asyncio.create_task(status_callback('task_started', {
                'job_id': task.context.get('job_id'),
                'message': f"Starting task: {task.description[:100]}...",
                'agent': task.agent.name,
                'task': task.description,
                'timestamp': datetime.now().isoformat()
            }))

        def task_completed(task: Task) -> None:
            asyncio.create_task(status_callback('task_completed', {
                'job_id': task.context.get('job_id'),
                'message': f"Completed task: {task.description[:100]}...",
                'agent': task.agent.name,
                'task': task.description,
                'output': task.output,
                'timestamp': datetime.now().isoformat()
            }))

        return Crew(
            agents=[
                self.pitch_analyzer(),
                self.market_researcher(),
                self.financial_analyst(),
                self.website_social_analyst(),
                self.investment_strategist(),
                self.due_diligence_analyst()
            ],
            tasks=[
                self.pitch_analysis_task(),
                self.market_research_task(),
                self.financial_analysis_task(),
                self.website_social_analysis_task(),
                self.investment_strategy_task(),
                self.due_diligence_task()
            ],
            process=Process.sequential,
            verbose=True,
            task_started_callback=task_started,
            task_completed_callback=task_completed
        )
