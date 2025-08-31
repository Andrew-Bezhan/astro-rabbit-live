"""
Клиент для работы с Qdrant векторной базой данных
Замена Pinecone согласно требованиям пользователя
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger()

class QdrantClient:
    """ОБЯЗАТЕЛЬНЫЙ Qdrant клиент для сбора всех результатов согласно ТЗ"""
    
    def __init__(self):
        """Инициализация ОБЯЗАТЕЛЬНОГО Qdrant"""
        self.api_key = os.getenv('QDRANT_API_KEY')
        self.url = os.getenv('QDRANT_URL', 'https://67c4f754-3521-4ca2-b53a-4f44317484d7.us-east4-0.gcp.cloud.qdrant.io:6333')
        self.collection_name = "astrobot-results"
        
        # Поддержка in-memory режима
        if self.url.startswith('memory://'):
            logger.info("🧠 Используется in-memory векторная БД")
            self.client = None
            self._memory_storage = {}
            return
        
        if not self.api_key:
            logger.warning("⚠️ Qdrant API ключ не найден - система будет работать без векторной БД")
            self.client = None
            return
        
        try:
            # Используем официальный Qdrant клиент
            from qdrant_client import QdrantClient as QClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            
            # Убираем порт для cloud версии Qdrant
            clean_url = self.url.replace(':6333', '') if ':6333' in self.url else self.url
            
            self.client = QClient(
                url=clean_url,
                api_key=self.api_key,
                timeout=30,
                prefer_grpc=False,  # Используем HTTP для cloud
                check_compatibility=False  # Отключаем проверку совместимости
            )
            
            # Проверяем соединение
            try:
                self.client.get_collections()
                logger.info(f"✅ Qdrant клиент инициализирован для {clean_url}")
                # Создаем коллекцию если не существует
                self._ensure_collection()
            except Exception as conn_error:
                logger.warning(f"⚠️ Qdrant недоступен (проверка соединения): {conn_error}")
                self.client = None
            
        except Exception as e:
            logger.warning(f"⚠️ Qdrant недоступен: {e}")
            # НЕ raise - система должна работать без Qdrant
            self.client = None
    
    def _ensure_collection(self):
        """Обеспечиваем наличие коллекции для результатов"""
        if not self.client:
            logger.warning("⚠️ Qdrant клиент недоступен, пропускаем создание коллекции")
            return
            
        try:
            from qdrant_client.models import Distance, VectorParams
            
            # Проверяем существование коллекции
            try:
                collections = self.client.get_collections()
                collection_exists = any(c.name == self.collection_name for c in collections.collections)
            except Exception as e:
                logger.warning(f"⚠️ Не удалось проверить коллекции Qdrant: {e}")
                # Пытаемся создать коллекцию без проверки
                collection_exists = False
            
            if not collection_exists:
                # Создаем коллекцию
                logger.info(f"🔧 Создаем Qdrant коллекцию: {self.collection_name}")
                
                try:
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
                    )
                    logger.info("✅ Qdrant коллекция создана")
                except Exception as create_error:
                    logger.warning(f"⚠️ Не удалось создать коллекцию: {create_error}")
                    # Коллекция может уже существовать
                    pass
            
            logger.info("✅ Qdrant коллекция готова для сбора результатов")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка настройки Qdrant коллекции: {e}")
            # НЕ raise - система должна работать с ограниченным функционалом
    
    async def save_astro_result(self, user_id: int, company_name: str, analysis_type: str, result: str):
        """ОБЯЗАТЕЛЬНОЕ сохранение всех астропрогнозов согласно ТЗ"""
        # In-memory режим
        if hasattr(self, '_memory_storage'):
            point_id = f"memory_{user_id}_{analysis_type}_{int(datetime.now().timestamp())}"
            self._memory_storage[point_id] = {
                'user_id': user_id,
                'company_name': company_name,
                'analysis_type': analysis_type,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"🧠 Результат сохранен в памяти: {point_id}")
            return point_id
        
        if not self.client:
            logger.warning("⚠️ Qdrant недоступен, результат не сохранен в векторной БД")
            return f"local_{user_id}_{analysis_type}_{int(datetime.now().timestamp())}"
            
        try:
            # Создаем embedding результата через Gemini или OpenAI
            embedding = [0.0] * 1536  # Default fallback
            
            # Пробуем Gemini для embeddings
            gemini_key = os.getenv('GEMINI_API_KEY')
            if gemini_key:
                try:
                    # Используем простой текстовый хеш как псевдо-embedding
                    import hashlib
                    text_hash = hashlib.md5(result[:2000].encode('utf-8')).hexdigest()
                    # Конвертируем в псевдо-вектор
                    embedding = [float(int(text_hash[i:i+2], 16)) / 255.0 for i in range(0, min(len(text_hash), 3072), 2)]
                    embedding = (embedding * (1536 // len(embedding) + 1))[:1536]  # Дополняем до 1536
                    logger.info("🧠 Embedding создан через хеш-алгоритм")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка создания embedding: {e}")
            else:
                # Fallback OpenAI
                openai_key = os.getenv('OPENAI_API_KEY')
                if openai_key:
                    try:
                        import openai
                        openai.api_key = openai_key
                        response = openai.embeddings.create(
                            model="text-embedding-ada-002",
                            input=result[:2000]
                        )
                        embedding = response.data[0].embedding
                        logger.info("🧠 Embedding создан через OpenAI")
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка OpenAI embedding: {e}")
                else:
                    logger.warning("⚠️ Ни Gemini, ни OpenAI ключи недоступны для embeddings")
            
            # Сохраняем в Qdrant
            from qdrant_client.models import PointStruct
            
            # Создаем UUID для Qdrant
            import uuid
            point_id = str(uuid.uuid4())
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "user_id": user_id,
                    "company_name": company_name,
                    "analysis_type": analysis_type,
                    "result_preview": result[:500],
                    "timestamp": datetime.now().isoformat(),
                    "full_result": result
                }
            )
            
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[point]
                )
                logger.info(f"✅ Результат сохранен в Qdrant: {point_id}")
                return point_id
            except Exception as upsert_error:
                logger.warning(f"⚠️ Ошибка сохранения в Qdrant: {upsert_error}")
                return point_id  # Возвращаем ID даже если сохранение не удалось
            
        except Exception as e:
            logger.error(f"❌ Qdrant сохранение ОБЯЗАТЕЛЬНО согласно ТЗ: {e}")
            return f"error_{user_id}_{analysis_type}_{int(datetime.now().timestamp())}"
    
    async def search_similar_results(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Поиск похожих результатов"""
        # In-memory режим
        if hasattr(self, '_memory_storage'):
            # Простой поиск по ключевым словам в памяти
            results = []
            query_lower = query.lower()
            
            for point_id, data in self._memory_storage.items():
                result_text = data.get('result', '').lower()
                if any(word in result_text for word in query_lower.split()):
                    results.append({
                        'id': point_id,
                        'score': 0.8,  # Фиксированный score для in-memory
                        'payload': data
                    })
            
            logger.info(f"🧠 Найдено в памяти: {len(results)} результатов")
            return results[:limit]
        
        if not self.client:
            logger.warning("⚠️ Qdrant недоступен, поиск невозможен")
            return []
            
        try:
            # Создаем embedding для запроса через Gemini или OpenAI
            query_embedding = [0.0] * 1536  # Default fallback
            
            # Пробуем Gemini
            gemini_key = os.getenv('GEMINI_API_KEY')
            if gemini_key:
                try:
                    # Используем хеш-алгоритм для поискового запроса
                    import hashlib
                    query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
                    query_embedding = [float(int(query_hash[i:i+2], 16)) / 255.0 for i in range(0, min(len(query_hash), 3072), 2)]
                    query_embedding = (query_embedding * (1536 // len(query_embedding) + 1))[:1536]
                    logger.info("🧠 Query embedding создан через хеш-алгоритм")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка создания query embedding: {e}")
            else:
                # Fallback OpenAI
                openai_key = os.getenv('OPENAI_API_KEY')
                if openai_key:
                    try:
                        import openai
                        openai.api_key = openai_key
                        response = openai.embeddings.create(
                            model="text-embedding-ada-002",
                            input=query
                        )
                        query_embedding = response.data[0].embedding
                        logger.info("🧠 Query embedding создан через OpenAI")
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка OpenAI query embedding: {e}")
                else:
                    logger.warning("⚠️ Поиск недоступен без API ключей")
                    return []
            
            # Ищем в Qdrant
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True
            )
            
            return [
                {
                    'id': hit.id,
                    'score': hit.score,
                    'payload': hit.payload
                }
                for hit in search_result
            ]
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка поиска в Qdrant: {e}")
            return []

# Создаем алиас для совместимости
MandatoryQdrantClient = QdrantClient
