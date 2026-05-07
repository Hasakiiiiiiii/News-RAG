import gc
import threading

from typing import List
from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex,  QueryBundle #,Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core import Settings as LlamaSettings

from .config import settings
from .logger_setup import logger
from .schemas import SearchHit

import torch

class Retriever:
    """
    Handles Advanced Retrieval: Hybrid Search (Vector + Sparse) followed by Reranking.
    """

    _instance = None
    _lock = threading.Lock()
    _is_initialized = False

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                if settings is None:
                    logger.error("[Retriever] Settings must be provided for Retriever initialization.")
                    raise ValueError("[Retriever] Settings cannot be None.")
                
                cls._instance = super(Retriever, cls).__new__(cls)
                logger.info("[Retriever] Creating a new instance of Retriever.")

        return cls._instance
    

    def __init__(self):
        with self.__class__._lock:
            if self._is_initialized:
                return 
            
            logger.info("[Retriever] Initializing Retriever instance.")
            
            if settings is None:
                logger.error("[Retriever] Settings must be provided for Retriever initialization.")
                raise ValueError("[Retriever] Settings cannot be None.")
            
            self.settings = settings
            self._initialize_retriever_models()
            self.__class__._is_initialized = True

    def _initialize_retriever_models(self):
        """Initializes the retriever models and Qdrant client."""
        try:
            logger.info("[Retriever] Initializing retriever...")
        
            # Initialize embedding model
            logger.info(f"[Retriever] Initializing embedding model: {self.settings.model.embedding}")   
            self.embedding_model = HuggingFaceEmbedding(
                model_name=self.settings.model.embedding,
                model_kwargs={
                    "trust_remote_code": True,
                    "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32
                },
                normalize=True,
                cache_folder="./model_cache/embeddings",
                query_instruction="Represent this query for retrieval:",
                text_instruction="Represent this text for retrieval:"
            )
            LlamaSettings.embed_model = self.embedding_model
            LlamaSettings.llm = None

            logger.info(f"[Retriever] Initialized embedding model: {self.settings.model.embedding}")

            # Initialize Reranker
            logger.info(f"[Retriever] Initializing Reranker model: {self.settings.model.reranking}")
            self.reranker = SentenceTransformerRerank(
                model=self.settings.model.reranking,
                top_n=self.settings.model.top_k_rerank,
                keep_retrieval_score=True,
                trust_remote_code=True
            )
            logger.info(f"[Retriever] Initialized Reranker model: {self.settings.model.reranking}")
            
            # Connecting to Qdrant Vector Database
            logger.info(f"[Retriever] Connecting to Qdrant at {self.settings.search.qdrant_url}:{self.settings.search.grpc_port}")
            self.qdrant_client = QdrantClient(
                url=self.settings.search.qdrant_url, 
                port=self.settings.search.port,
                api_key=self.settings.search.api_key,
                grpc_port=self.settings.search.grpc_port,
                timeout=60
            )
            self.vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=self.settings.search.collection_name,
                enable_hybrid=True,
                dense_vector_name="dense",
                sparse_vector_name="sparse",
                text_key="content",
            )
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                embed_model=self.embedding_model
            )
            self.retriever = self.index.as_retriever(
                similarity_top_k=self.settings.model.top_k,
                vector_store_kwargs={"hybrid": True}
            )
            logger.info(f"[Retriever] Connected to Qdrant at {self.settings.search.qdrant_url}:{self.settings.search.grpc_port}")
            logger.info("[Retriever] Retriever heavy components initialized successfully.")
        except Exception as e:
            logger.error(f"[Retriever] Error initializing retriever models: {e}")
            raise e
        
    def search(self, query: str) -> List[SearchHit]:
        """Performs a search query (Hybrid Search + Reranking) and returns a list of SearchHit objects."""
        try:
            logger.info(f"[Retriever] Performing search for query: {query}")

            query_bundle = QueryBundle(query_str=query)
            # 1. Retrieve initial results using hybrid search
            retrieved_nodes = self.retriever.retrieve(query_bundle)
            # 2. Reranking top results using the Reranker model
            if retrieved_nodes:
                logger.info(f"[Retriever] Reranking retrieved results to get top {self.settings.model.top_k_rerank}...")
                reranked_results = self.reranker.postprocess_nodes(
                    nodes=retrieved_nodes,
                    query_bundle=query_bundle
                    )
                logger.info("[Retriever] Reranking completed.")
            else:
                reranked_results = []
                logger.info("[Retriever] No results to rerank.")

            search_hits = []
            for result in reranked_results:
                node= result.node
                metadata = node.metadata if hasattr(node, "metadata") else {}
                hit = SearchHit(
                    id=node.id_ if hasattr(node, "id_") else "unknown",
                    title=str(metadata.get("title") or "No Title"),
                    content=str(metadata.get("content") or node.text),
                    url=str(metadata.get("url") or "#"),
                    score=result.score if result.score is not None else 0.0,
                    metadata={k: v for k, v in metadata.items() 
                              if k not in {"title", "url", "content"}
                              }
                )
                search_hits.append(hit)
            
            return search_hits
        except Exception as e:
            logger.error(f"[Retriever] Search failed for query '{query}': {e}")
            return []
        
    @classmethod
    def clear_instance(cls):
        """Clears the singleton instance and releases memory of heavy models."""
        if cls._instance:
            logger.info("[Retriever] Clearing Retriever instance and releasing memory...")
            
            if hasattr(cls._instance, 'retriever'):
                del cls._instance.retriever
            if hasattr(cls._instance, 'reranker'):
                del cls._instance.reranker
            
            LlamaSettings.embed_model = None
            LlamaSettings.llm = None
            
            cls._instance = None
            cls._is_initialized = False

            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                
            logger.info("[Retriever] Memory cleared successfully. System is clean.")
        
class VanillaRetriever:
    """
    Handles Baseline Retrieval: Vanilla RAG (Dense Vector Search ONLY, No Reranking).
    Lấy cố định Top 5 kết quả cao nhất.
    """

    _instance = None
    _lock = threading.Lock()
    _is_initialized = False

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                if settings is None:
                    logger.error("[VanillaRetriever] Settings must be provided for initialization.")
                    raise ValueError("[VanillaRetriever] Settings cannot be None.")
                
                cls._instance = super(VanillaRetriever, cls).__new__(cls)
                logger.info("[VanillaRetriever] Creating a new instance of VanillaRetriever.")

        return cls._instance

    def __init__(self):
        with self.__class__._lock:
            if self._is_initialized:
                return 
            
            logger.info("[VanillaRetriever] Initializing VanillaRetriever instance.")
            
            self.settings = settings
            self._initialize_retriever_models()
            self.__class__._is_initialized = True

    def _initialize_retriever_models(self):
        """Initializes ONLY the embedding model and dense Qdrant client."""
        try:
            logger.info("[VanillaRetriever] Initializing baseline retriever...")
        
            # 1. Chỉ khởi tạo Embedding Model 
            logger.info(f"[VanillaRetriever] Initializing embedding model: {self.settings.model.embedding}")   
            self.embedding_model = HuggingFaceEmbedding(
                model_name=self.settings.model.embedding,
                model_kwargs={
                    "trust_remote_code": True,
                    "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32
                },
                normalize=True,
                cache_folder="./model_cache/embeddings",
                query_instruction="Represent this query for retrieval:",
                text_instruction="Represent this text for retrieval:"
            )
            LlamaSettings.embed_model = self.embedding_model
            LlamaSettings.llm = None

            # 2. Kết nối Qdrant nhưng CHỈ dùng Dense Vector
            logger.info(f"[VanillaRetriever] Connecting to Qdrant at {self.settings.search.qdrant_url}:{self.settings.search.grpc_port}")
            self.qdrant_client = QdrantClient(
                url=self.settings.search.qdrant_url, 
                port=self.settings.search.port,
                api_key=self.settings.search.api_key,
                grpc_port=self.settings.search.grpc_port,
                timeout=60
            )
            
            self.vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=self.settings.search.collection_name,
                enable_hybrid=False,          # <--- Đổi thành False
                dense_vector_name="dense",   
                text_key="content",
            )
            
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                embed_model=self.embedding_model
            )
            
            # 3. Cấu hình lấy chuẩn Top 5 và tắt tham số hybrid
            self.retriever = self.index.as_retriever(
                similarity_top_k=5,           
            )
            
            logger.info("[VanillaRetriever] Baseline components initialized successfully.")
        except Exception as e:
            logger.error(f"[VanillaRetriever] Error initializing models: {e}")
            raise e
        
    def search(self, query: str) -> List[SearchHit]:
        """Performs a standard Dense Search and returns Top 5 SearchHit objects."""
        try:
            logger.info(f"[VanillaRetriever] Performing baseline search for query: {query}")

            query_bundle = QueryBundle(query_str=query)
            
            # 1. Retrieve initial results (Dense Only)
            retrieved_nodes = self.retriever.retrieve(query_bundle)
            
            print(f"\n[DEBUG VANILLA] Lấy được {len(retrieved_nodes)} kết quả từ Qdrant (Dense Only)")

            # 2. Mapping thẳng kết quả sang SearchHit
            search_hits = []
            for result in retrieved_nodes:
                node = result.node
                metadata = node.metadata if hasattr(node, "metadata") else {}
                hit = SearchHit(
                    id=node.id_ if hasattr(node, "id_") else "unknown",
                    title=str(metadata.get("title") or "No Title"),
                    content=str(metadata.get("content") or node.text),
                    url=str(metadata.get("url") or "#"),
                    score=result.score if result.score is not None else 0.0,
                    metadata={k: v for k, v in metadata.items() 
                              if k not in {"title", "url", "content"}
                              }
                )
                search_hits.append(hit)
            
            return search_hits
        
        except Exception as e:
            logger.error(f"[VanillaRetriever] Search failed for query '{query}': {e}")
            return []
        
    @classmethod
    def clear_instance(cls):
        """Clears the singleton instance and releases memory."""
        if cls._instance:
            logger.info("[VanillaRetriever] Clearing instance and releasing memory...")
            
            if hasattr(cls._instance, 'retriever'):
                del cls._instance.retriever
            
            LlamaSettings.embed_model = None
            LlamaSettings.llm = None
            
            cls._instance = None
            cls._is_initialized = False

            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                
            logger.info("[VanillaRetriever] Memory cleared successfully.")