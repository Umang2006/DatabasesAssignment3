# Module B Test Harness

This repository now includes runnable helper scripts at the project root:

- `seed_test_data.py`
- `test_concurrent.py`
- `test_failure_and_rollback.py`
- `locustfile.py`
- `generate_report.py`

They work together through a generated file named `.test_seed.json`.

## Prerequisites

1. Start the Flask app from the project root:

```powershell
python app/main.py
```

2. Make sure your admin credentials are correct.

Defaults used by the scripts:

- username: `admin`
- password: `password123`

If yours are different, set environment variables before running:

```powershell
$env:DMS_ADMIN_USER="admin"
$env:DMS_ADMIN_PASS="your-real-password"
```

## Step 1: Seed test users and slots

```powershell
python seed_test_data.py
```

This will:

- log in as admin
- create `patient1`, `patient2`, and `doctor1` if needed
- insert doctor slots directly into MySQL if missing
- write `.test_seed.json`

## Step 2: Run concurrent and stress tests

```powershell
python test_concurrent.py
```

This produces:

- console results
- `test_results.json`

## Step 3: Run failure and rollback checks

```powershell
python test_failure_and_rollback.py
```

## Step 4: Generate markdown report

```powershell
python generate_report.py test_results.json
```

Output:

- `module_b_report.md`

## Step 5: Run Locust

If `locust.exe` is not on your PATH, use:

```powershell
python -m locust -f locustfile.py --host=http://localhost:5000
```

Then open:

- `http://localhost:8089`

Suggested values:

- Users: `50`
- Spawn rate: `5`

Headless example:

```powershell
python -m locust -f locustfile.py --host=http://localhost:5000 --headless -u 50 -r 5 --run-time 60s --html locust_report.html --csv locust_results
```

## Common fixes

- `401 Unauthorized` on seed/test scripts:
  - your admin password in the script config did not match the real one
  - set `DMS_ADMIN_PASS`

- `doctor_id` / `slot_id` issues:
  - rerun `python seed_test_data.py`
  - it rewrites `.test_seed.json`

- `locust` not found:
  - use `python -m locust ...`

- stale test data:
  - delete `.test_seed.json`
  - rerun the seeder
