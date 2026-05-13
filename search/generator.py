from abc import ABC, abstractmethod
from typing import List, Type, Dict
from .logger_setup import logger
import threading
import re

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama.chat_models import ChatOllama
from langchain_groq import ChatGroq
from langchain_nvidia_ai_endpoints import ChatNVIDIA


from .config import settings, LLMInstanceConfig
from .schemas import SearchHit
from .prompts import (
    NEWS_RAG_SYSTEM_PROMPT, NEWS_RAG_HUMAN_PROMPT,
    VANILLA_SYSTEM_PROMPT, VANILLA_HUMAN_PROMPT
)

"""
This module defines the generator classes responsible for generating responses based on search hits and user queries. It includes implementations for different LLM providers such as OpenAI, Google, Groq, and a local model via Ollama. The GeneratorRegistry class manages the available generator instances based on the configuration settings.
The generators utilize LangChain's prompt templates and output parsers to structure the input and output for the LLMs. Each generator handles the specific requirements for its respective provider, including API keys, base URLs, and model configurations. The module also includes error handling and logging to ensure robustness during the generation process.
"""

# ---------------------------- Abstract Base Generator ----------------------------
class BaseGenerator(ABC):
    """Abstract base class for generators."""
    def __init__(self, config: LLMInstanceConfig = None):
        try:
            if not config:
                logger.error(f"[Generator] Invalid configuration provided. 'config' is required.")
                raise ValueError("Invalid configuration: 'config' is required for Generator.")
            self._config = config
            self._llm = self._init_llm()
            if not self._llm:
                self.chain = None
                self._vanilla_chain = None
                logger.error(f"[{self._config.name.upper()}] LLM was not initialized. Chain is unavailable.")
            self._prompt_template = ChatPromptTemplate.from_messages([
                ("system", NEWS_RAG_SYSTEM_PROMPT),
                ("human", NEWS_RAG_HUMAN_PROMPT)
            ])
            self._chain = self._prompt_template | self._llm | StrOutputParser()

            self._vanilla_prompt_template = ChatPromptTemplate.from_messages([
                    ("system", VANILLA_SYSTEM_PROMPT),
                    ("human", VANILLA_HUMAN_PROMPT)
                ])
            self._vanilla_chain = self._vanilla_prompt_template | self._llm | StrOutputParser()
        except Exception as e:
            logger.error(f"[Generator] Failed to initialize BaseGenerator: {e}")
            raise RuntimeError(f"Failed to initialize BaseGenerator: {e}")
    
    @abstractmethod
    def _init_llm(self):
        """Optional method to set up LLM and prompt chain, can be overridden by subclasses."""
        pass

    def _format_context(self, sources: List[SearchHit]) -> str:
        """Formats the search hits into a string context for the prompt."""
        return "\n\n".join([
            f"[{i+1}] {s.title}: {s.content}\nSource: {s.url}" 
            for i, s in enumerate(sources)
        ])
    
    def _clean_response(self, text: str) -> str:
        """Helper aims to remove the <think>...</think> from the response."""
        if text:
            cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
            return cleaned_text.strip()
        return text

    def generate(self, query: str, search_hits: List[SearchHit], is_vanilla: bool = False) -> str:
        """Generates a response based on the query and search hits."""
        try:
            mode_str = "VANILLA" if is_vanilla else "ADVANCED"
            logger.info(f"[{self._config.name.upper()}Generator] Generating response in {mode_str} mode...")

            if not search_hits:
                logger.warning(f"[{self._config.name.upper()}Generator] No relevant sources found for the given query.")
                return "Không tìm thấy nguồn tin nào liên quan đến câu hỏi của bạn. Vui lòng thử lại với câu hỏi khác hoặc kiểm tra lại kết quả tìm kiếm."
        
            context = self._format_context(search_hits)
            
            active_chain = self._vanilla_chain if is_vanilla else self._chain
            
            if not active_chain:
                logger.error(f"[{self._config.name.upper()}Generator] Cannot generate: LLM Chain is None.")
                return "Lỗi hệ thống: Không thể kết nối với mô hình AI."

            answer = active_chain.invoke({"context": context, "question": query})
            if not answer:
                logger.warning(f"[{self._config.name.upper()}Generator] Received empty response, retrying...")
                answer = active_chain.invoke({"context": context, "question": query})

            answer = self._clean_response(answer)
            return answer
            
        except Exception as e:
            logger.error(f"[{self._config.name.upper()}Generator] Error during generation: {e}")
            raise RuntimeError(f"Error during generation: {e}")
    
    def cleanup(self):
        """Optional method to clean up resources, can be overridden by subclasses."""
        logger.info(f"[{self._config.name.upper()}Generator] Cleaning up resources...")
        self._llm = None
        self._chain = None
        self._vanilla_chain = None

# ---------------------------- Concrete Generators ----------------------------
class OpenAIGenerator(BaseGenerator):
    """Concrete implementation of BaseGenerator using OpenAI's API."""
    def _init_llm(self):
        """Initializes the LLM and prompt chain."""
        try: 
            logger.info(f"[{self._config.name.upper()}Generator] Initializing LLM and prompt chain...")
            return ChatOpenAI(
                model=self._config.model_id,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
                api_key=self._config.api_key,
                base_url=self._config.base_url if self._config.base_url else None
            )
        except Exception as e:
            logger.error(f"[{self._config.name.upper()}Generator] Failed to initialize LLM chain: {e}")
            raise RuntimeError(f"[{self._config.name.upper()}Generator] Failed to initialize LLM chain: {e}")

class OllamaGenerator(BaseGenerator):
    """Concrete implementation of BaseGenerator using a local model via Ollama."""
    def _init_llm(self):
        """Initializes the Ollama LLM."""
        try:
            return ChatOllama(
                model=self._config.model_id,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
                api_key=self._config.api_key,
                base_url=self._config.base_url if self._config.base_url else "http://localhost:11434"
            )
        except Exception as e:
            logger.error(f"[OllamaGenerator] Failed to initialize LLM chain: {e}")
            raise RuntimeError(f"[{self._config.name.upper()}Generator] Failed to initialize LLM chain: {e}")

class GoogleGenerator(BaseGenerator):
    """Concrete implementation of BaseGenerator using Google's Gemini model."""
    def _init_llm(self):
        """Initializes the Google LLM."""
        try:
            logger.info(f"[{self._config.name.upper()}Generator] Initializing Google LLM and prompt chain...")
            return ChatGoogleGenerativeAI(
                model=self._config.model_id,
                temperature=self._config.temperature,
                max_output_tokens=self._config.max_tokens,
                google_api_key=self._config.api_key,
                base_url=self._config.base_url if self._config.base_url else None
            )
        except Exception as e:
            logger.error(f"[{self._config.name.upper()}Generator] Failed to initialize LLM chain: {e}")
            raise RuntimeError(f"[{self._config.name.upper()}Generator] Failed to initialize LLM chain: {e}")

class GroqGenerator(BaseGenerator):
    """Concrete implementation of BaseGenerator using Groq's API."""
    def _init_llm(self):
        """Initializes the Groq LLM."""
        try:
            logger.info(f"[{self._config.name.upper()}Generator] Initializing Groq LLM and prompt chain...")
            return ChatGroq(
                model=self._config.model_id,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
                api_key=self._config.api_key
            )
        except Exception as e:
            logger.error(f"[{self._config.name.upper()}Generator] Failed to initialize LLM chain: {e}")
            raise RuntimeError(f"[{self._config.name.upper()}Generator] Failed to initialize LLM chain: {e}")
        
class NvidiaGenerator(BaseGenerator):
    """Concrete implementation of BaseGenerator using Nvidia's API."""
    def _init_llm(self):
        """Initializes the Nvidia LLM."""
        try:
            logger.info(f"[{self._config.name.upper()}Generator] Initializing Nvidia LLM and prompt chain...")
            return ChatNVIDIA(
                model=self._config.model_id,
                nvidia_api_key=self._config.api_key,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens
            )
        except Exception as e:
            logger.error(f"[{self._config.name.upper()}Generator] Failed to initialize LLM chain: {e}")
            raise RuntimeError(f"[{self._config.name.upper()}Generator] Failed to initialize LLM chain: {e}")

    
class GeneratorRegistry:
    """Registry to manage and retrieve generator instances."""
    _instances = None
    _lock = threading.Lock()
    _is_initialized = False

    _PROVIDER_MAP: Dict[str, Type[BaseGenerator]] = {
        "openai": OpenAIGenerator,
        "google": GoogleGenerator,
        "groq": GroqGenerator,
        "ollama": OllamaGenerator,
        "nvidia": NvidiaGenerator,
        "siliconflow": OpenAIGenerator
    }

    def __new__(cls):
        if cls._instances is None:
            with cls._lock:
                if cls._instances is None:
                    cls._instances = super().__new__(cls)
                    cls._instances._is_initialized = False
        return cls._instances

    def __init__(self):
        """Initializes the generator registry."""
        if self._is_initialized:
            return

        with self._lock:
            if not self._is_initialized:
                self._generators: Dict[str, BaseGenerator] = {}
                self._setup()
                self._is_initialized = True

    def _setup(self):
        """Initializes the generator instances based on the settings."""
        self._id_map: Dict[str, str] = {}

        for cfg in settings.llm.instances:
            provider_class = self._PROVIDER_MAP.get(cfg.provider.lower())
            if provider_class:
                try:
                    gen_instance = provider_class(cfg)
                    self._generators[cfg.name] = gen_instance
                    self._id_map[cfg.model_id] = cfg.name
                    logger.info(f"[GeneratorRegistry] Generator Registered: {cfg.name} (ID: {cfg.model_id}) using provider '{cfg.provider}'")
                except Exception as e:
                    logger.error(f"[GeneratorRegistry] Failed to initialize generator for '{cfg.name}': {e}")
            else:
                logger.warning(f"[GeneratorRegistry] Unsupported provider '{cfg.provider}' for instance '{cfg.name}'. Skipping registration.")

    def get_generator(self, identifier: str = 'default') -> BaseGenerator:
        """Retrieves a generator instance by its name or its model id."""
        # If no generators are registered, raise an error
        if not self._generators:
            logger.error("[GeneratorRegistry] No generators are registered in the registry.")
            raise ValueError("No generators are registered in the registry.")
        
        # If no specific identifier is provided, return the first generator in the registry
        if (identifier == 'default' and 'default' not in self._generators) or not identifier:
            logger.warning("[GeneratorRegistry] No specific generator identifier provided. Returning the first place generator instead.")
            first_name = next(iter(self._generators))
            return self._generators[first_name]

        # First try to find by name
        if identifier in self._generators:
            return self._generators[identifier]
        
        # Then try to find by model_id
        name_from_id = self._id_map.get(identifier)
        if name_from_id:
            return self._generators[name_from_id]

        # If not found, log an error and raise an exception
        logger.error(f"[GeneratorRegistry] Generator with identifier '{identifier}' not found in registry.")
        raise ValueError(
            f"[GeneratorRegistry] Generator with identifier '{identifier}' not found. \n",
            f"Available generators: {list(self._generators.keys())}.\n",
            f"Available model IDs: {list(self._id_map.keys())}.\n"
        )

    def generate_with_fallback(self, query: str, search_hits: List[SearchHit], 
                               identifier: str = 'default', fallback_identifiers: List[str] = None, 
                               is_vanilla: bool = False) -> str:
        primary_name = None
        
        try:
            if not search_hits or len(search_hits) == 0:
                logger.warning(f"[Generator] No relevant sources found for the given query.")
                return "Không tìm thấy nguồn tin nào liên quan đến câu hỏi của bạn. Vui lòng thử lại với câu hỏi khác hoặc kiểm tra lại kết quả tìm kiếm."
            
            primary_gen = self.get_generator(identifier)
            primary_name = next((name for name, gen in self._generators.items() if gen == primary_gen), identifier)
            return primary_gen.generate(query, search_hits, is_vanilla)
        except Exception as e:
            logger.error(f"[Generator] Error during generation: {e}")
        
        if fallback_identifiers is None:
            fallback_identifiers = list(self._generators.keys())
            
        for fallback_id in fallback_identifiers:
            if fallback_id == primary_name:
                continue
            
            try:
                logger.info(f"[GeneratorRegistry] Attempting fallback using generator '{fallback_id}'...")
                fallback_gen = self.get_generator(fallback_id)
                return fallback_gen.generate(query, search_hits, is_vanilla)
            except Exception as fallback_error:
                logger.warning(f"[GeneratorRegistry] Fallback generator '{fallback_id}' failed or not found: {fallback_error}. Skipping to next...")
                continue

        error_msg = "Xin lỗi, hệ thống AI hiện tại đang gặp sự cố và không thể tạo câu trả lời. Vui lòng thử lại sau."
        logger.error("[GeneratorRegistry] All generators (primary and fallbacks) failed to generate a response.")
        return error_msg
            

        
    
    def unregister_generator(self, identifier: str):
        """Unregisters a generator instance by its name."""
        try: 
            target_name = None
            target_id = None 

            if identifier in self._generators:
                target_name = identifier
                for mid, name in self._id_map.items():
                    if name == target_name:
                        target_id = mid
                        break
            elif identifier in self._id_map:
                target_id = identifier
                target_name = self._id_map[identifier]
                
            if target_name:
                with self._lock:
                    if target_name in self._generators:
                        self._generators[target_name].cleanup()
                        del self._generators[target_name]
                    if target_id and target_id in self._id_map:
                        del self._id_map[target_id]
                logger.info(f"[GeneratorRegistry] Unregistered generator '{target_name}' with ID '{target_id}'.")
            else:
                logger.warning(f"[GeneratorRegistry] Attempted to unregister non-existent generator '{identifier}'.")
        except Exception as e:
            logger.error(f"[GeneratorRegistry] Error while unregistering generator '{identifier}': {e}")
            raise RuntimeError(f"Error while unregistering generator '{identifier}': {e}")

    def list_generators(self) -> List[Dict[str, str]]:
        """Lists all registered generators with their provider types."""
        results = []
        for name, gen in self._generators.items():
            model_id = "N/A"
            for mid, mname in self._id_map.items():
                if mname == name:
                    model_id = mid
                    break
            results.append({
                "name": name,
                "model_id": model_id,
                "provider": gen._config.provider,
                "class": gen.__class__.__name__
            })
        return results

generator_registry = GeneratorRegistry()
