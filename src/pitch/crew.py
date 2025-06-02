from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List, Callable, Any
from langchain_openai import ChatOpenAI
import asyncio
from datetime import datetime
from .tools.document_tools import DocumentParserTool
from .tools.serper_tool import WebResearchTool
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

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def pitch_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['pitch_analyzer'],
            llm=self.llm,
            verbose=True,
            tools=[DocumentParserTool()]
        )

    @agent
    def industry_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['industry_researcher'],
            llm=self.llm,
            verbose=True,
            tools=[WebResearchTool()]
        )

    @agent
    def due_diligence_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['due_diligence_analyst'],
            llm=self.llm,
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def pitch_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['pitch_analysis_task'], # type: ignore[index]
            context_format=True  # Enable context formatting for variables
        )

    @task
    def industry_research_task(self) -> Task:
        return Task(
            config=self.tasks_config['industry_research_task'], # type: ignore[index]
        )

    @task
    def due_diligence_task(self) -> Task:
        return Task(
            config=self.tasks_config['due_diligence_task'], # type: ignore[index]
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
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            task_started_callback=task_started,
            task_completed_callback=task_completed
        )
