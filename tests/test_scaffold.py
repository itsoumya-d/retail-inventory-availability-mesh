from src.mesh.models import ItemStock

def test_models_scaffold():
    stock = ItemStock(sku="SKU-100", store_id="store-1", total_qty=20, reserved_qty=5)
    assert stock.available_qty == 15
