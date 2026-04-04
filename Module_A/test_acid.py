"""
test_acid.py -- Module A, Assignment 3
ACID Validation for the Custom B+ Tree DBMS Engine

Run from the project root:
    python test_acid.py

Six tests are executed in sequence.  Each prints PASS or FAIL and the
reason.  All state (WAL + snapshot) is cleaned up between test groups so
tests are fully independent.
"""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

from database.db_manager          import DatabaseManager
from database.transaction_manager import TransactionManager
from database                     import recovery as crash_recovery

# - Paths -
WAL_PATH      = "test_wal.log"
SNAPSHOT_PATH = "test_snapshot.json"


# - Helpers -
def clean():
    for p in [WAL_PATH, SNAPSHOT_PATH]:
        if os.path.exists(p):
            os.remove(p)

def sep(title):
    width = 64
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)

RESULTS = []

def record(name, passed, note=""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, status, note))
    tag = "[PASS]" if passed else "[FAIL]"
    print(f"\n  {tag}  RESULT: {status}" + (f"  -- {note}" if note else ""))


# -
# TEST 1 -- Atomicity: full rollback reverts ALL changes
# -
clean()
sep("TEST 1 -- Atomicity: Rollback Reverts All Changes")

db  = DatabaseManager()
db.create_table("employees", order=4)
emp = db.get_table("employees")
txn = TransactionManager(db, WAL_PATH, SNAPSHOT_PATH)

# Baseline: one committed record added directly
emp.insert(1, {"name": "Alice", "salary": 70_000})
count_before = emp.count()
print(f"  Baseline record count : {count_before}")

t1 = txn.begin()
txn.insert(t1, "employees", 2, {"name": "Bob",   "salary": 80_000})
txn.insert(t1, "employees", 3, {"name": "Carol",  "salary": 90_000})
print(f"  Count mid-transaction  : {emp.count()}  (should be {count_before + 2})")

txn.rollback(t1)

ok = (emp.count() == count_before
      and emp.select(2) is None
      and emp.select(3) is None)
record("Atomicity - full rollback", ok,
       f"count after rollback = {emp.count()}, expected {count_before}")


# -
# TEST 2 -- Atomicity: partial failure mid-transaction
# -
sep("TEST 2 -- Atomicity: Partial Failure Mid-Transaction")

t2 = txn.begin()
txn.insert(t2, "employees", 10, {"name": "Dave",  "salary": 60_000})
txn.update(t2, "employees",  1, {"name": "Alice", "salary": 75_000})
print(f"  Alice's salary inside TXN 2  : {emp.select(1)['salary']}")

# Simulate a crash / exception -> rollback
txn.rollback(t2)

alice_salary = emp.select(1)["salary"] if emp.select(1) else None
ok = (emp.select(10) is None and alice_salary == 70_000)
record("Atomicity - partial failure", ok,
       f"key-10={emp.select(10)}, alice_salary={alice_salary}")


# -
# TEST 3 -- Consistency: invalid operation raises error, no side-effects
# -
sep("TEST 3 -- Consistency: Invalid Operation Rejected")

t3 = txn.begin()
caught = False
try:
    txn.insert(t3, "nonexistent_table", 99, {"x": 1})
except ValueError as exc:
    caught = True
    print(f"  Caught expected ValueError: {exc}")
finally:
    txn.rollback(t3)

ok = caught and emp.count() == count_before
record("Consistency - invalid table access",
       ok, f"exception caught={caught}, emp.count={emp.count()}")


# -
# TEST 4 -- Durability: committed data survives a simulated restart
# -
clean()
sep("TEST 4 -- Durability: Committed Data Survives Restart")

db  = DatabaseManager()
db.create_table("employees", order=4)
emp = db.get_table("employees")
txn = TransactionManager(db, WAL_PATH, SNAPSHOT_PATH)

t4 = txn.begin()
txn.insert(t4, "employees", 5,  {"name": "Eve",   "salary": 95_000})
txn.insert(t4, "employees", 6,  {"name": "Frank",  "salary": 85_000})
txn.commit(t4)
committed_count = emp.count()
print(f"  Records committed  : {committed_count}")

# - Simulate restart: fresh in-memory DB loaded from snapshot -
print("  Simulating system restart-")
db2  = DatabaseManager()
txn2 = TransactionManager(db2, WAL_PATH, SNAPSHOT_PATH)
txn2.restore_from_snapshot()
emp2 = db2.get_table("employees")

restored_count = emp2.count() if emp2 else 0
eve   = emp2.select(5)  if emp2 else None
frank = emp2.select(6)  if emp2 else None
print(f"  Restored count     : {restored_count}")
print(f"  Eve  -> {eve}")
print(f"  Frank-> {frank}")

ok = (restored_count == committed_count
      and eve is not None
      and frank is not None)
record("Durability - snapshot restore", ok,
       f"restored={restored_count}, expected={committed_count}")


# -
# TEST 5 -- WAL Crash Recovery: incomplete TXN is undone on restart
# -
clean()
sep("TEST 5 -- WAL Crash Recovery: Incomplete Transaction Undone")

db3 = DatabaseManager()
db3.create_table("orders", order=4)
orders = db3.get_table("orders")

# Commit one record first so snapshot has a clean baseline
txn3 = TransactionManager(db3, WAL_PATH, SNAPSHOT_PATH)
t_pre = txn3.begin()
txn3.insert(t_pre, "orders", 100, {"item": "Widget", "qty": 10})
txn3.commit(t_pre)

# Now simulate a crash: WAL records BEGIN + ops but no COMMIT
t5 = txn3.begin()
txn3.insert(t5, "orders", 200, {"item": "Gadget",    "qty": 5})
txn3.insert(t5, "orders", 300, {"item": "Doohickey", "qty": 3})
# # process killed here, no commit

print(f"  Count BEFORE recovery: {orders.count()}  (includes uncommitted rows)")

# Run recovery on the current in-memory DB (simulates restart + WAL replay)
crash_recovery.recover(WAL_PATH, db3)

count_after = orders.count()
print(f"  Count AFTER  recovery: {count_after}")

ok = (orders.select(200) is None
      and orders.select(300) is None
      and orders.select(100) is not None
      and count_after == 1)
record("Durability - WAL crash recovery", ok,
       f"key-200={orders.select(200)}, key-300={orders.select(300)}, "
       f"key-100={orders.select(100)}")


# -
# TEST 6 -- Isolation: rolled-back TXN does not affect a committed TXN
# -
clean()
sep("TEST 6 -- Isolation: Rolled-back TXN Does Not Affect Committed TXN")

db4 = DatabaseManager()
db4.create_table("accounts", order=4)
accs = db4.get_table("accounts")
txn4 = TransactionManager(db4, WAL_PATH, SNAPSHOT_PATH)

# TXN A: inserts Alice
tA = txn4.begin()
txn4.insert(tA, "accounts", 1, {"holder": "Alice", "balance": 1_000})

# TXN B (concurrent): inserts Bob then rolls back
tB = txn4.begin()
txn4.insert(tB, "accounts", 2, {"holder": "Bob", "balance": 2_000})
txn4.rollback(tB)   # B aborts -> should not affect A

# TXN A commits after B rolled back
txn4.commit(tA)

alice = accs.select(1)
bob   = accs.select(2)
print(f"  Alice -> {alice}")
print(f"  Bob   -> {bob}  (should be None)")

ok = alice is not None and bob is None
record("Isolation - rolled-back TXN", ok,
       f"alice={alice}, bob={bob}")


# -
# SUMMARY
# -
sep("SUMMARY")
all_pass = True
for name, status, note in RESULTS:
    tag = "[PASS]" if status == "PASS" else "[FAIL]"
    print(f"  {tag}  {name:<44} {status}")
    if status == "FAIL":
        all_pass = False

print()
if all_pass:
    print("  All 6 ACID tests PASSED.")
else:
    print("  One or more tests FAILED -- see details above.")

# Clean up temp files
clean()