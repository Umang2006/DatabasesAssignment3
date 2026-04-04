"""
wal.py — Write-Ahead Log
Every mutating operation is written here BEFORE it touches the B+ Tree.
This guarantees that a crash at any point leaves enough information to
either re-apply (redo) or undo the interrupted transaction.

Log format: one JSON object per line (JSON Lines).
{
  "txn_id"   : int,
  "op_type"  : "BEGIN" | "INSERT" | "UPDATE" | "DELETE" | "COMMIT" | "ROLLBACK",
  "table"    : str | null,
  "key"      : any | null,
  "before"   : value-before-change | null,   # used for UNDO
  "after"    : value-after-change  | null,   # used for REDO
  "timestamp": float
}
"""

import json
import os
import threading
import time


class WALEntry:
    """Represents one record in the Write-Ahead Log."""

    def __init__(self, txn_id, op_type,
                 table=None, key=None,
                 before=None, after=None):
        self.txn_id    = txn_id
        self.op_type   = op_type   # BEGIN | INSERT | UPDATE | DELETE | COMMIT | ROLLBACK
        self.table     = table
        self.key       = key
        self.before    = before    # value that existed before this op  (undo image)
        self.after     = after     # value that will exist after this op (redo image)
        self.timestamp = time.time()

    def to_dict(self):
        return {
            "txn_id":    self.txn_id,
            "op_type":   self.op_type,
            "table":     self.table,
            "key":       self.key,
            "before":    self.before,
            "after":     self.after,
            "timestamp": self.timestamp,
        }


class WriteAheadLog:
    """
    Append-only log file.
    Thread-safe: a single lock serialises all appends.
    """

    def __init__(self, path="wal.log"):
        self.path  = path
        self._lock = threading.Lock()

    # ── Public API ──────────────────────────────────────────────────────────

    def append(self, entry: WALEntry) -> None:
        """Flush one entry to disk before returning."""
        with self._lock:
            with open(self.path, "a") as fh:
                fh.write(json.dumps(entry.to_dict()) + "\n")
                fh.flush()
                os.fsync(fh.fileno())   # force OS buffer → disk

    def read_all(self) -> list:
        """Return every entry as a list of dicts (oldest first)."""
        if not os.path.exists(self.path):
            return []
        entries = []
        with open(self.path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass  # tolerate a torn last line from a crash
        return entries

    def clear(self) -> None:
        """Delete the log file (called after a clean checkpoint)."""
        if os.path.exists(self.path):
            os.remove(self.path)
