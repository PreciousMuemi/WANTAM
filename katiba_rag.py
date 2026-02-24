"""
Katiba AI - RAG Pipeline with Multiple Embedding & LLM Options
Supports: OpenAI, Anthropic, Gemini, Cohere, Hugging Face, Ollama
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import re

from supabase import create_client, Client
import numpy as np
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Choose embedding provider: "openai", "gemini", "huggingface", "ollama"
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gemini")
# Choose LLM provider: "claude", "gemini", "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")

TOP_K_RESULTS = 5
EMBEDDING_DIMENSIONS = 3072  # For Gemini embedding (gemini-embedding-001)

# System prompt for Claude
SYSTEM_PROMPT = """You are Katiba AI, a helpful assistant that explains Kenyan law 
to ordinary citizens in plain, simple English.

IMPORTANT INSTRUCTIONS:
1. Answer ONLY using the context provided below.
2. If the answer is not in the context, say: "I don't have that information, but you can check kenyalaw.org"
3. Always cite which document/article your answer comes from.
4. Use simple, clear language that anyone can understand.
5. Break down complex legal concepts into everyday examples.
6. Be accurate - do not invent information or interpret laws beyond what's in the context."""


@dataclass
class RetrievedChunk:
    """Container for retrieved document chunk."""
    text: str
    source_url: str
    document_title: str
    chunk_id: int
    page_number: int
    similarity_score: float


class EmbeddingGenerator:
    """Handles text embedding generation with multiple providers."""
    
    def __init__(self, provider: str = "gemini"):
        self.provider = provider
        
        if provider == "openai":
            import openai
            openai.api_key = OPENAI_API_KEY
            self.client = openai.OpenAI()
        
        elif provider == "gemini":
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY environment variable required")
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
        
        elif provider == "huggingface":
            if not HF_API_KEY:
                raise ValueError("HF_API_KEY environment variable required")
            from huggingface_hub import InferenceClient
            self.client = InferenceClient(token=HF_API_KEY)
        
        elif provider == "ollama":
            # Ollama runs locally, no key needed
            import requests
            self.ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        elif provider == "cohere":
            if not COHERE_API_KEY:
                raise ValueError("COHERE_API_KEY environment variable required")
            import cohere
            self.client = cohere.Client(COHERE_API_KEY)
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a text string."""
        try:
            if self.provider == "openai":
                response = self.client.embeddings.create(
                    input=text.strip(),
                    model="text-embedding-3-small"
                )
                return response.data[0].embedding
            
            elif self.provider == "gemini":
                try:
                    import google.genai as genai
                except ImportError:
                    import google.generativeai as genai
                result = genai.embed_content(
                    model="models/gemini-embedding-001",
                    content=text.strip()
                )
                return result['embedding']
            
            elif self.provider == "huggingface":
                response = self.client.feature_extraction(
                    text.strip(),
                    model="sentence-transformers/all-MiniLM-L6-v2"
                )
                return response[0]
            
            elif self.provider == "ollama":
                import requests
                response = requests.post(
                    f"{self.ollama_base}/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": text.strip()}
                )
                return response.json()["embedding"]
            
            elif self.provider == "cohere":
                response = self.client.embed(
                    texts=[text.strip()],
                    model="embed-english-v3.0",
                    input_type="search_document"
                )
                return response.embeddings[0]
        
        except Exception as e:
            logger.error(f"Error generating embedding with {self.provider}: {e}")
            raise


class VectorStore:
    """Handles vector storage and similarity search in Supabase."""
    
    def __init__(self, embedding_provider: str = "gemini"):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables required")
        
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.embedding_gen = EmbeddingGenerator(embedding_provider)
    
    def add_embeddings_to_documents(self):
        """Add embeddings to existing documents (one-time operation)."""
        try:
            # Fetch all documents without embeddings
            response = self.client.table("documents").select(
                "id, text, source_url, document_title, chunk_id, page_number"
            ).is_("embedding", "null").execute()
            
            documents = response.data
            logger.info(f"Found {len(documents)} documents without embeddings")
            
            if not documents:
                logger.info("All documents already have embeddings")
                return
            
            # Generate embeddings with progress bar
            updates = []
            for doc in tqdm(documents, desc="Generating embeddings"):
                embedding = self.embedding_gen.embed_text(doc["text"])
                updates.append({
                    "id": doc["id"],
                    "embedding": embedding
                })
            
            # Update documents in batches
            batch_size = 100
            for i in tqdm(range(0, len(updates), batch_size), desc="Uploading embeddings"):
                batch = updates[i:i + batch_size]
                for update in batch:
                    self.client.table("documents").update({
                        "embedding": update["embedding"]
                    }).eq("id", update["id"]).execute()
            
            logger.info(f"Added embeddings to {len(updates)} documents")
        
        except Exception as e:
            logger.error(f"Error adding embeddings: {e}")
            raise
    
    def similarity_search(self, query: str, top_k: int = TOP_K_RESULTS) -> List[RetrievedChunk]:
        """
        Search for documents similar to the query.
        
        Args:
            query: User question/search text
            top_k: Number of results to return
        
        Returns:
            List of RetrievedChunk objects sorted by similarity
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_gen.embed_text(query)
            
            # Use Supabase RPC for vector similarity search
            # Note: Requires pgvector extension and RPC function (see setup in README)
            response = self.client.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_count": top_k
                }
            ).execute()
            
            retrieved = []
            for doc in response.data:
                chunk = RetrievedChunk(
                    text=doc["text"],
                    source_url=doc["source_url"],
                    document_title=doc["document_title"],
                    chunk_id=doc["chunk_id"],
                    page_number=doc["page_number"],
                    similarity_score=doc["similarity"]
                )
                retrieved.append(chunk)
            
            logger.info(f"Retrieved {len(retrieved)} documents (similarity: {retrieved[0].similarity_score:.4f} - {retrieved[-1].similarity_score:.4f})")
            return retrieved
        
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            raise


class ClaudeQA:
    """Handles question answering using multiple LLM providers."""
    
    def __init__(self, provider: str = "gemini"):
        self.provider = provider
        
        if provider == "claude":
            import anthropic
            self.client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
            self.model = "claude-3-5-sonnet-20241022"
        
        elif provider == "gemini":
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY environment variable required")
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            # Auto-select a model that supports generateContent
            self.model = None
            try:
                for model in genai.list_models():
                    methods = getattr(model, "supported_generation_methods", [])
                    if methods and "generateContent" in methods:
                        self.model = model.name
                        break
            except Exception:
                self.model = None
            if not self.model:
                # Fallback to known model name; will error with a clear message if unavailable
                self.model = "models/gemini-1.0-pro"
        
        elif provider == "ollama":
            import requests
            self.ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            self.model = os.getenv("OLLAMA_MODEL", "neural-chat")
        
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    def answer_question(self, question: str, context_chunks: List[RetrievedChunk]) -> Dict[str, Any]:
        """
        Generate an answer to a question using the LLM with retrieved context.
        """
        try:
            # Format context
            context_text = self._format_context(context_chunks)
            
            # Build user message
            user_message = f"""Context from Kenyan law documents:
{context_text}

Question: {question}"""
            
            logger.info(f"Sending request to {self.provider}: {self.model}")
            
            if self.provider == "claude":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_message}]
                )
                answer = response.content[0].text
            
            elif self.provider == "gemini":
                try:
                    import google.genai as genai
                except ImportError:
                    import google.generativeai as genai
                full_prompt = f"{SYSTEM_PROMPT}\n\n{user_message}"
                model = genai.GenerativeModel(self.model)
                response = model.generate_content(full_prompt)
                answer = response.text
            
            elif self.provider == "ollama":
                import requests
                response = requests.post(
                    f"{self.ollama_base}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": f"{SYSTEM_PROMPT}\n\n{user_message}",
                        "stream": False
                    }
                )
                answer = response.json()["response"]
            
            # Extract sources
            sources = self._extract_sources(answer, context_chunks)
            
            return {
                "answer": answer,
                "sources": sources,
                "model": self.model,
                "provider": self.provider
            }
        
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise
    
    def _format_context(self, chunks: List[RetrievedChunk]) -> str:
        """Format context chunks for Claude."""
        formatted = []
        for i, chunk in enumerate(chunks, 1):
            formatted.append(f"""
Document {i}: {chunk.document_title}
Source: {chunk.source_url}
Page: {chunk.page_number}
Similarity Score: {chunk.similarity_score:.4f}
---
{chunk.text}
---
""")
        return "\n".join(formatted)
    
    def _extract_sources(self, answer: str, context_chunks: List[RetrievedChunk]) -> List[Dict[str, Any]]:
        """Extract source citations from answer and context."""
        sources = []
        
        # Add all context sources with similarity scores
        for chunk in context_chunks:
            sources.append({
                "document_title": chunk.document_title,
                "source_url": chunk.source_url,
                "page_number": chunk.page_number,
                "similarity_score": float(chunk.similarity_score),
                "chunk_id": chunk.chunk_id
            })
        
        return sources


class KatibaRAG:
    """Main RAG pipeline orchestrator."""
    
    def __init__(self, embedding_provider: str = "gemini", llm_provider: str = "gemini"):
        logger.info(f"Initializing Katiba RAG pipeline (Embeddings: {embedding_provider}, LLM: {llm_provider})...")
        self.vector_store = VectorStore(embedding_provider)
        self.qa_engine = ClaudeQA(llm_provider)
    
    def answer(self, question: str) -> Dict[str, Any]:
        """
        Answer a question using the RAG pipeline.
        
        Args:
            question: User's question about Kenyan law
        
        Returns:
            Dict with answer, sources, and metadata
        """
        logger.info(f"Processing question: {question}")
        
        # Retrieve relevant documents
        retrieved_chunks = self.vector_store.similarity_search(question, top_k=TOP_K_RESULTS)
        
        if not retrieved_chunks:
            logger.warning("No relevant documents found")
            return {
                "answer": "I don't have relevant information about this topic. Please check kenyalaw.org for more information.",
                "sources": [],
                "model": LLM_MODEL
            }
        
        # Generate answer using Claude
        result = self.qa_engine.answer_question(question, retrieved_chunks)
        
        return result


def interactive_mode(embedding_provider: str = "gemini", llm_provider: str = "gemini"):
    """Run Katiba AI in interactive Q&A mode."""
    print("\n" + "="*60)
    print("🏛️  KATIBA AI - Kenyan Law Assistant")
    print(f"📊 Using: {embedding_provider} embeddings + {llm_provider} LLM")
    print("="*60)
    print("Ask questions about Kenyan law. Type 'quit' to exit.\n")
    
    rag = KatibaRAG(embedding_provider, llm_provider)
    
    while True:
        try:
            question = input("You: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("Thank you for using Katiba AI!")
                break
            
            if not question:
                continue
            
            # Get answer
            result = rag.answer(question)
            
            # Display answer
            print(f"\nKatiba AI: {result['answer']}\n")
            
            # Display sources
            if result['sources']:
                print("📚 Sources:")
                for source in result['sources']:
                    print(f"  - {source['document_title']} (Page {source['page_number']})")
                    print(f"    Relevance: {source['similarity_score']:.1%}")
                    print(f"    URL: {source['source_url']}\n")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"Error processing question: {e}\n")


def batch_query_mode(queries: List[str], output_file: Optional[str] = None):
    """
    Process multiple queries in batch mode.
    
    Args:
        queries: List of questions to answer
        output_file: Optional file to save results as JSON
    """
    rag = KatibaRAG()
    results = []
    
    for i, question in enumerate(tqdm(queries, desc="Processing queries"), 1):
        try:
            result = rag.answer(question)
            result["question"] = question
            result["query_number"] = i
            results.append(result)
        except Exception as e:
            logger.error(f"Error processing query {i}: {e}")
            results.append({
                "question": question,
                "query_number": i,
                "error": str(e)
            })
    
    # Save results if requested
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {output_file}")
    
    return results


if __name__ == "__main__":
    import sys
    
    embedding_provider = EMBEDDING_PROVIDER
    llm_provider = LLM_PROVIDER
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup":
            print("Setting up embeddings for all documents...")
            vector_store = VectorStore(embedding_provider)
            vector_store.add_embeddings_to_documents()
        
        elif sys.argv[1] == "--embedding":
            embedding_provider = sys.argv[2] if len(sys.argv) > 2 else "gemini"
            llm_provider = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--llm" else llm_provider
            interactive_mode(embedding_provider, llm_provider)
        
        elif sys.argv[1] == "--llm":
            llm_provider = sys.argv[2] if len(sys.argv) > 2 else "gemini"
            embedding_provider = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--embedding" else embedding_provider
            interactive_mode(embedding_provider, llm_provider)
        
        else:
            print("Usage:")
            print("  python katiba_rag.py setup")
            print("  python katiba_rag.py [--embedding PROVIDER] [--llm PROVIDER]")
            print("\nProviders:")
            print("  Embeddings: openai, gemini (default), huggingface, ollama, cohere")
            print("  LLM: claude, gemini (default), ollama")
    
    else:
        interactive_mode(embedding_provider, llm_provider)
