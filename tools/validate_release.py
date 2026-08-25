from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def check(ok, message):
    if not ok:
        errors.append(message)

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

def sha256(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

required = [
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICE.md",
    "DEBUGGING.md",
    "SUPPORT.md",
    "ROADMAP.md",
    "CHANGELOG.md",
    "launcher.py",
    "payload/dbe-mod.js",
    "data/pitches.json",
    "data/variants.json",
    "docs/index.html",
    "docs/pitches.html",
    "docs/data/pitches.json",
    ".github/workflows/validate.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
]

for path in required:
    check((ROOT / path).is_file(), f"missing {path}")

version_file = ROOT / "VERSION"
if version_file.is_file():
    version = version_file.read_text(encoding="utf-8").strip()
    check(version == "V19", f"VERSION is {version!r}, expected 'V19'")

# Data catalog
try:
    pitches = json.loads(read("data/pitches.json"))
    check(isinstance(pitches, list), "data/pitches.json is not a list")
    if isinstance(pitches, list):
        check(len(pitches) == 3000, f"pitch count {len(pitches)} != 3000")
        names = [p.get("name") for p in pitches]
        ids = [p.get("id") for p in pitches]
        check(len(set(names)) == 3000, "pitch names are not unique")
        check(len(set(ids)) == 3000, "pitch IDs are not unique")
except Exception as e:
    errors.append(f"pitch catalog: {e}")

try:
    variants = json.loads(read("data/variants.json"))
    check(isinstance(variants, list), "data/variants.json is not a list")
    if isinstance(variants, list):
        check(len(variants) == 16, f"variant count {len(variants)} != 16")
        check(len({v.get('name') for v in variants}) == 16, "variant names are not unique")
except Exception as e:
    errors.append(f"variant catalog: {e}")

if (ROOT / "data/pitches.json").is_file() and (ROOT / "docs/data/pitches.json").is_file():
    check(
        sha256("data/pitches.json") == sha256("docs/data/pitches.json"),
        "docs pitch catalog is out of sync with data/pitches.json",
    )

# Runtime anchors
if (ROOT / "payload/dbe-mod.js").is_file():
    js = read("payload/dbe-mod.js")
    check('const VERSION="V19";' in js, "runtime VERSION anchor is not V19")
    check("const PROFILE_COUNT=3000;" in js, "runtime PROFILE_COUNT != 3000")
    check("const VARIANT_COUNT=16;" in js, "runtime VARIANT_COUNT != 16")
    check("debugIssueText" in js, "debug issue reporter missing")
    check("F9" in js, "F9 debug support missing")

    node = shutil.which("node")
    if node:
        result = subprocess.run(
            [node, "--check", str(ROOT / "payload/dbe-mod.js")],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            errors.append("JavaScript syntax: " + result.stderr.strip())

# Launcher syntax / diagnostics anchors
if (ROOT / "launcher.py").is_file():
    launcher = read("launcher.py")
    check("dbe-build-report.json" in launcher, "launcher build report support missing")
    try:
        compile(launcher, str(ROOT / "launcher.py"), "exec")
    except Exception as e:
        errors.append(f"launcher syntax: {e}")

# Public-page sanity
for path in ["docs/index.html", "docs/pitches.html"]:
    if (ROOT / path).is_file():
        html = read(path).lower()
        check("<!doctype html" in html, f"{path} missing doctype")
        check("<title>" in html, f"{path} missing title")

# Legal file should remain a recognizable MIT license.
if (ROOT / "LICENSE").is_file():
    check(read("LICENSE").startswith("MIT License"), "LICENSE is not standard MIT text")

if errors:
    print("DBE REPOSITORY VALIDATION FAILED")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("DBE repository validation PASS")
print(" - required public files present")
print(" - 3,000 unique pitch identities")
print(" - 16 unique variants / 48,000 combinations")
print(" - docs pitch data matches runtime data")
print(" - launcher and JavaScript syntax")
print(" - debug/release/legal files present")
