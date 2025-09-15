from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
import sys
import os
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llms import _create_gpt
from tools.qdrant_vector_search_tool import QdrantLegalSearchTool
from crewai_tools import SerperDevTool, WebsiteSearchTool, ScrapeWebsiteTool

load_dotenv()

@CrewBase
class LegalAnalysisProcessingCrew:
    agents_config = '../config/agents.yaml'
    tasks_config = '../config/tasks.yaml'
    
    def __init__(self):
        self.feedback_suggestions = None
        self.topic = None
        self.serper_tool = SerperDevTool(
            api_key=os.getenv("SERPER_API_KEY"),
            n_results=5,
            search_type="search",
        )
        self.website_tool = WebsiteSearchTool()
        self.scrape_tool = ScrapeWebsiteTool()
        self.llm = _create_gpt()

    @agent
    def _case_law_rag_analyzer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["case_law_rag_analyzer"],
            llm=self.llm,
            verbose=True,
            tools=[QdrantLegalSearchTool()]
        )
    
    @agent
    def _legal_precedent_web_scanner_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["legal_precedent_web_scanner"],
            llm=self.llm,
            verbose=True,
            tools=[self.serper_tool, self.website_tool, self.scrape_tool]
        )
    
    @agent
    def _contradiction_detector_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["contradiction_detector"],
            llm=self.llm,
            verbose=True,
            tools=[]
        )
    
    @task
    def _analyze_case_law_rag(self) -> Task:
        return Task(
            config=self.tasks_config["case_law_rag_analysis_task"],
            agent=self._case_law_rag_analyzer_agent(),
        )
    
    @task
    def _search_legal_web_sources(self) -> Task:           
        return Task(
            config=self.tasks_config["legal_web_search_task"],
            agent=self._legal_precedent_web_scanner_agent(),
        )

    @task
    def _validate_legal_findings(self) -> Task:
        validation_task = Task(
            config=self.tasks_config["legal_validation_task"],
            agent=self._contradiction_detector_agent(),
            context=[
                self._analyze_case_law_rag(),
                self._search_legal_web_sources()
            ],
        )
        
        if hasattr(self, 'topic') and self.topic:
            validation_task.context_kwargs = {"topic": self.topic}
        
        return validation_task
    
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            name="Legal Analysis Crew",
            process=Process.sequential,
            verbose=True,
            memory=False,
            cache=True,
        )