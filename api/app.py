import os
import time
import strawberry
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.asgi import GraphQL
from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer
import ollama

# Конфигурация OpenSearch
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
OPENSEARCH_USER = os.getenv("OPENSEARCH_USER", "admin")
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_PASSWORD", "S!rong_Password100%")
INDEX_NAME = "documents"

client = OpenSearch(
    hosts=[OPENSEARCH_URL],
    http_auth=(OPENSEARCH_USER, OPENSEARCH_PASSWORD),
    use_ssl=False, verify_certs=False
)

# Ожидание доступности OpenSearch перед запуском
while True:
    try:
        if client.ping():
            break
    except Exception:
        time.sleep(5)

# Создание индекса, если не создан ранее
if not client.indices.exists(INDEX_NAME):
    client.indices.create(
        index=INDEX_NAME,
        body={
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100, # точность поиска k-NN
                    "number_of_shards": 1, # количество разделов, оптимально для небольшого объема данных
                    "number_of_replicas": 0, # количество копий индекса, оптимально для одного сервера
                }
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "text": {"type": "text"},
                    "vector": {
                        "type": "knn_vector", 
                        "dimension": 384, # размерность вектора all-MiniLM-L6-v2
                        "space_type": "l2",
                        "method": {
                            "name": "hnsw",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 128, 
                                "m": 16 # кол-во связей между узлами
                            }
                        }}
                }
            }
        }
    )

# Модель векторизации
vectorizer = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Схемы данных
@strawberry.type
class Document:
    id: str
    title: str
    text: str

@strawberry.type
class DocumentPagination:
    listDocument: list[Document]
    total: int

# Поиск и суммаризация
@strawberry.type
class Query:
    @strawberry.field
    def search(self, searchString: str, offset: int = 0, limit: int = 20) -> DocumentPagination:
        '''Поиск документов'''
        vector = vectorizer.encode(searchString).tolist()
        query = {
            "size": limit,
            "from": offset,
            "query": {
                "bool": {
                    "should": [ # Поиск и по тексту, и по заголовку
                        {"knn": {"vector": {"vector": vector, "k": 12}}},
                        {"match": {"title": {"query": searchString, "boost": 2}}}, # Увеличение приоритета заголовков
                        {"match": {"text": {"query": searchString}}}
                    ]
                }
            }
        }
        response = client.search(index=INDEX_NAME, body=query)
        results = [
            Document(id=hit["_id"], title=hit["_source"]["title"], text=hit["_source"]["text"])
            for hit in response["hits"]["hits"]
        ]
        return DocumentPagination(listDocument=results, total=response["hits"]["total"]["value"])

    @strawberry.field
    def summarize(self, ids: list[str]) -> str:
        '''Суммаризация текста документов'''
        if len(ids) > 50:
            raise ValueError("Превышено максимальное число документов (50)")
        
        docs = [client.get(index=INDEX_NAME, id=doc_id)["_source"]["text"] for doc_id in ids]
        input_text = " ".join(docs)

        max_chunk_size = 5000 # размер чанка для суммаризации
        chunks = [input_text[i:i+max_chunk_size] for i in range(0, len(input_text), max_chunk_size)]

        summaries = []
        for chunk in chunks:
            response = ollama.chat(model="mistral", messages=[
                {
                    "role": "user",
                    "content": f"Суммаризируй этот текст: {chunk}"
                }
            ])

            # Выводим ответ в строковом формате
            summary_text = response["message"] if isinstance(response, dict) and "message" in response else str(response)
            summaries.append(summary_text)

        return " ".join(summaries)



@strawberry.type
class Mutation:
    @strawberry.mutation
    def indexDocument(self, title: str, text: str) -> Document:
        '''Добавление нового документа с векторизацией'''
        vector = vectorizer.encode(text).tolist()
        doc = {"title": title, "text": text, "vector": vector}
        response = client.index(index=INDEX_NAME, body=doc, refresh=True)
        return Document(id=response["_id"], title=title, text=text)


# Запуск FastAPI с GraphQL
schema = strawberry.Schema(query=Query, mutation=Mutation)
app = FastAPI()

# Разрешаем CORS для работы с GraphQL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_route("/graphql", GraphQL(schema))
