import pandas as pd
from pathlib import Path
from typing import List

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

class OrderDataStore:
    def __init__(self, data_dir: str | Path = DEFAULT_DATA_DIR):
        data_path = Path(data_dir)
        self.orders = pd.read_csv(data_path / "olist_orders_dataset.csv")
        self.items = pd.read_csv(data_path / "olist_order_items_dataset.csv")
        self.sellers = pd.read_csv(data_path / "olist_sellers_dataset.csv")
        
        # Convert date columns to datetime
        self.orders['order_delivered_carrier_date'] = pd.to_datetime(self.orders['order_delivered_carrier_date'])
        self.items['shipping_limit_date'] = pd.to_datetime(self.items['shipping_limit_date'])

    def get_order(self, order_id: str) -> pd.DataFrame:
        return self.orders[self.orders["order_id"] == order_id]

    def get_order_items(self, order_id: str) -> pd.DataFrame:
        return self.items[self.items["order_id"] == order_id]

    def get_sellers(self, seller_ids: List[str]) -> pd.DataFrame:
        return self.sellers[self.sellers["seller_id"].isin(seller_ids)]
