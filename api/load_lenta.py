import gzip
import opensearchpy
from corus import load_lenta
from sentence_transformers import SentenceTransformer

# Настройки и подключение к OpenSearch
OPENSEARCH_URL = "http://localhost:9200"
OPENSEARCH_USER = "admin"
OPENSEARCH_PASSWORD = "S!rong_Password100%"
INDEX_NAME = "documents"

client = opensearchpy.OpenSearch(
    hosts=[OPENSEARCH_URL],
    http_auth=(OPENSEARCH_USER, OPENSEARCH_PASSWORD),
    use_ssl=False, verify_certs=False
)

# Проверка индекса на существование
if not client.indices.exists(INDEX_NAME):
    raise ValueError("Индекс не существует.")

# Модель для векторизации
vectorizer = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Загрузка данных
data_path = "lenta-ru-news.csv.gz"

print("Начало загрузки данных Lenta.ru v1.0")
records = load_lenta(data_path)

count = 0
max_records = 2000  # Загружаем ограниченное число документов для тестирования

for record in records:
    title = record.title
    text = record.text
    vector = vectorizer.encode(text).tolist()
    
    doc = {"title": title, "text": text, "vector": vector}
    client.index(index=INDEX_NAME, body=doc, refresh=True)
    
    count += 1
    if count % 100 == 0:  # Логирование каждые 100 записей
        print(f"Загружено {count} документов...")

    if count >= max_records:
        break

print("Загрузка завершена. Всего загружено:", count)
