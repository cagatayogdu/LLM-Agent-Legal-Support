from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from llms import _create_gpt
from dotenv import load_dotenv

load_dotenv()

@CrewBase
class LegalFeedbackCrew:
    agents_config = '../config/agents.yaml'
    tasks_config = '../config/tasks.yaml'
    
    def __init__(self):
        self.topic = None 
        self.llm = _create_gpt()

    @agent
    def _adaptive_legal_optimizer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["adaptive_legal_optimizer"],
            llm=self.llm,
            verbose=True,
            tools=[]
        )
    
    @task
    def _legal_feedback_task(self) -> Task:
        task_instance = Task(
            config=self.tasks_config["legal_feedback_task"],
            agent=self._adaptive_legal_optimizer_agent(),
        )
        
        if hasattr(self, 'topic') and self.topic:
            task_instance.context_kwargs = {"topic": self.topic}
            
        return task_instance
    
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            name="Legal Feedback Crew",
            process=Process.sequential,
            verbose=True
        )