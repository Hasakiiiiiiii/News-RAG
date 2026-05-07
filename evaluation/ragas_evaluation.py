import os
import sys 
import warnings 
import pandas as pd
from dotenv import load_dotenv
from datasets import Dataset
from ragas import evaluate
from ragas.run_config import RunConfig # Bổ sung RunConfig để chống lỗi sót số

warnings.filterwarnings("ignore", category=DeprecationWarning)

from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from search.engine import Pipeline
from search.generator import generator_registry

def run_ragas_evaluation():
    load_dotenv()
    
    if not os.getenv("JUDGE_API_KEY"):
        print("[!] Thiếu JUDGE_API_KEY trong .env.")
        return

    # --- 1. KHỞI TẠO GIÁM KHẢO (GPT-4o-mini) ---
    print("[*] Đang mời Giám khảo GPT-4o-mini vào vị trí...")
    judge_key = os.getenv("JUDGE_API_KEY")
    
    # Tăng max_retries và timeout để tránh đứt kết nối giữa chừng
    judge_llm = ChatOpenAI(
        model="gpt-4o-mini", 
        temperature=0.0, 
        api_key=judge_key,
        max_retries=10,        
        timeout=120          
    )
    judge_embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small", 
        api_key=judge_key,
        max_retries=10       
    )

    faithfulness.llm = judge_llm
    answer_relevancy.llm = judge_llm
    answer_relevancy.embeddings = judge_embeddings
    context_precision.llm = judge_llm
    context_recall.llm = judge_llm

    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    # --- TỐI ƯU HÓA: CẤU HÌNH CHỐNG LỖI SÓT SỐ (NaN) ---
    ragas_config = RunConfig(
        max_retries=15,       # Bắt giám khảo thử lại 15 lần nếu trả về JSON lỗi
        max_wait=90,          # Thời gian chờ tối đa giữa các lần gọi
        max_workers=4         # Giới hạn số luồng đồng thời để không bị OpenAI chặn (Rate Limit)
    )

    # --- 2. ĐỌC BỘ ĐỀ THI TỪ CSV ---
    testset_path = "evaluation/testset.csv"
    if not os.path.exists(testset_path):
        print(f"[!] Không tìm thấy file {testset_path}.")
        print("Hãy tạo file CSV gồm 2 cột: 'question' và 'ground_truth'")
        return

    print(f"[*] Đang đọc bộ đề thi từ {testset_path}...")
    df_testset = pd.read_csv(testset_path)
    test_cases = df_testset[['question', 'ground_truth']].to_dict('records')

    # --- 3. LẤY DANH SÁCH GENERATORS ĐỂ TEST ---
    available_models = generator_registry.list_generators()
    if not available_models:
        print("[!] Không có model nào được nạp từ Registry. Hãy kiểm tra lại file .env")
        return

    model_names = [m["name"] for m in available_models]
    print(f"[*] Đã tìm thấy {len(model_names)} models cần đánh giá: {model_names}")
    
    pipeline = Pipeline()

    test_modes = [
        {"name": "VANILLA_RAG", "is_vanilla": True},
        {"name": "ADVANCED_RAG", "is_vanilla": False}
    ]

    # --- 4. CHẠY VÒNG LẶP KÉP: TỪNG MODEL -> TỪNG CHẾ ĐỘ RAG ---
    for model_name in model_names:
        print("\n" + "#"*80)
        print(f"BẮT ĐẦU ĐÁNH GIÁ MÔ HÌNH: {model_name.upper()}")
        print("#"*80)

        for mode in test_modes:
            mode_name = mode["name"]
            is_vanilla_flag = mode["is_vanilla"]
            
            print("\n" + "="*60)
            print(f"ĐANG CHẠY CHẾ ĐỘ: {mode_name}")
            print("="*60)

            data_for_ragas = {
                "question": [],
                "answer": [],
                "contexts": [],
                "ground_truth": []
            }

            print(f"[*] {model_name} đang làm bài thi ({mode_name})...")
            for idx, tc in enumerate(test_cases):
                question = str(tc["question"]).strip()
                print(f"  [{idx+1}/{len(test_cases)}] Đang trả lời: {question[:50]}...")
                
                # Gọi Pipeline với cấu hình tương ứng
                response = pipeline.ask(query=question, model=model_name, is_vanilla=is_vanilla_flag)
                
                # --- TỐI ƯU HÓA: XỬ LÝ CONTEXT RỖNG (TRÁNH LỖI CHIA CHO 0 CỦA RAGAS) ---
                if response.results:
                    contexts = [hit.content for hit in response.results]
                else:
                    # Nếu không tìm thấy gì, chèn 1 câu giả định để Ragas vẫn chấm 0 điểm thay vì lỗi NaN
                    contexts = ["Không tìm thấy bất kỳ tài liệu hoặc ngữ cảnh nào liên quan."]
                
                answer = response.summary if response.summary else "Không có thông tin."
                
                data_for_ragas["question"].append(question)
                data_for_ragas["answer"].append(answer)
                data_for_ragas["contexts"].append(contexts)
                data_for_ragas["ground_truth"].append(str(tc["ground_truth"]).strip())

            dataset = Dataset.from_dict(data_for_ragas)

            print(f"\n[*] Giám khảo đang chấm điểm cho {model_name} - {mode_name} (Vui lòng đợi)...")
            # Bổ sung run_config vào hàm evaluate
            evaluation_result = evaluate(
                dataset=dataset, 
                metrics=metrics, 
                run_config=ragas_config, 
                raise_exceptions=False
            )

            print("\n" + "-"*50)
            print(f"BẢNG ĐIỂM CỦA: {model_name.upper()} ({mode_name})")
            print("-" * 50)
            print(evaluation_result)
            
            # --- 5. LƯU BẢNG ĐIỂM VỚI TÊN ĐỘNG ---
            df_result = evaluation_result.to_pandas()
            
            # Lưu file bao gồm cả tên model và chế độ RAG
            output_path = f"evaluation/result/eval_{model_name.lower()}_{mode_name.lower()}.csv"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            df_result.to_csv(output_path, index=False, encoding="utf-8-sig")
            print(f"[+] Đã lưu bảng điểm chi tiết tại: {output_path}")

    print("\nĐÃ HOÀN TẤT KIỂM TRA VÀ CHẤM ĐIỂM TOÀN BỘ HỆ THỐNG!")

if __name__ == "__main__":
    run_ragas_evaluation()