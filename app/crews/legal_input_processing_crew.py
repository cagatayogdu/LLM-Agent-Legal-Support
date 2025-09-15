from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from llms import _create_gpt

@CrewBase
class LegalInputProcessingCrew:
    agents_config = '../config/agents.yaml'
    tasks_config = '../config/tasks.yaml'
    
    def __init__(self):
        self.llm = _create_gpt()
        
    @agent
    def _legal_text_clarifier_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['legal_text_clarifier'],
            llm=self.llm,
            tools=[],
            verbose=True,
        )

    @task
    def _clarify_legal_text(self) -> Task:
        return Task(
            config=self.tasks_config["legal_text_clarifier"],
            agent=self._legal_text_clarifier_agent(),
        )
    
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            name="Legal Input Processing Crew",
            process=Process.sequential,
            max_rpm=10,
            verbose=True,
            memory=False,
            cache=True,
        )