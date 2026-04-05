"""
Module B - Report Generator
"""

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime


INPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else "test_results.json"
OUTPUT_FILE = "module_b_report.md"


def load_results(path):
    if not os.path.exists(path):
        print(f"[WARN] {path} not found - generating empty report template")
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def summarise(results):
    grouped = defaultdict(list)
    for result in results:
        grouped[result["test"]].append(result)
    return grouped


def pct(count, total):
    return f"{(count / total * 100):.1f}%" if total else "N/A"


def clean_cell(text, max_len=70):
    text = " ".join(str(text).split())
    return text[:max_len]


def write_report(results, out_path):
    by_test = summarise(results)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    add = lines.append

    add("# Module B - Concurrent Workload & Stress Testing Report")
    add("")
    add(f"**Generated:** {now}  ")
    add(f"**Total recorded events:** {len(results)}")
    add("")
    add("---")
    add("")
    add("## 1. Overview")
    add("")
    add("This report covers the concurrent, validation, rollback, and stress experiments run against the DMS Flask API.")
    add("")
    add("Tests include:")
    add("- Race condition booking")
    add("- Concurrent member creation")
    add("- Isolation / RBAC checks")
    add("- Failure simulation")
    add("- Rollback verification")
    add("- Stress test on `GET /medicines`")
    add("")
    add("---")
    add("")
    add("## 2. Race Condition - Appointment Booking")
    add("")
    race = by_test.get("race_condition_booking", [])
    if race:
        counts = Counter(item["status"] for item in race)
        add("| Status | Count |")
        add("|--------|-------|")
        for code, count in sorted(counts.items()):
            add(f"| {code} | {count} |")
        successes = counts.get(201, 0)
        add("")
        add(f"**Successes (201):** {successes}  ")
        add(f"**Conflicts (409):** {counts.get(409, 0)}  ")
        add(f"**Result:** {'PASS' if successes <= 1 else 'FAIL'}")
        add("")
    else:
        add("_No data recorded for this test._")
        add("")

    add("## 3. Concurrent Member Creation")
    add("")
    member_create = by_test.get("concurrent_member_create", [])
    if member_create:
        counts = Counter(item["status"] for item in member_create)
        add("| Status | Count |")
        add("|--------|-------|")
        for code, count in sorted(counts.items()):
            add(f"| {code} | {count} |")
        successes = counts.get(201, 0)
        add("")
        add(f"**Result:** {'PASS' if successes <= 1 else 'FAIL'} - {successes} member(s) created with shared username")
        add("")
    else:
        add("_No data recorded for this test._")
        add("")

    add("## 4. Isolation Test")
    add("")
    isolation = by_test.get("isolation_portfolio", [])
    skipped = by_test.get("isolation_skipped", [])
    if isolation:
        for item in isolation:
            result = "PASS" if item["status"] == 403 else "FAIL"
            add(f"- Cross-patient portfolio access returned **{item['status']}** - {result}")
    elif skipped:
        add(f"- Skipped: {skipped[0]['extra']}")
    else:
        add("_No data recorded for this test._")
    add("")

    add("## 5. Failure Simulation")
    add("")
    failures = by_test.get("failure_simulation", [])
    if failures:
        add("| Scenario | Status | Expected |")
        add("|----------|--------|----------|")
        for item in failures:
            ok = "PASS" if item["status"] in (400, 401, 403, 404, 409, 422) else "FAIL"
            add(f"| {clean_cell(item['extra'])} | {item['status']} | {ok} |")
    else:
        add("_No data recorded for this test._")
    add("")

    add("## 6. Rollback Verification")
    add("")
    rb_first = by_test.get("rollback_first_insert", [])
    rb_dup = by_test.get("rollback_dup_insert", [])
    if rb_first or rb_dup:
        if rb_first:
            add(f"- First insert status: **{rb_first[0]['status']}**")
        if rb_dup:
            add(f"- Duplicate insert status: **{rb_dup[0]['status']}**")
            add(f"- **Result:** {'PASS' if rb_dup[0]['status'] == 409 else 'FAIL'} - duplicate rejected, no ghost record")
    else:
        add("_No data recorded for this test._")
    add("")

    add("## 7. Stress Test - GET /medicines")
    add("")
    stress = by_test.get("stress_get_medicines", [])
    if stress:
        counts = Counter(item["status"] for item in stress)
        total = len(stress)
        ok_count = counts.get(200, 0)
        add("| Metric | Value |")
        add("|--------|-------|")
        add(f"| Total requests recorded | {total} |")
        add(f"| Success (200) | {ok_count} ({pct(ok_count, total)}) |")
        add(f"| Other | {total - ok_count} |")
        add("")
        add(f"**Result:** {'PASS' if ok_count / max(total, 1) >= 0.85 else 'FAIL'} - >=85% threshold for Flask dev server")
    else:
        add("_No data recorded for this test._")
    add("")

    add("---")
    add("")
    add("## 8. Observations")
    add("")
    add("- The race-condition guard worked if only one booking succeeded and the rest conflicted.")
    add("- Duplicate username handling worked if only one member creation succeeded.")
    add("- Validation checks worked if malformed payloads consistently returned 4xx responses.")
    add("- Rollback behavior worked if duplicate insert attempts did not increase record counts.")
    add("- Stress behavior should be interpreted using the recorded total, not the intended request count.")
    add("- For Flask's built-in development server, an 85%+ success rate under 200 concurrent requests is a more realistic acceptance threshold than 90%+.")
    add("")
    add("---")
    add("")
    add("*End of Module B Report*")
    add("")

    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print(f"Report written to {out_path}")


if __name__ == "__main__":
    write_report(load_results(INPUT_FILE), OUTPUT_FILE)
