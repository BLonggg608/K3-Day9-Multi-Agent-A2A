from typing import Any
import pandas as pd

from src.shared.contracts import AgentResult
from src.order_seller.queries import OrderDataStore


def _serialize_timestamp(value: Any) -> str | None:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat(sep=" ")
    return str(value)


class OrderSellerAgent:
    name: str = "order_seller"
    
    def __init__(self, data_store: OrderDataStore = None):
        if data_store is None:
            self.data_store = OrderDataStore()
        else:
            self.data_store = data_store

    def analyze(self, context: dict[str, Any]) -> AgentResult:
        case = context.get("case", {})
        customer_request = case.get("customer_request", {})
        order_id = customer_request.get("claimed_order_id")
        
        if not order_id:
            return AgentResult(
                agent=self.name,
                ok=False,
                errors=["claimed_order_id is missing from case context"]
            )
            
        order_df = self.data_store.get_order(order_id)
        if order_df.empty:
            return AgentResult(
                agent=self.name,
                ok=False,
                errors=[f"Order not found: {order_id}"]
            )
            
        order_row = order_df.iloc[0]
        order_status = order_row["order_status"]
        order_delivered_carrier_date = order_row["order_delivered_carrier_date"]
        
        items_df = self.data_store.get_order_items(order_id)
        
        items = []
        seller_ids = []
        item_total_brl = 0.0
        freight_total_brl = 0.0
        seller_handoff_violations = False
        violating_seller_ids: list[str] = []
        evidence_ids = [f"order:{order_id}"]
        
        if not items_df.empty:
            item_total_brl = items_df["price"].sum()
            freight_total_brl = items_df["freight_value"].sum()
            seller_ids = items_df["seller_id"].unique().tolist()
            
            if pd.notna(order_delivered_carrier_date):
                # check if order_delivered_carrier_date > shipping_limit_date
                violations = items_df[
                    order_delivered_carrier_date > items_df["shipping_limit_date"]
                ]
                if not violations.empty:
                    seller_handoff_violations = True
                    violating_seller_ids = (
                        violations["seller_id"].dropna().unique().tolist()
                    )
            
            # Convert timestamp columns to string for JSON serialization
            items_df_copy = items_df.copy()
            items_df_copy['shipping_limit_date'] = items_df_copy['shipping_limit_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
            items = items_df_copy.to_dict(orient="records")
            
            for _, item_row in items_df.iterrows():
                evidence_ids.append(
                    f"item:{order_id}:{int(item_row['order_item_id'])}"
                )
                
        item_total_brl = round(float(item_total_brl), 2)
        freight_total_brl = round(float(freight_total_brl), 2)
        
        data = {
            "order_id": order_id,
            "order_status": order_status,
            "order_delivered_customer_date": _serialize_timestamp(
                order_row.get("order_delivered_customer_date")
            ),
            "order_estimated_delivery_date": _serialize_timestamp(
                order_row.get("order_estimated_delivery_date")
            ),
            "order_delivered_carrier_date": _serialize_timestamp(
                order_delivered_carrier_date
            ),
            "items": items,
            "seller_ids": seller_ids,
            "item_total_brl": item_total_brl,
            "freight_total_brl": freight_total_brl,
            "seller_handoff_violations": seller_handoff_violations,
            "violating_seller_ids": violating_seller_ids,
            "evidence_ids": evidence_ids
        }
        
        return AgentResult(
            agent=self.name,
            ok=True,
            data=data,
            evidence_ids=evidence_ids
        )
