# Поисковая система для хранения и суммаризации документов на OpenSearch + GraphQL  

## **Функционал**
Индексация новостных статей (Lenta.ru) в OpenSearch.  
Поиск документов по **текстовому и векторному соответствию**.  
Векторизация текста с `sentence-transformers/all-MiniLM-L6-v2`.  
Генерация кратких суммаризаций с `Mistral` или `Gemma`.  
Веб-интерфейс **OpenSearch Dashboards** для отладки.

Для заполнения базы данных испольуется Lenta.ru v1.0
https://github.com/natasha/corus?tab=readme-ov-file#reference

Файл lenta-ru-news.csv.gz не включён в репозиторий (он слишком большой).
Скачать вручную: wget https://github.com/yutkin/Lenta.Ru-News-Dataset/releases/download/v1.0/lenta-ru-news.csv.gz
Затем переместить его в папку проекта (рядом с load_lenta.py) и запустить скрипт python load_lenta.py

## **Примеры использования**
1) **Поиск документа**
query {
  search(searchString: "Пример строки для поиска", offset: 0, limit: 10) {
    listDocument {
      id
      title
      text
    }
    total
  }
}

2) **Индексация нового документа**
mutation {
  indexDocument(title: "Пример заголовка", text: "Тестовый документ.") {
    id
    title
    text
  }
}

3) **Суммаризация документов**
query {
  summarize(ids: ["12345", "67890"])
}

