"""
Test utilities and examples for Katiba RAG pipeline.
"""

import json
import time
from typing import List, Dict, Any
from katiba_rag import KatibaRAG


# Example test questions about Kenyan law
SAMPLE_QUESTIONS = [
    "What are the basic rights guaranteed by the Kenyan Constitution?",
    "What is the role of Parliament in Kenya?",
    "What are the responsibilities of the President?",
    "How are judges appointed in Kenya?",
    "What are workers' rights under Kenyan employment law?",
    "How does the Kenyan legal system work?",
    "What is the Kenya Land Commission responsible for?",
    "What are the rights of children in Kenya?",
    "How are local governments structured in Kenya?",
    "What is the role of the Attorney General?",
]


def test_single_query():
    """Test a single query."""
    print("Testing single query...")
    rag = KatibaRAG()
    
    question = "What are the fundamental rights in the Kenyan Constitution?"
    print(f"\nQuestion: {question}")
    
    start_time = time.time()
    result = rag.answer(question)
    elapsed = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"Answer:\n{result['answer']}")
    print(f"\n{'='*60}")
    print(f"\nSources ({len(result['sources'])} retrieved):")
    for i, source in enumerate(result['sources'], 1):
        print(f"\n{i}. {source['document_title']}")
        print(f"   Page: {source['page_number']}")
        print(f"   Relevance: {source['similarity_score']:.1%}")
        print(f"   URL: {source['source_url']}")
    
    print(f"\n⏱️  Response time: {elapsed:.2f}s")


def test_batch_queries(num_samples: int = 5):
    """Test multiple queries."""
    print(f"Testing {num_samples} queries...")
    rag = KatibaRAG()
    
    questions = SAMPLE_QUESTIONS[:num_samples]
    results = []
    
    print(f"\nProcessing {len(questions)} questions...\n")
    
    total_time = 0
    for i, question in enumerate(questions, 1):
        print(f"{i}. {question}")
        
        start_time = time.time()
        result = rag.answer(question)
        elapsed = time.time() - start_time
        total_time += elapsed
        
        result["question"] = question
        result["response_time"] = elapsed
        results.append(result)
        
        print(f"   ✓ Got answer in {elapsed:.2f}s (Relevance: {result['sources'][0]['similarity_score']:.1%})\n")
    
    print(f"{'='*60}")
    print(f"Batch Results Summary:")
    print(f"{'='*60}")
    print(f"Total queries: {len(results)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average time per query: {total_time/len(results):.2f}s")
    
    # Show first result in detail
    print(f"\n{'='*60}")
    print(f"Example Result #1:")
    print(f"{'='*60}")
    first = results[0]
    print(f"Question: {first['question']}")
    print(f"\nAnswer: {first['answer'][:200]}...")
    print(f"\nTop source: {first['sources'][0]['document_title']} (Relevance: {first['sources'][0]['similarity_score']:.1%})")
    
    return results


def test_vector_search():
    """Test vector search directly."""
    from katiba_rag import VectorStore
    
    print("Testing vector search...")
    vs = VectorStore()
    
    test_queries = [
        "What are human rights?",
        "How to amend the constitution?",
        "Employment rights and duties",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        chunks = vs.similarity_search(query, top_k=3)
        
        for i, chunk in enumerate(chunks, 1):
            print(f"  {i}. {chunk.document_title} (Relevance: {chunk.similarity_score:.1%})")
            print(f"     {chunk.text[:100]}...")


def test_embedding_generation():
    """Test embedding generation."""
    from katiba_rag import EmbeddingGenerator
    
    print("Testing embedding generation...")
    eg = EmbeddingGenerator()
    
    test_texts = [
        "Article 33: Every person has the right to freedom of expression",
        "The President shall be elected by popular vote",
        "Parliament is the supreme legislative body",
    ]
    
    for text in test_texts:
        embedding = eg.embed_text(text)
        print(f"Generated {len(embedding)}-dimensional embedding for: {text[:50]}...")
        print(f"  Embedding (first 5 dims): {embedding[:5]}")


def test_api_connectivity():
    """Test connectivity to all required APIs."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("Testing API Connectivity...")
    print(f"{'='*60}\n")
    
    # Test Supabase
    print("1. Supabase:")
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            print("   ❌ Missing SUPABASE_URL or SUPABASE_KEY")
        else:
            client = create_client(url, key)
            response = client.table("documents").select("count").limit(1).execute()
            print(f"   ✅ Connected to Supabase")
            print(f"   📊 Documents in database: {len(response.data)}")
    except Exception as e:
        print(f"   ❌ Supabase error: {e}")
    
    print()
    
    # Test OpenAI
    print("2. OpenAI (for embeddings):")
    try:
        import openai
        key = os.getenv("OPENAI_API_KEY")
        
        if not key:
            print("   ❌ Missing OPENAI_API_KEY")
        else:
            openai.api_key = key
            client = openai.OpenAI()
            # Test with a small request
            response = client.embeddings.create(
                input="test",
                model="text-embedding-3-small"
            )
            print(f"   ✅ Connected to OpenAI")
            print(f"   📊 Embedding dimension: {len(response.data[0].embedding)}")
    except Exception as e:
        print(f"   ❌ OpenAI error: {e}")
    
    print()
    
    # Test Claude
    print("3. Claude (Anthropic):")
    try:
        import anthropic
        key = os.getenv("CLAUDE_API_KEY")
        
        if not key:
            print("   ❌ Missing CLAUDE_API_KEY")
        else:
            client = anthropic.Anthropic(api_key=key)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            print(f"   ✅ Connected to Claude")
            print(f"   📊 Model: claude-3-5-sonnet-20241022")
    except Exception as e:
        print(f"   ❌ Claude error: {e}")


def export_results_to_csv(results: List[Dict[str, Any]], filename: str = "rag_results.csv"):
    """Export results to CSV format."""
    import csv
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            "Question",
            "Answer (first 100 chars)",
            "Top Source",
            "Top Source Relevance",
            "Response Time (s)",
            "Num Sources"
        ])
        
        # Write rows
        for result in results:
            answer_preview = result['answer'][:100].replace('\n', ' ')
            top_source = result['sources'][0]['document_title'] if result['sources'] else "N/A"
            top_relevance = result['sources'][0]['similarity_score'] if result['sources'] else 0
            
            writer.writerow([
                result.get('question', 'N/A'),
                answer_preview,
                top_source,
                f"{top_relevance:.1%}",
                result.get('response_time', 'N/A'),
                len(result.get('sources', []))
            ])
    
    print(f"Results exported to {filename}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
        if mode == "single":
            test_single_query()
        
        elif mode == "batch":
            num_samples = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            results = test_batch_queries(num_samples)
            
            # Optionally export to CSV
            if len(sys.argv) > 3 and sys.argv[3] == "export":
                export_results_to_csv(results)
        
        elif mode == "search":
            test_vector_search()
        
        elif mode == "embedding":
            test_embedding_generation()
        
        elif mode == "connectivity":
            test_api_connectivity()
        
        else:
            print("Unknown mode. Available modes:")
            print("  - single: Test single query")
            print("  - batch [n] [export]: Test n queries, optionally export to CSV")
            print("  - search: Test vector search")
            print("  - embedding: Test embedding generation")
            print("  - connectivity: Test API connections")
    
    else:
        print("Katiba RAG - Test Suite")
        print(f"{'='*60}")
        print("\nUsage: python test_rag.py <mode> [options]\n")
        print("Modes:")
        print("  single              - Test a single query")
        print("  batch [n] [export]  - Test n queries (default 5), optionally export to CSV")
        print("  search              - Test vector search")
        print("  embedding           - Test embedding generation")
        print("  connectivity        - Check all API connections")
        print("\nExamples:")
        print("  python test_rag.py single")
        print("  python test_rag.py batch 10 export")
        print("  python test_rag.py connectivity")
