import pytest
import pandas as pd
from src.order_seller.queries import OrderDataStore
import io

MOCK_ORDERS = """order_id,order_status,order_delivered_carrier_date
ord1,delivered,2017-10-04 19:55:00
ord2,canceled,
"""

MOCK_ITEMS = """order_id,order_item_id,seller_id,price,freight_value,shipping_limit_date
ord1,1,sel1,50.0,10.0,2017-09-19 09:45:35
ord1,2,sel2,100.0,20.0,2017-10-05 09:45:35
"""

MOCK_SELLERS = """seller_id,seller_zip_code_prefix
sel1,13023
sel2,13024
"""

def test_queries(monkeypatch):
    def mock_read_csv(filepath):
        filename = str(filepath).split("/")[-1]
        if "olist_orders_dataset.csv" in filename:
            return pd.read_csv(io.StringIO(MOCK_ORDERS))
        elif "olist_order_items_dataset.csv" in filename:
            return pd.read_csv(io.StringIO(MOCK_ITEMS))
        elif "olist_sellers_dataset.csv" in filename:
            return pd.read_csv(io.StringIO(MOCK_SELLERS))
            
    monkeypatch.setattr(pd, "read_csv", mock_read_csv)
    
    store = OrderDataStore("dummy_dir")
    
    order = store.get_order("ord1")
    assert len(order) == 1
    assert order.iloc[0]["order_status"] == "delivered"
    
    items = store.get_order_items("ord1")
    assert len(items) == 2
    
    sellers = store.get_sellers(["sel1", "sel2"])
    assert len(sellers) == 2
