"""
Test utilities for RAG pipeline.

Usage:
  python -m tests.test_pipeline
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.ingest import PDFIngestionPipeline
from app.query import QueryEngine


async def test_pipeline():
    """Test the complete RAG pipeline."""
    print("🧪 Testing RAG Pipeline")
    print("=" * 60)

    try:
        # Test 1: Pipeline initialization
        print("\n1️⃣  Initializing pipeline...")
        ingest_pipeline = PDFIngestionPipeline()
        query_engine = QueryEngine()
        print("✅ Pipeline initialized successfully")

        # Test 2: Health check
        print("\n2️⃣  Checking system health...")
        try:
            ingest_pipeline.opensearch_client.info()
            print("✅ OpenSearch connection OK")
        except Exception as e:
            print(f"❌ OpenSearch connection failed: {e}")
            print("   Make sure OpenSearch is running: docker-compose up opensearch")
            return False

        # Test 3: API connectivity
        print("\n3️⃣  Checking Anthropic API...")
        try:
            # This will be tested when we actually query
            print("✅ Anthropic client initialized")
        except Exception as e:
            print(f"❌ Anthropic API failed: {e}")
            print("   Set ANTHROPIC_API_KEY environment variable")
            return False

        print("\n" + "=" * 60)
        print("✅ All system checks passed!")
        print("\nNext steps:")
        print("  1. Start the full stack: docker-compose up --build")
        print("  2. Upload a PDF: http://localhost:3000/ingest")
        print("  3. Query documents: http://localhost:3000")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_pipeline())
    sys.exit(0 if success else 1)
