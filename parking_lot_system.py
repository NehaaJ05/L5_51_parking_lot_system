
"""Manage parking slots, fees, tickets, and parking manifest exports."""

import ast
import hashlib
import operator
import secrets
from pathlib import Path

PARKING_SLOTS = {
    "P01": {
        "plate": "KA01AB1234",
        "hours": 2,
        "rate": 20.0,
        "is_occupied": True,
    },
    "P02": {
        "plate": "TN07CD5678",
        "hours": 0,
        "rate": 20.0,
        "is_occupied": False,
    },
    "P03": {
        "plate": "MH02EF9012",
        "hours": 4,
        "rate": 30.0,
        "is_occupied": True,
    },
}

TOTAL_COLLECTIONS = {"amount": 0.0}


def park_vehicle(slot_id, plate_no, hours_booked=1, entry_logs=None):
    """Park a vehicle and record its booking."""
    if entry_logs is None:
        entry_logs = []

    if slot_id not in PARKING_SLOTS:
        return False

    slot = PARKING_SLOTS[slot_id]
    if slot["is_occupied"]:
        return False

    slot["plate"] = plate_no
    slot["hours"] = hours_booked
    slot["is_occupied"] = True
    TOTAL_COLLECTIONS["amount"] += slot["rate"] * hours_booked
    entry_logs.append(
        f"Vehicle {plate_no} parked at slot {slot_id} "
        f"for {hours_booked} hours."
    )
    return True


def release_slot(slot_id):
    """Release a slot and clear its booking details."""
    slot = PARKING_SLOTS.get(slot_id)
    if slot is None:
        return False

    slot["is_occupied"] = False
    slot["plate"] = ""
    slot["hours"] = 0
    return True


def check_slot_availability(slot_id):
    """Check whether a parking slot exists and is vacant."""
    slot = PARKING_SLOTS.get(slot_id)
    return slot is not None and not slot["is_occupied"]


def calculate_parking_fee(slot_id, surge_expr):
    """Calculate a fee from a restricted arithmetic expression."""
    if slot_id not in PARKING_SLOTS:
        raise ValueError(f"Unknown parking slot: {slot_id}")

    base_rate = PARKING_SLOTS[slot_id]["rate"]

    try:
        expression = ast.parse(surge_expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid fee expression") from exc

    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.USub,
        ast.UAdd,
    )

    for node in ast.walk(expression):
        if not isinstance(node, allowed_nodes):
            raise ValueError("Unsupported fee expression")
        if isinstance(node, ast.Name) and node.id != "base_rate":
            raise ValueError("Only base_rate is allowed")
        if isinstance(node, ast.Constant) and (
            not isinstance(node.value, (int, float))
            or isinstance(node.value, bool)
        ):
            raise ValueError("Only numeric constants are allowed")

    return _evaluate_fee_expression(expression.body, base_rate)


def _evaluate_fee_expression(node, base_rate):
    """Evaluate permitted arithmetic without executing arbitrary code."""
    if isinstance(node, ast.Constant):
        result = node.value
    elif isinstance(node, ast.Name):
        result = base_rate
    elif isinstance(node, ast.UnaryOp):
        value = _evaluate_fee_expression(node.operand, base_rate)
        result = value if isinstance(node.op, ast.UAdd) else -value
    else:
        left = _evaluate_fee_expression(node.left, base_rate)
        right = _evaluate_fee_expression(node.right, base_rate)
        operations = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
        }
        operation = operations.get(type(node.op))
        if operation is None:
            raise ValueError("Unsupported arithmetic operation")
        result = operation(left, right)

    return result


def generate_vehicle_hash(plate_no):
    """Generate a SHA-256 digest for a vehicle plate."""
    return hashlib.sha256(plate_no.encode("utf-8")).hexdigest()


def generate_ticket_pin():
    """Generate a cryptographically strong four-digit ticket PIN."""
    return str(secrets.randbelow(9000) + 1000)


def export_parking_manifest(filename="parking_manifest.txt"):
    """Export parking slot information to a UTF-8 text file."""
    path = Path(filename)
    path.write_text(repr(PARKING_SLOTS), encoding="utf-8")
    print(f"Parking manifest exported to: {path}")


def get_available_summary():
    """Count the currently vacant parking slots."""
    return sum(
        not slot["is_occupied"] for slot in PARKING_SLOTS.values()
    )


def main():
    """Run a demonstration of the parking lot system."""
    park_vehicle("P02", "DL03GH3456", 3)
    release_slot("P01")

    print("Is P02 available:", check_slot_availability("P02"))
    print(
        "Surge Parking Fee:",
        calculate_parking_fee("P03", "base_rate * 1.50"),
    )
    print("Vehicle Hash:", generate_vehicle_hash("KA01AB1234"))
    print("Ticket PIN:", generate_ticket_pin())
    export_parking_manifest()
    print("Vacant slots:", get_available_summary())


if __name__ == "__main__":
    main()
