import os
import sys 
import warnings 
import re
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from datasets import Dataset
from ragas import evaluate
from ragas.run_config import RunConfig 

warnings.filterwarnings("ignore", category=DeprecationWarning)

from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from search.engine import Pipeline
# from search.generator import generator_registry # (Có thể bỏ qua nếu không cần lấy danh sách động nữa)

def run_ragas_evaluation():
    if not os.getenv("JUDGE_API_KEY"):
        print("[!] Thiếu JUDGE_API_KEY trong .env.")
        return

    # --- 1. KHỞI TẠO GIÁM KHẢO (GPT-4o-mini) ---
    print("[*] Đang mời Giám khảo GPT-4o-mini vào vị trí...")
    judge_key = os.getenv("JUDGE_API_KEY")
    
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

    ragas_config = RunConfig(
        max_retries=15,       
        max_wait=90,          
        max_workers=4         
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

    # --- 3. CỐ ĐỊNH MODEL VÀ CHẾ ĐỘ RAG THEO YÊU CẦU ---
    model_names = ["gpt-oss-120b"]
    print(f"[*] Chỉ chạy đánh giá trên mô hình: {model_names}")
    
    pipeline = Pipeline()

    # Chỉ giữ lại chế độ NewsRAG (Advanced RAG)
    test_modes = [
        {"name": "NEWS_RAG", "is_vanilla": False}
    ]

    # --- 4. CHẠY ĐÁNH GIÁ ---
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
                
                if response.results:
                    contexts = [hit.content for hit in response.results]
                else:
                    contexts = ["Không tìm thấy bất kỳ tài liệu hoặc ngữ cảnh nào liên quan."]
                
                raw_answer = response.summary if response.summary else "Không có thông tin."
                clean_answer = re.sub(r'<think>.*?</think>', '', raw_answer, flags=re.DOTALL)
                clean_answer = clean_answer.strip()
                data_for_ragas["question"].append(question)
                data_for_ragas["answer"].append(clean_answer)
                data_for_ragas["contexts"].append(contexts)
                data_for_ragas["ground_truth"].append(str(tc["ground_truth"]).strip())

            dataset = Dataset.from_dict(data_for_ragas)

            print(f"\n[*] Giám khảo đang chấm điểm cho {model_name} - {mode_name} (Vui lòng đợi)...")
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
            
            # --- 5. LƯU BẢNG ĐIỂM ---
            df_result = evaluation_result.to_pandas()
            
            output_path = f"evaluation/result/eval_{model_name.lower()}_{mode_name.lower()}.csv"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            df_result.to_csv(output_path, index=False, encoding="utf-8-sig")
            print(f"[+] Đã lưu bảng điểm chi tiết tại: {output_path}")

    print("\nĐÃ HOÀN TẤT KIỂM TRA VÀ CHẤM ĐIỂM TOÀN BỘ HỆ THỐNG!")

if __name__ == "__main__":
    run_ragas_evaluation()