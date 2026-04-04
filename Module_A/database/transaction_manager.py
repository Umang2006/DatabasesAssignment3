"""
transaction_manager.py -- Transaction Engine
Provides BEGIN / COMMIT / ROLLBACK semantics on top of the B+ Tree DBMS.

Design
------
* Every mutating operation (insert / update / delete) is logged to the WAL
  BEFORE the B+ Tree is modified (Write-Ahead Log protocol).
* On COMMIT, the complete database state is serialised to a JSON snapshot
  file (durability checkpoint).
* On ROLLBACK, every operation is undone in reverse order using the
  "before" image stored in the WAL entry.
* On startup, call TransactionManager.recover() to undo any transaction
  that was in-flight when the process was killed.
"""

import json
import os
import threading

from .wal import WriteAheadLog, WALEntry


class TransactionManager:
    """
    Coordinates ACID-compliant transactions over a DatabaseManager instance.

    Parameters
    ----------
    db_manager    : DatabaseManager - the in-memory DBMS
    wal_path      : path for the Write-Ahead Log file
    snapshot_path : path for the JSON durability snapshot
    """

    def __init__(self, db_manager,
                 wal_path="wal.log",
                 snapshot_path="db_snapshot.json"):
        self.db            = db_manager
        self.wal           = WriteAheadLog(wal_path)
        self.snapshot_path = snapshot_path

        self._counter      = 0
        self._counter_lock = threading.Lock()
        # active_txns: txn_id -> list[WALEntry]  (in-memory undo log)
        self._active       = {}

    # - Transaction control -

    def begin(self) -> int:
        """Open a new transaction and return its id."""
        txn_id = self._next_id()
        self._active[txn_id] = []
        self.wal.append(WALEntry(txn_id, "BEGIN"))
        print(f"[TXN {txn_id}] BEGIN")
        return txn_id

    def commit(self, txn_id: int) -> None:
        """
        Flush COMMIT to WAL, remove transaction from active set,
        and write a full durability snapshot.
        """
        if txn_id not in self._active:
            raise RuntimeError(f"TXN {txn_id} is not active.")
        self.wal.append(WALEntry(txn_id, "COMMIT"))
        del self._active[txn_id]
        self._save_snapshot()
        print(f"[TXN {txn_id}] COMMIT  (snapshot saved -> {self.snapshot_path})")

    def rollback(self, txn_id: int) -> None:
        """
        Undo every operation of *txn_id* in reverse order,
        then flush ROLLBACK to WAL.
        """
        ops = self._active.pop(txn_id, [])
        for op in reversed(ops):
            self._undo_op(op)
        self.wal.append(WALEntry(txn_id, "ROLLBACK"))
        print(f"[TXN {txn_id}] ROLLBACK  ({len(ops)} operation(s) undone)")

    # - Data-manipulation operations -

    def insert(self, txn_id: int, table_name: str, key, record: dict) -> None:
        """Insert *record* at *key*; log to WAL before touching the tree."""
        table  = self._require_table(table_name)
        before = table.select(key)                  # None means the key is new

        entry = WALEntry(txn_id, "INSERT",
                         table=table_name, key=key,
                         before=before, after=record)
        self.wal.append(entry)
        self._active[txn_id].append(entry)

        # Apply to tree
        table.tree.insert(key, record)
        if before is None:
            table.record_count += 1
        print(f"  [TXN {txn_id}] INSERT  key={key}  ->  {record}")

    def update(self, txn_id: int, table_name: str, key, new_record: dict) -> None:
        """Update the record at *key*; log old value for undo."""
        table  = self._require_table(table_name)
        before = table.select(key)

        entry = WALEntry(txn_id, "UPDATE",
                         table=table_name, key=key,
                         before=before, after=new_record)
        self.wal.append(entry)
        self._active[txn_id].append(entry)

        table.tree.update(key, new_record)
        print(f"  [TXN {txn_id}] UPDATE  key={key}  ->  {new_record}")

    def delete(self, txn_id: int, table_name: str, key) -> None:
        """Delete *key*; log old value so a rollback can re-insert it."""
        table  = self._require_table(table_name)
        before = table.select(key)

        entry = WALEntry(txn_id, "DELETE",
                         table=table_name, key=key,
                         before=before, after=None)
        self.wal.append(entry)
        self._active[txn_id].append(entry)

        ok = table.tree.delete(key)
        if ok:
            table.record_count -= 1
        print(f"  [TXN {txn_id}] DELETE  key={key}")

    # - Durability helpers -

    def _save_snapshot(self) -> None:
        """
        Serialise every table's records to JSON.
        Only called on COMMIT -- the snapshot always reflects committed state.
        """
        snap = {}
        for name, table in self.db.tables.items():
            snap[name] = {
                "order":   table.tree.order,
                "records": list(table.tree.get_all()),   # [(key, value), ...]
            }
        with open(self.snapshot_path, "w") as fh:
            json.dump(snap, fh, indent=2)

    def restore_from_snapshot(self) -> None:
        """
        Reload all tables from the JSON snapshot.
        Call this after creating a fresh DatabaseManager to simulate a restart.
        """
        if not os.path.exists(self.snapshot_path):
            print("[Restore] No snapshot found -- starting with empty database.")
            return

        with open(self.snapshot_path) as fh:
            snap = json.load(fh)

        for name, data in snap.items():
            self.db.create_table(name, order=data["order"])
            table = self.db.get_table(name)
            for key, record in data["records"]:
                table.tree.insert(key, record)
                table.record_count += 1

        print(f"[Restore] Reloaded {len(snap)} table(s) from '{self.snapshot_path}'.")

    # - Crash recovery -

    def recover(self) -> None:
        """
        Scan the WAL and undo any transaction that never committed.
        Call once at startup, before accepting new transactions.
        """
        entries   = self.wal.read_all()
        txn_ops   = {}        # txn_id -> [op_dict, ...]
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
        if not incomplete:
            print("[Recovery] WAL clean -- no recovery needed.")
            return

        print(f"[Recovery] Found {len(incomplete)} incomplete transaction(s): "
              f"{sorted(incomplete)}")

        for tid in sorted(incomplete):
            ops = txn_ops[tid]
            print(f"[Recovery] Undoing TXN {tid}  ({len(ops)} op(s))-")
            for op in reversed(ops):
                self._undo_from_dict(op)
            # Record the recovery in the WAL so a second crash doesn't redo it
            self.wal.append(WALEntry(tid, "ROLLBACK"))
            print(f"[Recovery] TXN {tid} undone.")

        print("[Recovery] Recovery complete.")

    # - Internal helpers -

    def _next_id(self) -> int:
        with self._counter_lock:
            self._counter += 1
            return self._counter

    def _require_table(self, table_name: str):
        table = self.db.get_table(table_name)
        if table is None:
            raise ValueError(f"Table '{table_name}' does not exist.")
        return table

    def _undo_op(self, entry: WALEntry) -> None:
        """Undo a single WALEntry (in-memory object)."""
        table = self.db.get_table(entry.table)
        if table is None:
            return
        if entry.op_type == "INSERT":
            if entry.before is None:
                # Key was brand-new -> delete it
                table.tree.delete(entry.key)
                table.record_count = max(0, table.record_count - 1)
            else:
                # Key existed before -> restore old value
                table.tree.update(entry.key, entry.before)
        elif entry.op_type == "UPDATE":
            if entry.before is not None:
                table.tree.update(entry.key, entry.before)
        elif entry.op_type == "DELETE":
            if entry.before is not None:
                table.tree.insert(entry.key, entry.before)
                table.record_count += 1

    def _undo_from_dict(self, op: dict) -> None:
        """Undo a WAL entry that was read back from disk (dict form)."""
        table = self.db.get_table(op["table"])
        if table is None:
            return
        ot = op["op_type"]
        if ot == "INSERT":
            if op["before"] is None:
                table.tree.delete(op["key"])
                table.record_count = max(0, table.record_count - 1)
            else:
                table.tree.update(op["key"], op["before"])
        elif ot == "UPDATE":
            if op["before"] is not None:
                table.tree.update(op["key"], op["before"])
        elif ot == "DELETE":
            if op["before"] is not None:
                table.tree.insert(op["key"], op["before"])
                table.record_count += 1