import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from .models import ItemStock, CartReservation, ReservationStatus

class InventoryMesh:
    def __init__(self):
        self._lock = threading.Lock()
        # (store_id, sku) -> ItemStock
        self._stock: Dict[Tuple[str, str], ItemStock] = {}
        # reservation_id -> CartReservation
        self._reservations: Dict[str, CartReservation] = {}

    def set_stock(self, store_id: str, sku: str, total_qty: int):
        with self._lock:
            key = (store_id, sku)
            if key in self._stock:
                self._stock[key].total_qty = total_qty
            else:
                self._stock[key] = ItemStock(sku=sku, store_id=store_id, total_qty=total_qty)

    def get_available(self, store_id: str, sku: str) -> int:
        with self._lock:
            key = (store_id, sku)
            item = self._stock.get(key)
            return item.available_qty if item else 0

    def reserve(self, reservation_id: str, store_id: str, items: Dict[str, int], ttl_seconds: int = 600) -> Tuple[bool, str]:
        with self._lock:
            now = datetime.now(timezone.utc)
            # 1. Verify availability for all items (atomic all-or-nothing)
            for sku, qty in items.items():
                key = (store_id, sku)
                item = self._stock.get(key)
                if not item or item.available_qty < qty:
                    return False, f"insufficient stock for SKU {sku}"

            # 2. Apply reservation
            for sku, qty in items.items():
                key = (store_id, sku)
                self._stock[key].reserved_qty += qty

            expires = now + timedelta(seconds=ttl_seconds)
            res = CartReservation(
                reservation_id=reservation_id,
                store_id=store_id,
                items=items.copy(),
                expires_at=expires,
                status=ReservationStatus.CONFIRMED
            )
            self._reservations[reservation_id] = res
            return True, "reserved"

    def commit(self, reservation_id: str) -> bool:
        """Deducts stock permanently upon customer successful payment."""
        with self._lock:
            res = self._reservations.get(reservation_id)
            if not res or res.status != ReservationStatus.CONFIRMED:
                return False

            store_id = res.store_id
            for sku, qty in res.items.items():
                key = (store_id, sku)
                item = self._stock.get(key)
                if item:
                    item.total_qty = max(0, item.total_qty - qty)
                    item.reserved_qty = max(0, item.reserved_qty - qty)

            res.status = ReservationStatus.CONFIRMED
            del self._reservations[reservation_id]
            return True

    def rollback(self, reservation_id: str) -> bool:
        """Releases reserved capacity back to inventory upon cart abandonment or payment failure."""
        with self._lock:
            res = self._reservations.get(reservation_id)
            if not res or res.status != ReservationStatus.CONFIRMED:
                return False

            store_id = res.store_id
            for sku, qty in res.items.items():
                key = (store_id, sku)
                item = self._stock.get(key)
                if item:
                    item.reserved_qty = max(0, item.reserved_qty - qty)

            res.status = ReservationStatus.RELEASED
            del self._reservations[reservation_id]
            return True

    def sweep_expired(self, current_time: datetime) -> int:
        """Sweeps and rolls back any cart reservations past their TTL lease."""
        with self._lock:
            expired_ids = []
            for res_id, res in self._reservations.items():
                if res.status == ReservationStatus.CONFIRMED and current_time > res.expires_at:
                    expired_ids.append(res_id)

            for res_id in expired_ids:
                res = self._reservations[res_id]
                store_id = res.store_id
                for sku, qty in res.items.items():
                    key = (store_id, sku)
                    item = self._stock.get(key)
                    if item:
                        item.reserved_qty = max(0, item.reserved_qty - qty)
                res.status = ReservationStatus.EXPIRED
                del self._reservations[res_id]

            return len(expired_ids)
