import time
from .retriever import Retriever, VanillaRetriever
from .generator import generator_registry
from .schemas import SearchHit, GeneratorResponse
from .logger_setup import logger
from typing import List
from .config import settings

class Pipeline:
    """A simple pipeline to execute a sequence of steps with timing."""
    def __init__(self):
        self.settings = settings

    def ask(self, query: str, model:str=None, is_vanilla: bool=False) -> GeneratorResponse:
        """Run the pipeline with the given query and return the result."""
        if not model:
            logger.warning("[Engine] No specific model provided. Using default generator.")
            generator = generator_registry.get_generator("default")
        else:
            logger.info(f"[Engine] Using model '{model}' for generation.")
            generator= generator_registry.get_generator(model)

        mode_str = "VANILLA" if is_vanilla else "ADVANCED"
        logger.info(f"[Engine] Received query: '{query}'. Starting pipeline execution in {mode_str} mode...")

        try:
            start_time = time.time()
            if is_vanilla:
                active_retriever = VanillaRetriever()
            else:
                active_retriever = Retriever()
            # Step 1: Retrieval
            sources: List[SearchHit] = active_retriever.search(query)

            # Step 2: Generation
            if not sources:
                logger.warning("[Engine] No relevant sources found for the given query.")
                return GeneratorResponse(
                    query=query,
                    summary="Không tìm thấy nguồn tin nào liên quan đến câu hỏi của bạn.",
                    results=[],
                    total=0,
                    duration_ms=(time.time() - start_time) * 1000
                )
            else:
                answer = generator.generate(query, sources, is_vanilla=is_vanilla)
                duration_ms = (time.time() - start_time) * 1000
                return GeneratorResponse(
                    query=query,
                    summary=answer,
                    results=sources,
                    total=len(sources),
                    duration_ms=round(duration_ms, 2)
                )
        except Exception as e:
            logger.exception("Pipeline execution failed")
            return GeneratorResponse(
                query=query,
                summary=None,
                results=[],
                total=0,
                duration_ms=0.0
            )
        
    def generate_response(self, query: str, model: str = "default") -> GeneratorResponse:
        """Run the pipeline with the given query, retrieval, and generation with fallback."""
        logger.info(f"[Engine] Received query: '{query}'. Starting pipeline execution with fallback...")
        if not model:
            logger.warning("[Engine] No specific model provided. Using default generator.")
        else:
            logger.info(f"[Engine] Using model '{model}' for generation.")
        try:
            start_time = time.time()
            
            active_retriever = Retriever()
                
            sources: List[SearchHit] = active_retriever.search(query)

            if not sources:
                logger.warning("[Engine] No relevant sources found for the given query.")
                return GeneratorResponse(
                    query=query,
                    summary="Không tìm thấy nguồn tin nào liên quan đến câu hỏi của bạn.",
                    results=[],
                    total=0,
                    duration_ms=round((time.time() - start_time) * 1000, 2)
                )

            answer = generator_registry.generate_with_fallback(
                query=query,
                search_hits=sources,
                identifier=model,
                fallback_identifiers=None,
                is_vanilla=False
            )

            duration_ms = (time.time() - start_time) * 1000
            return GeneratorResponse(
                query=query,
                summary=answer,
                results=sources,
                total=len(sources) if sources else 0,
                duration_ms=round(duration_ms, 2)
            )

        except Exception as e:
            logger.exception(f"[Engine] Pipeline execution failed critically: {e}")
            return GeneratorResponse(
                query=query,
                summary="Xin lỗi, hệ thống AI hiện tại đang gặp sự cố và không thể tạo câu trả lời. Vui lòng thử lại sau.",
                results=[],
                total=0,
                duration_ms=0.0
            )
