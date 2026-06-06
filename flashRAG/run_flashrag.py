import json
import os
import time
from flashrag.config import Config
from flashrag.utils import get_retriever
from flashrag.utils import get_dataset
import faiss
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ==========================================
# KHỞI TẠO CLIENT OPENAI TỰ LÀM (GROQ)
# ==========================================
client = OpenAI(
    api_key=os.getenv("MODEL_2_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

model_id = os.getenv("MODEL_2_MODEL_ID", "gpt-oss-120b")
temperature = float(os.getenv("MODEL_2_TEMPERATURE", 0.3))
max_tokens = int(os.getenv("MODEL_2_MAX_TOKENS", 2048))

# ==========================================
# 1. CHUYỂN ĐỔI FORMAT & TẠO CẤU TRÚC FOLDER
# ==========================================
input_dataset_path = "evaluation/testset.jsonl"
flashrag_dataset_dir = "evaluation/flash_dataset"
os.makedirs(flashrag_dataset_dir, exist_ok=True)
flashrag_dataset_path = os.path.join(flashrag_dataset_dir, "test.jsonl")

with open(input_dataset_path, "r", encoding="utf-8") as fin, \
     open(flashrag_dataset_path, "w", encoding="utf-8") as fout:
    for line in fin:
        data = json.loads(line)
        formatted_data = {
            "id": data["id"],
            "question": data["question"],
            "golden_answers": [data["answers"]] 
        }
        fout.write(json.dumps(formatted_data, ensure_ascii=False) + "\n")

# ==========================================
# 2. CẤU HÌNH FLASHRAG (CHỈ ĐỂ LẤY RETRIEVER)
# ==========================================
config_dict = {
    "data_dir": "evaluation/",           
    "dataset_name": "flash_dataset",     
    "split": ["test"],                   
    "retrieval_method": "dense", 
    "retrieval_model_path": "BAAI/bge-m3", 
    "index_path": "indexes/bge_Flat.index", 
    "corpus_path": "flashRAG/corpus.jsonl",
    "pooling_method": "cls",
    "use_sentence_transformer": True,
    "retrieval_topk": 5
}

my_config = Config(config_dict=config_dict)

print("[*] Đang nạp Retriever...")
retriever = get_retriever(my_config)

print("[*] Đang load bộ câu hỏi...")
dataset = get_dataset(my_config)
test_data = dataset['test'] 
num_questions = len(test_data.data)

# ==========================================
# 3. CHẠY TRUY XUẤT (RETRIEVAL)
# ==========================================
print("[*] Đang chạy Retriever tìm ngữ cảnh cho TOÀN BỘ câu hỏi (Chạy Local cực nhanh)...")
queries = test_data.question 
raw_retrieval_results = retriever.batch_search(queries)

# ==========================================
# 4. CHẠY GENERATOR TỰ CODE & XUẤT FILE
# ==========================================
print(f"[*] Đang chạy Inference với {model_id}...")
print("[!] Đã kích hoạt chế độ Delay (Nghỉ 5 giây/câu) để chống sập API Groq...")

ragas_output = []

for i in range(num_questions):
    print(f"  -> Đang hỏi Groq câu {i+1}/{num_questions}...")
    
    question = queries[i]
    my_raw_docs = raw_retrieval_results[i]
    
    # 1. Trích xuất Context
    contexts = [doc['contents'] for doc in my_raw_docs] if my_raw_docs else ["Không tìm thấy ngữ cảnh."]
    
    # 2. Gộp Context thành 1 đoạn văn bản dài
    reference_text = "\n\n".join(contexts)
    
    # 3. Ghép Prompt thủ công
    prompt = f"Dựa vào các tài liệu sau đây:\n{reference_text}\n\nHãy trả lời câu hỏi sau một cách ngắn gọn và chính xác. Trả lời trực tiếp vào trọng tâm, không cần giải thích thêm.\nCâu hỏi: {question}\nTrả lời:"
    
    # 4. Gọi API Groq tự túc (Né hoàn toàn thư viện FlashRAG lỗi)
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Lỗi khi gọi API: {e}")
        answer = "[Lỗi API]"

    # 5. Lưu kết quả
    ragas_output.append({
        "question": question,
        "answer": answer, 
        "contexts": contexts,
        "ground_truth": test_data.data[i].golden_answers[0] 
    })
        
    time.sleep(5)

# Lưu thẳng vào thư mục evaluation
output_path = "evaluation/ragas_flashrag_input.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(ragas_output, f, ensure_ascii=False, indent=4)

print(f"\n[SUCCESS] Đã tạo xong file hoàn chỉnh tại: {output_path}")