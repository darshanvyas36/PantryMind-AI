# app/core/agents/base_agent.py
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from app.core.prompts.system_prompts import PHASE_1_SYSTEM_PROMPT
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class PantryMindChatbot:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openrouter_model,
            temperature=0.3,
            api_key=settings.openrouter_api_key or settings.gemini_api_key,
            base_url="https://openrouter.ai/api/v1",
            max_tokens=1000
        )
        
        # Modern LangChain memory setup
        self.store = {}
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", PHASE_1_SYSTEM_PROMPT),
            ("placeholder", "{chat_history}"),
            ("human", "{input}")
        ])
        
        # Create chain with memory
        self.chain = self.prompt_template | self.llm
        self.agent = RunnableWithMessageHistory(
            self.chain,
            self._get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history"
        )
    
    def _get_session_history(self, session_id: str):
        if session_id not in self.store:
            self.store[session_id] = InMemoryChatMessageHistory()
        return self.store[session_id]
    
    async def chat_async(self, user_input: str, session_id: str = "default") -> str:
        """Async chat method using modern LangChain memory"""
        try:
            response = await self.agent.ainvoke(
                {"input": user_input},
                config={"configurable": {"session_id": session_id}}
            )
            return response.content
        except Exception as e:
            logger.error(f"Async chat error: {str(e)}")
            return "I'm sorry, I'm having trouble processing your request right now. Please try again."
    
    def chat(self, user_input: str, session_id: str = "default") -> str:
        """Sync chat method for backward compatibility"""
        try:
            response = self.agent.invoke(
                {"input": user_input},
                config={"configurable": {"session_id": session_id}}
            )
            return response.content
        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            return "I'm sorry, I'm having trouble processing your request right now. Please try again."
