from crewai_tools import SerperDevTool

class WebResearchTool(SerperDevTool):
    """Tool for conducting web research about startups and industries"""
    
    name: str = "Web Research"
    description: str = (
        "Tool for conducting web research about startups and industries. "
        "This tool searches the internet to find relevant information."
    )
