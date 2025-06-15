from sklearn.cluster import KMeans
from sentence_transformers import SentenceTransformer

# Получаем эмбеддинги
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
sentences = ["Привет, как дела?", "Здравствуйте, как ваши дела?", 
             "Что нового?", "Какие планы?", "Как жизнь?", "Что делаешь?"]
embeddings = model.encode(sentences)

# Кластеризация
num_clusters = 2  # можно подбирать оптимальное количество
kmeans = KMeans(n_clusters=num_clusters, random_state=42)
clusters = kmeans.fit_predict(embeddings)

# Результаты
for sentence, cluster in zip(sentences, clusters):
    print(f"'{sentence}' -> Cluster {cluster}")
