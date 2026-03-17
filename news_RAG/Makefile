init:
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

up:
	docker compose up -d

run:
	. .venv/bin/activate && python main.py

stop:
	docker compose down

clean:
	rm -rf .venv

check_docker:
	docker exec -it mongo_news_rag mongo -u tuan -p tuan --eval "db.getSiblingDB('news_rag').articles.find().limit(5).pretty()"