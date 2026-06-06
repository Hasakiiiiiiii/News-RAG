import os
import json
import warnings
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from datasets import Dataset
from ragas import evaluate
from ragas.run_config import RunConfig 

warnings.filterwarnings("ignore", category=DeprecationWarning)

from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

def run_ragas_evaluation_for_flashrag():
    if not os.getenv("JUDGE_API_KEY"):
        print("[!] Thiếu JUDGE_API_KEY trong .env.")
        return

    # --- 1. KHỞI TẠO GIÁM KHẢO (GPT-4o-mini) ---
    print("[*] Đang khởi tạo Giám khảo GPT-4o-mini cho FlashRAG...")
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

    # --- 2. ĐỌC DỮ LIỆU TỪ FLASHRAG ---
    flashrag_output_path = "evaluation/ragas_flashrag_input.json"
    if not os.path.exists(flashrag_output_path):
        print(f"[!] Không tìm thấy file {flashrag_output_path}.")
        print("Hãy chạy script FlashRAG trước để tạo ra file này.")
        return

    print(f"[*] Đang đọc kết quả thi của FlashRAG từ {flashrag_output_path}...")
    with open(flashrag_output_path, "r", encoding="utf-8") as f:
        data_for_ragas = json.load(f)

    # Chuyển đổi list of dicts (từ JSON) sang dict of lists (chuẩn của thư viện Datasets)
    formatted_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }

    for idx, item in enumerate(data_for_ragas):
        question = str(item["question"]).strip()
        print(f"  [{idx+1}/{len(data_for_ragas)}] Đã load câu: {question[:50]}...")
        
        # Xử lý an toàn: Nếu FlashRAG không tìm thấy context, chèn câu báo rỗng
        contexts = item.get("contexts", [])
        if not contexts:
             contexts = ["Không tìm thấy bất kỳ tài liệu hoặc ngữ cảnh nào liên quan."]
             
        formatted_data["question"].append(question)
        formatted_data["answer"].append(str(item["answer"]).strip())
        formatted_data["contexts"].append(contexts)
        formatted_data["ground_truth"].append(str(item["ground_truth"]).strip())

    dataset = Dataset.from_dict(formatted_data)

    # --- 3. TIẾN HÀNH CHẤM ĐIỂM ---
    print("\n[*] Giám khảo đang chấm điểm cho hệ thống FLASHRAG (Vui lòng đợi)...")
    evaluation_result = evaluate(
        dataset=dataset, 
        metrics=metrics, 
        run_config=ragas_config, 
        raise_exceptions=False
    )

    print("\n" + "-"*50)
    print("BẢNG ĐIỂM CỦA: FLASHRAG (BASELINE)")
    print("-" * 50)
    print(evaluation_result)
    
    # --- 4. LƯU BẢNG ĐIỂM ---
    df_result = evaluation_result.to_pandas()
    
    # Đặt tên file xuất ra theo format chung (eval_model_mode.csv)
    output_path = "evaluation/result/eval_flashrag.csv"
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_result.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[+] Đã lưu bảng điểm chi tiết tại: {output_path}")
    print("\nHOÀN TẤT ĐÁNH GIÁ FLASHRAG!")

if __name__ == "__main__":
    run_ragas_evaluation_for_flashrag()