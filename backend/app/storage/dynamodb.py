"""DynamoDB-based storage implementation."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key, Attr

from app.api.schemas import (
    Transaction,
    CustomerBehavior,
    DecisionResponse,
    AuditEvent,
    HitlCase,
    TransactionSummary,
)
from app.storage.interfaces import TransactionRepository, AuditRepository, HitlRepository


def _to_decimal(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, Decimal):
        return value
    if isinstance(value, dict):
        return {k: _to_decimal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_decimal(v) for v in value]
    return value


def _from_decimal(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    if isinstance(value, dict):
        return {k: _from_decimal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_from_decimal(v) for v in value]
    return value


class DynamoDBTransactionRepository(TransactionRepository):
    """DynamoDB transaction repository."""

    def __init__(self, table_name: str, region: str | None = None) -> None:
        resource = boto3.resource("dynamodb", region_name=region)
        self.table = resource.Table(table_name)

    def save_transaction(self, transaction: Transaction) -> None:
        existing = self.table.get_item(Key={"transaction_id": transaction.transaction_id}).get("Item")
        item = transaction.model_dump()
        item["transaction_id"] = transaction.transaction_id
        item["entity_type"] = "transaction"
        if existing:
            for key in ("decision_data", "decision", "confidence"):
                if key in existing:
                    item[key] = existing[key]
        self.table.put_item(Item=_to_decimal(item))

    def get_transaction(self, transaction_id: str) -> Transaction | None:
        item = self.table.get_item(Key={"transaction_id": transaction_id}).get("Item")
        if not item or item.get("entity_type") != "transaction":
            return None
        item = _from_decimal(item)
        return Transaction(**item)

    def list_transactions(self) -> list[TransactionSummary]:
        items: list[dict[str, Any]] = []
        response = self.table.scan(FilterExpression=Attr("entity_type").eq("transaction"))
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.scan(
                FilterExpression=Attr("entity_type").eq("transaction"),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        summaries: list[TransactionSummary] = []
        for item in items:
            item = _from_decimal(item)
            summaries.append(TransactionSummary(
                transaction_id=item["transaction_id"],
                customer_id=item["customer_id"],
                amount=item["amount"],
                currency=item["currency"],
                timestamp=item["timestamp"],
                decision=item.get("decision"),
                confidence=item.get("confidence"),
            ))
        return summaries

    def save_decision(self, transaction_id: str, decision: DecisionResponse) -> None:
        decision_data = decision.model_dump()
        self.table.update_item(
            Key={"transaction_id": transaction_id},
            UpdateExpression="SET decision_data=:decision_data, #decision=:decision, confidence=:confidence",
            ExpressionAttributeValues=_to_decimal({
                ":decision_data": decision_data,
                ":decision": decision.decision,
                ":confidence": decision.confidence,
            }),
            ExpressionAttributeNames={
                "#decision": "decision",
            },
        )

    def get_decision(self, transaction_id: str) -> DecisionResponse | None:
        item = self.table.get_item(Key={"transaction_id": transaction_id}).get("Item")
        if not item or "decision_data" not in item:
            return None
        decision_data = _from_decimal(item["decision_data"])
        return DecisionResponse(**decision_data)

    def save_customer_behavior(self, customer: CustomerBehavior) -> None:
        item = customer.model_dump()
        item["transaction_id"] = f"CUSTOMER#{customer.customer_id}"
        item["entity_type"] = "customer"
        self.table.put_item(Item=_to_decimal(item))

    def get_customer_behavior(self, customer_id: str) -> CustomerBehavior | None:
        key = f"CUSTOMER#{customer_id}"
        item = self.table.get_item(Key={"transaction_id": key}).get("Item")
        if not item or item.get("entity_type") != "customer":
            return None
        item = _from_decimal(item)
        return CustomerBehavior(**item)

    def clear(self) -> None:
        items: list[dict[str, Any]] = []
        response = self.table.scan(ProjectionExpression="transaction_id")
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.scan(
                ProjectionExpression="transaction_id",
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
        with self.table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"transaction_id": item["transaction_id"]})


class DynamoDBAuditRepository(AuditRepository):
    """DynamoDB audit repository."""

    def __init__(self, table_name: str, region: str | None = None) -> None:
        resource = boto3.resource("dynamodb", region_name=region)
        self.table = resource.Table(table_name)

    @staticmethod
    def _build_sk(event: AuditEvent) -> str:
        return f"ts#{event.ts}#seq#{event.seq:06d}#agent#{event.agent}"

    def append_event(self, event: AuditEvent) -> None:
        item = event.model_dump()
        item["transaction_id"] = event.transaction_id
        item["sk"] = self._build_sk(event)
        item["entity_type"] = "audit"
        self.table.put_item(Item=_to_decimal(item))

    def get_events(self, transaction_id: str) -> list[AuditEvent]:
        items: list[dict[str, Any]] = []
        response = self.table.query(
            KeyConditionExpression=Key("transaction_id").eq(transaction_id),
            ScanIndexForward=True,
        )
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.query(
                KeyConditionExpression=Key("transaction_id").eq(transaction_id),
                ScanIndexForward=True,
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
        return [AuditEvent(**_from_decimal(item)) for item in items]

    def get_next_seq(self, transaction_id: str) -> int:
        max_seq = 0
        response = self.table.query(
            KeyConditionExpression=Key("transaction_id").eq(transaction_id),
            ProjectionExpression="seq",
        )
        for item in response.get("Items", []):
            seq = int(_from_decimal(item.get("seq", 0)))
            if seq > max_seq:
                max_seq = seq
        while "LastEvaluatedKey" in response:
            response = self.table.query(
                KeyConditionExpression=Key("transaction_id").eq(transaction_id),
                ProjectionExpression="seq",
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            for item in response.get("Items", []):
                seq = int(_from_decimal(item.get("seq", 0)))
                if seq > max_seq:
                    max_seq = seq
        return max_seq + 1 if max_seq > 0 else 1

    def clear(self) -> None:
        items: list[dict[str, Any]] = []
        response = self.table.scan(ProjectionExpression="transaction_id, sk")
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.scan(
                ProjectionExpression="transaction_id, sk",
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
        with self.table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"transaction_id": item["transaction_id"], "sk": item["sk"]})


class DynamoDBHitlRepository(HitlRepository):
    """DynamoDB HITL case repository."""

    def __init__(self, table_name: str, region: str | None = None) -> None:
        resource = boto3.resource("dynamodb", region_name=region)
        self.table = resource.Table(table_name)

    def create_case(self, case: HitlCase) -> None:
        item = case.model_dump()
        self.table.put_item(Item=_to_decimal(item))

    def get_case(self, case_id: str) -> HitlCase | None:
        item = self.table.get_item(Key={"case_id": case_id}).get("Item")
        if not item:
            return None
        return HitlCase(**_from_decimal(item))

    def get_case_by_transaction(self, transaction_id: str) -> HitlCase | None:
        response = self.table.query(
            IndexName="transaction-id-index",
            KeyConditionExpression=Key("transaction_id").eq(transaction_id),
            Limit=1,
        )
        items = response.get("Items", [])
        if not items:
            return None
        return HitlCase(**_from_decimal(items[0]))

    def list_open_cases(self) -> list[HitlCase]:
        response = self.table.query(
            IndexName="status-index",
            KeyConditionExpression=Key("status").eq("OPEN"),
        )
        return [HitlCase(**_from_decimal(item)) for item in response.get("Items", [])]

    def resolve_case(self, case_id: str, resolution: dict[str, Any], resolved_at: str) -> None:
        self.table.update_item(
            Key={"case_id": case_id},
            UpdateExpression="SET #status=:status, resolution=:resolution, resolved_at=:resolved_at",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues=_to_decimal({
                ":status": "RESOLVED",
                ":resolution": resolution,
                ":resolved_at": resolved_at,
            }),
        )

    def clear(self) -> None:
        items: list[dict[str, Any]] = []
        response = self.table.scan(ProjectionExpression="case_id")
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = self.table.scan(
                ProjectionExpression="case_id",
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
        with self.table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"case_id": item["case_id"]})
