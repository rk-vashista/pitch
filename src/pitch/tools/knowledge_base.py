from crewai.tools import BaseTool
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
import os
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader

class KnowledgeBaseInput(BaseModel):
    """Input schema for knowledge base tool."""
    query: str = Field(..., description="Query to search in the knowledge base")

class KnowledgeBaseTool(BaseTool):
    name: str = "Knowledge Base Tool"
    description: str = (
        "Tool for searching the knowledge base containing market research, "
        "competitor analysis, industry reports, and other relevant documents"
    )
    args_schema: Type[BaseModel] = KnowledgeBaseInput
    vector_store: Optional[Any] = None

    def __init__(self):
        super().__init__()
        self._initialize_vectorstore()

    def _initialize_vectorstore(self):
        """Initialize the vector store with documents from the knowledge directory"""
        knowledge_dir = os.path.join(os.path.dirname(__file__), "../../../knowledge")
        if os.path.exists(knowledge_dir):
            loader = DirectoryLoader(knowledge_dir, glob="**/*.txt", loader_cls=TextLoader)
            documents = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            texts = text_splitter.split_documents(documents)
            
            embeddings = OpenAIEmbeddings()
            self.vector_store = FAISS.from_documents(texts, embeddings)

    def _run(self, query: str) -> str:
        """Search the knowledge base for relevant information"""
        if not self.vector_store:
            return "Knowledge base is not initialized or empty."
            
        docs = self.vector_store.similarity_search(query, k=3)
        results = []
        
        for doc in docs:
            results.append(f"Source: {doc.metadata.get('source', 'Unknown')}\n{doc.page_content}")
            
        return "\n\n---\n\n".join(results)
