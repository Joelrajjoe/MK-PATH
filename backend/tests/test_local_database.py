import asyncio
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from app.database import (
    LocalFallbackCollection,
    LocalFallbackDB,
    LocalDeleteResult,
    LocalUpdateResult,
)
from app.main import app


def test_local_fallback_collection_crud():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            coll_file = tmp_path / "test_coll.json"
            coll = LocalFallbackCollection("test_coll", coll_file)

            # 1. Insert documents
            doc1 = {"dataset_id": "ds-100", "name": "alpha", "val": 10}
            doc2 = {"dataset_id": "ds-200", "name": "beta", "val": 20}
            doc3 = {"dataset_id": "ds-300", "name": "gamma", "val": 30}

            await coll.insert_one(doc1)
            await coll.insert_many([doc2, doc3])

            assert await coll.count_documents({}) == 3
            assert await coll.count_documents({"dataset_id": "ds-100"}) == 1

            # 2. Find and to_list
            cursor = coll.find({"name": {"$in": ["alpha", "beta"]}}).sort("val", -1)
            items = await cursor.to_list(length=10)
            assert len(items) == 2
            assert items[0]["name"] == "beta"
            assert items[1]["name"] == "alpha"

            # 3. Update one and update many
            up_res = await coll.update_one(
                {"dataset_id": "ds-100"},
                {"$set": {"status": "ready"}, "$inc": {"val": 5}}
            )
            assert isinstance(up_res, LocalUpdateResult)
            assert up_res.matched_count == 1
            assert up_res.modified_count == 1
            updated_doc = await coll.find_one({"dataset_id": "ds-100"})
            assert updated_doc["status"] == "ready"
            assert updated_doc["val"] == 15

            # 4. Delete one
            del_res = await coll.delete_one({"dataset_id": "ds-100"})
            assert isinstance(del_res, LocalDeleteResult)
            assert del_res.deleted_count == 1
            assert del_res.acknowledged is True
            assert await coll.count_documents({"dataset_id": "ds-100"}) == 0

            # Deleting non-existent returns deleted_count == 0
            del_res_empty = await coll.delete_one({"dataset_id": "ds-nonexistent"})
            assert del_res_empty.deleted_count == 0

            # 5. Delete many
            del_many_res = await coll.delete_many({"val": {"$gte": 20}})
            assert isinstance(del_many_res, LocalDeleteResult)
            assert del_many_res.deleted_count == 2
            assert await coll.count_documents({}) == 0

            # 6. Distinct and drop
            await coll.insert_many([
                {"category": "A", "num": 1},
                {"category": "B", "num": 2},
                {"category": "A", "num": 3},
            ])
            categories = await coll.distinct("category")
            assert set(categories) == {"A", "B"}

            await coll.drop()
            assert not coll_file.exists()

    asyncio.run(_run())


def test_delete_dataset_endpoint():
    """Verify DELETE /api/datasets/{id} executes smoothly with delete_one."""
    with TestClient(app) as client:
        # 1. Upload sample dataset
        csv_bytes = b"id,val\n1,10\n2,20\n"
        upload_res = client.post(
            "/api/datasets/upload",
            files={"file": ("test_del.csv", csv_bytes, "text/csv")},
        )
        assert upload_res.status_code == 201, upload_res.text
        data = upload_res.json()
        ds_id = data["datasets"][0]["dataset_id"]

        # 2. Delete dataset
        del_res = client.delete(f"/api/datasets/{ds_id}")
        assert del_res.status_code == 200, del_res.text
        del_data = del_res.json()
        assert del_data["deleted"] is True
        assert del_data["dataset_id"] == ds_id

        # 3. Confirm 404 when querying deleted dataset
        get_res = client.get(f"/api/datasets/{ds_id}")
        assert get_res.status_code == 404
