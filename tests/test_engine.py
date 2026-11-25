import pytest
import threading
from datetime import datetime, timedelta, timezone
from src.mesh.engine import InventoryMesh

def test_reserve_and_commit():
    mesh = InventoryMesh()
    mesh.set_stock("store-london", "MILK-01", 10)
    assert mesh.get_available("store-london", "MILK-01") == 10

    ok, msg = mesh.reserve("res-1", "store-london", {"MILK-01": 3}, ttl_seconds=300)
    assert ok is True
    assert mesh.get_available("store-london", "MILK-01") == 7

    ok = mesh.commit("res-1")
    assert ok is True
    # Permanently deducted
    assert mesh.get_available("store-london", "MILK-01") == 7

def test_insufficient_stock_rollback():
    mesh = InventoryMesh()
    mesh.set_stock("store-london", "BREAD-01", 2)

    ok, msg = mesh.reserve("res-fail", "store-london", {"BREAD-01": 5})
    assert ok is False
    assert "insufficient" in msg
    assert mesh.get_available("store-london", "BREAD-01") == 2

def test_lease_expiration_sweep():
    mesh = InventoryMesh()
    mesh.set_stock("store-london", "APPLES-01", 20)

    now = datetime.now(timezone.utc)
    ok, _ = mesh.reserve("res-exp", "store-london", {"APPLES-01": 5}, ttl_seconds=60)
    assert ok is True
    assert mesh.get_available("store-london", "APPLES-01") == 15

    # 10 minutes later
    future = now + timedelta(minutes=10)
    swept = mesh.sweep_expired(future)
    assert swept == 1
    assert mesh.get_available("store-london", "APPLES-01") == 20

def test_concurrent_reservations():
    mesh = InventoryMesh()
    mesh.set_stock("store-fast", "WATER-01", 50)

    success_count = [0]
    lock = threading.Lock()

    def try_reserve(idx):
        ok, _ = mesh.reserve(f"r-{idx}", "store-fast", {"WATER-01": 2})
        if ok:
            with lock:
                success_count[0] += 1

    threads = [threading.Thread(target=try_reserve, args=(i,)) for i in range(40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Total capacity is 50, each takes 2 -> exactly 25 must succeed
    assert success_count[0] == 25
    assert mesh.get_available("store-fast", "WATER-01") == 0
