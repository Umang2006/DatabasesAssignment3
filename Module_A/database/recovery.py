"""
recovery.py -- Standalone Crash Recovery
Scans the WAL and undoes every transaction that was not committed.

Usage
-----
    from database import recovery
    recovery.recover(wal_path="wal.log", db_manager=db)

Call this ONCE at startup, after loading the last durability snapshot but
before accepting any new transactions.
"""

import json
import os


def recover(wal_path: str, db_manager) -> None:
    """
    Read *wal_path* and undo every incomplete transaction found there.

    An "incomplete" transaction is one that has a BEGIN entry but no
    corresponding COMMIT or ROLLBACK entry -- i.e. the process was killed
    in the middle of it.

    Parameters
    ----------
    wal_path   : str              - path to the WAL file
    db_manager : DatabaseManager  - the in-memory DBMS (already loaded
                                    from the last durability snapshot)
    """
    if not os.path.exists(wal_path):
        print("[Recovery] No WAL file found.  Clean start -- nothing to undo.")
        return

    # - 1. Parse the log -
    entries   = []
    with open(wal_path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # tolerate torn last line

    if not entries:
        print("[Recovery] WAL is empty.  Nothing to do.")
        return

    # - 2. Classify each transaction -
    txn_ops   = {}    # txn_id -> [op_dict, ...]   (only data-change ops)
    committed = set()
    rolled    = set()

    for e in entries:
        tid = e["txn_id"]
        if e["op_type"] == "BEGIN":
            txn_ops.setdefault(tid, [])
        elif e["op_type"] in ("INSERT", "UPDATE", "DELETE"):
            txn_ops.setdefault(tid, []).append(e)
        elif e["op_type"] == "COMMIT":
            committed.add(tid)
        elif e["op_type"] == "ROLLBACK":
            rolled.add(tid)

    incomplete = set(txn_ops) - committed - rolled

    print(f"[Recovery] WAL entries: {len(entries)}  |  "
          f"Committed: {len(committed)}  |  "
          f"Rolled-back: {len(rolled)}  |  "
          f"Incomplete: {len(incomplete)}")

    if not incomplete:
        print("[Recovery] All transactions are complete.  No rollback needed.")
        return

    # - 3. Undo incomplete transactions (newest-first for safety) -
    for tid in sorted(incomplete, reverse=True):
        ops = txn_ops[tid]
        print(f"[Recovery] Undoing TXN {tid}  ({len(ops)} operation(s))-")

        for op in reversed(ops):   # reverse chronological = undo order
            _undo(op, db_manager)

        print(f"[Recovery] TXN {tid} successfully rolled back.")

    print("[Recovery] -  Recovery complete.")


# - Internal -

def _undo(op: dict, db_manager) -> None:
    """Apply the undo image of *op* to the in-memory database."""
    table = db_manager.get_table(op.get("table"))
    if table is None:
        return   # table may not exist if the CREATE itself was partial

    op_type = op["op_type"]

    if op_type == "INSERT":
        if op["before"] is None:
            # Key was brand-new when inserted -> delete it
            ok = table.tree.delete(op["key"])
            if ok:
                table.record_count = max(0, table.record_count - 1)
        else:
            # Key existed before the insert -> restore original value
            table.tree.update(op["key"], op["before"])

    elif op_type == "UPDATE":
        if op["before"] is not None:
            table.tree.update(op["key"], op["before"])

    elif op_type == "DELETE":
        if op["before"] is not None:
            table.tree.insert(op["key"], op["before"])
            table.record_count += 1