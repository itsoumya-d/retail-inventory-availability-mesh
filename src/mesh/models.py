from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional
from datetime import datetime

class ReservationStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"

@dataclass
class ItemStock:
    sku: str
    store_id: str
    total_qty: int
    reserved_qty: int = 0

    @property
    def available_qty(self) -> int:
        return max(0, self.total_qty - self.reserved_qty)

@dataclass
class CartReservation:
    reservation_id: str
    store_id: str
    items: Dict[str, int]  # sku -> qty
    expires_at: datetime
    status: ReservationStatus = ReservationStatus.CONFIRMED
