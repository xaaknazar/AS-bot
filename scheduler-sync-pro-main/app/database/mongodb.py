import certifi
from typing import Any
from datetime import datetime
from bson import ObjectId

from fastapi import HTTPException
from pymongo import MongoClient, DESCENDING, errors

from app.config import settings


class MongoDBRepository:
    def __init__(self, db_name: str):
        self._client = MongoClient(
            settings.mongodb_url, tlsCAFile=certifi.where()
        )
        self._db = self._client.get_database(db_name)

    @staticmethod
    def execute(func, *args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except errors.DuplicateKeyError:
            raise HTTPException(400, "Document already exists")
        except errors.WriteError as e:
            raise HTTPException(400, str(e))
        except errors.PyMongoError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(500, str(e))

    def _collection_is_exists(self, collection_name: str) -> bool:
        return collection_name in self._db.list_collection_names()

    def _validate_collection(self, collection_name: str) -> None:
        if not self._collection_is_exists(collection_name):
            raise HTTPException(404, "Collection not found")

    def create_index(self, collection_name: str, field: str) -> None:
        self._db[collection_name].create_index(
            [(field, DESCENDING)],
            unique=True
        )

    def get_collections(self) -> list[str]:
        return self._db.list_collection_names()

    def get_collection(
            self,
            collection_name: str,
            sort_by: str = "_id",
            order_by: int = DESCENDING,
            query: dict = None,
            fields: list[str] = None,
            limit: int = 100,
            skip: int = 0
    ) -> list[dict]:
        self._validate_collection(collection_name)
        projection = {}
        if fields:
            projection = {field: 1 for field in fields}

        cursor = (
            self._db[collection_name]
            .find(query, projection)
            .sort(sort_by, order_by)
            .skip(skip)
            .limit(limit)
        )
        result = cursor.to_list()

        return result

    def create_collection(
            self,
            collection_name: str
    ) -> None:
        if not self._collection_is_exists(collection_name):
            self._db.create_collection(collection_name)
            self.create_index(collection_name, "datetime")

    def delete_collection(
            self,
            collection_name: str
    ) -> None:
        if self._collection_is_exists(collection_name):
            self._db.drop_collection(collection_name)

    def get_document(
            self,
            id: ObjectId,
            collection_name: str
    ) -> dict | None:
        self._validate_collection(collection_name)
        return self._db[collection_name].find_one({"_id": id})

    def get_last_document(
            self,
            collection_name: str,
            validate_collection: bool = True
    ) -> dict | None:
        if validate_collection:
            self._validate_collection(collection_name)
        return self._db[collection_name].find_one(sort=[('_id', -1)])

    def _create(self, document: dict, collection_name: str) -> ObjectId:
        result = self._db[collection_name].insert_one(document)
        return result.inserted_id

    def create_document(
            self,
            document: dict,
            set_timestamp: bool,
            collection_name: str
    ) -> dict:
        if set_timestamp:
            now = datetime.now()
            document.setdefault('created_at', now)
            document.setdefault('updated_at', now)

        inserted_id = self.execute(
            self._create, document, collection_name
        )

        return self.get_document(
            inserted_id, collection_name
        )

    def _update(
            self, id: ObjectId, update_fields: dict, collection_name: str
    ) -> int:
        result = self._db[collection_name].update_one(
            {'_id': id},
            {'$set': update_fields}
        )
        return result.matched_count

    def update_document(
            self,
            id: ObjectId,
            update_fields: dict,
            update_timestamp: bool,
            collection_name: str
    ) -> dict:
        if update_timestamp:
            update_fields['updated_at'] = datetime.now()

        matched_count = self.execute(
            self._update, id, update_fields, collection_name
        )

        if matched_count == 0:
            raise HTTPException(404, "Document not found")

        return self.get_document(id, collection_name)

    def delete_document(
            self,
            id: ObjectId,
            collection_name: str
    ) -> None:
        result = self._db[collection_name].delete_one({'_id': id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Document not found")
