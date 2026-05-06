import os
import logging
from dotenv import load_dotenv
from search.retriever import Retriever
from search.generator import generator_registry # Import registry mới

# Cấu hình logging để thấy được quá trình nạp model
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_scaling_generators():
    load_dotenv()
    
    # 1. Khởi tạo Retriever
    print("\n[*] Đang khởi động Retriever...")
    retriever = Retriever() 
    
    # 2. Kiểm tra danh sách model đã nạp từ Registry
    available_models = generator_registry.list_generators()
    if not available_models:
        print("[!] Không có model nào được nạp. Hãy kiểm tra NUM_MODELS trong .env")
        return

    model_names = [m["name"] for m in available_models]
    print(f"[*] Đã nạp {len(available_models)} models: {model_names}")

    # 3. Chạy thử nghiệm
    query = "Tình hình giá dầu mỏ thế giới hiện nay như thế nào?"
    print(f"\n🔍 User Query: {query}")
    print("=" * 50)
    
    try:
        # Bước 1: Tìm kiếm context chung cho tất cả models
        print("[*] Đang tìm kiếm tài liệu liên quan...")
        search_hits = retriever.search(query)
        
        if not search_hits:
            print("[!] Không tìm thấy dữ liệu từ Retriever.")
            return

        # Bước 2: Duyệt qua từng model để lấy câu trả lời (Scaling Test)
        for model_item in available_models:
            actual_model_name = model_item.get("name")
            
            if not actual_model_name:
                print(f"[!] Dữ liệu model bị lỗi, bỏ qua: {model_item}")
                continue

            print(f"\n--- [Đang gọi AI: {actual_model_name.upper()}] ---")
            
            # Lấy generator cụ thể từ registry
            generator = generator_registry.get_generator(actual_model_name)
            
            # Thực thi tạo câu trả lời
            response = generator.generate(query, search_hits)
            
            print(f"🤖 Response: {response}")
            print("-" * 30)
                    
    except Exception as e:
        print(f"\n[ERROR] Test thất bại: {e}")

if __name__ == "__main__":
    test_scaling_generators()