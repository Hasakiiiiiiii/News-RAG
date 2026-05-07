import sys
import os
from pprint import pprint

# Ensure the root directory is in the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from search.engine import Pipeline

def run_e2e_vanilla_test():
    print("\n" + "="*60)
    print("🚀 STARTING VANILLA RAG PIPELINE TEST (BASELINE)")
    print("="*60)

    try:
        # 1. Initialize Pipeline
        print("[*] Initializing Pipeline (Loading models and connecting to Cloud)...")
        pipeline = Pipeline()
        
        # 2. Define a query based on your news data
        query = "Tình hình giá dầu thô Brent năm 2024 và 2026 thế nào?"
        print(f"\n[?] Câu hỏi: {query}")
        
        # 3. Execute the pipeline in VANILLA mode
        print("[*] Đang xử lý (Chế độ Vanilla RAG: Chỉ Dense Vector, Không Rerank)...")
        
        # --- ĐIỂM QUAN TRỌNG: BẬT CỜ is_vanilla=True ---
        # Bạn có thể đổi "gemini-2.5-flash" thành "openai" hoặc model khác tùy ý
        response = pipeline.ask(query=query, model="qwen3-32b", is_vanilla=True)

        # 4. Display Results
        print("\n" + "✨" + "-"*15 + " CÂU TRẢ LỜI (VANILLA) " + "-"*15)
        if response.summary:
            print(f"{response.summary}")
        else:
            print("Không tìm thấy câu trả lời.")
        
        print("-" * 55)
        print(f"⏱️ Duration: {response.duration_ms} ms")
        print(f"📚 Sources Found: {response.total} (Cố định lấy Top 5)")
        
        if response.results:
            print("\n🔗 References Used:")
            for i, hit in enumerate(response.results):
                print(f"   [{i+1}] {hit.title} | Link: {hit.url}")

    except Exception as e:
        print(f"❌ Vanilla Test failed with error: {e}")

if __name__ == "__main__":
    run_e2e_vanilla_test()