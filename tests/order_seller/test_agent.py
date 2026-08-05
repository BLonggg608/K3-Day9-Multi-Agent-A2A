import pytest
import pandas as pd
from src.order_seller.agent import OrderSellerAgent

class MockDataStore:
    def get_order(self, order_id):
        if order_id == "ord1":
            return pd.DataFrame([{"order_id": "ord1", "order_status": "delivered", "order_delivered_carrier_date": pd.to_datetime("2017-10-06")}])
        elif order_id == "ord_canceled":
            return pd.DataFrame([{"order_id": "ord_canceled", "order_status": "canceled", "order_delivered_carrier_date": pd.NaT}])
        elif order_id == "ord_empty":
            return pd.DataFrame([{"order_id": "ord_empty", "order_status": "delivered", "order_delivered_carrier_date": pd.to_datetime("2017-10-06")}])
        return pd.DataFrame()
        
    def get_order_items(self, order_id):
        if order_id == "ord1":
            return pd.DataFrame([
                {"order_id": "ord1", "order_item_id": 1, "seller_id": "sel1", "price": 50.0, "freight_value": 10.0, "shipping_limit_date": pd.to_datetime("2017-10-05")},
                {"order_id": "ord1", "order_item_id": 2, "seller_id": "sel2", "price": 100.0, "freight_value": 20.0, "shipping_limit_date": pd.to_datetime("2017-10-07")}
            ])
        elif order_id == "ord_canceled":
            return pd.DataFrame([
                {"order_id": "ord_canceled", "order_item_id": 1, "seller_id": "sel1", "price": 50.0, "freight_value": 10.0, "shipping_limit_date": pd.to_datetime("2017-10-05")}
            ])
        return pd.DataFrame()

def test_analyze_normal_order():
    agent = OrderSellerAgent(data_store=MockDataStore())
    res = agent.analyze({"case": {"customer_request": {"claimed_order_id": "ord1"}}})
    
    assert res.ok
    assert res.data["order_id"] == "ord1"
    assert res.data["order_status"] == "delivered"
    assert res.data["item_total_brl"] == 150.0
    assert res.data["freight_total_brl"] == 30.0
    assert res.data["seller_handoff_violations"] is True
    assert "sel1" in res.data["seller_ids"]
    assert "sel2" in res.data["seller_ids"]
    assert "order:ord1" in res.data["evidence_ids"]
    assert "item:ord1:1" in res.data["evidence_ids"]
    assert "seller:sel1" in res.data["evidence_ids"]
    assert res.data["violating_seller_ids"] == ["sel1"]
    assert res.data["order_delivered_carrier_date"] == "2017-10-06 00:00:00"

def test_analyze_canceled_order():
    agent = OrderSellerAgent(data_store=MockDataStore())
    res = agent.analyze({"case": {"customer_request": {"claimed_order_id": "ord_canceled"}}})
    
    assert res.ok
    assert res.data["order_status"] == "canceled"
    assert res.data["seller_handoff_violations"] is False

def test_analyze_unavailable_order():
    agent = OrderSellerAgent(data_store=MockDataStore())
    res = agent.analyze({"case": {"customer_request": {"claimed_order_id": "missing"}}})
    assert not res.ok
    assert res.errors == ["Order not found: missing"]

def test_analyze_empty_items():
    agent = OrderSellerAgent(data_store=MockDataStore())
    res = agent.analyze({"case": {"customer_request": {"claimed_order_id": "ord_empty"}}})
    assert res.ok
    assert res.data["item_total_brl"] == 0.0
