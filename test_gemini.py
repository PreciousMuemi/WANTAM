#!/usr/bin/env python3
"""Quick test of Gemini API integration"""

import os
from dotenv import load_dotenv

load_dotenv()

print("Testing Gemini API...")
print("=" * 60)

try:
    import google.generativeai as genai
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env")
        exit(1)
    
    genai.configure(api_key=api_key)
    print("✅ Gemini API configured")
    
    # Test embedding
    print("\n1. Testing Embedding (text-embedding-004)...")
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content="What is the constitution?"
        )
        embedding = result['embedding']
        print(f"✅ Embedding successful! Dimensions: {len(embedding)}")
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        exit(1)
    
    # Test LLM
    print("\n2. Testing LLM (gemini-1.5-flash)...")
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say hello briefly")
        answer = response.text
        print(f"✅ LLM response: {answer[:100]}...")
    except Exception as e:
        print(f"❌ LLM error: {e}")
        exit(1)
    
    print("\n" + "=" * 60)
    print("✅ All Gemini API tests passed!")
    print("\nYou can now run:")
    print("  python katiba_rag.py")
    
except ImportError as e:
    print(f"❌ Missing import: {e}")
    print("\nPlease run:")
    print("  pip install google-generativeai")
    exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    exit(1)
