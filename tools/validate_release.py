from pathlib import Path
import json, re, subprocess, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/'payload'/'dbe-mod.js'
LAUNCHER=ROOT/'launcher.py'
errors=[]
def check(ok,msg):
    if not ok: errors.append(msg)
js=JS.read_text(encoding='utf-8')
launcher=LAUNCHER.read_text(encoding='utf-8')
check('const VERSION="V19";' in js,'VERSION is not V19')
check('const PROFILE_COUNT=3000;' in js,'PROFILE_COUNT != 3000')
check('const VARIANT_COUNT=16;' in js,'VARIANT_COUNT != 16')
m=re.search(r'const PITCH_IDENTITIES=(\[.*?\]);\n\nfunction profileFor',js,re.S)
check(bool(m),'pitch catalog missing')
if m:
    pitches=json.loads(m.group(1))
    check(len(pitches)==3000,f'pitch count {len(pitches)} != 3000')
    check(len({p.get("name") for p in pitches})==3000,'pitch names are not unique')
check('debugIssueText' in js,'debug issue reporter missing')
check('F9' in js,'F9 debug overlay missing')
check('dbe-build-report.json' in launcher,'launcher build report missing')
for f in ['README.md','DEBUGGING.md','ROADMAP.md','docs/index.html','docs/pitches.html','.github/workflows/validate.yml']:
    check((ROOT/f).is_file(),f'missing {f}')
try: compile(launcher,str(LAUNCHER),'exec')
except Exception as e: errors.append(f'launcher syntax: {e}')
node=shutil.which('node')
if node:
    r=subprocess.run([node,'--check',str(JS)],capture_output=True,text=True)
    if r.returncode: errors.append('JavaScript syntax: '+r.stderr)
if errors:
    print('RELEASE VALIDATION FAILED')
    for e in errors: print(' -',e)
    sys.exit(1)
print('DBE V19 release validation PASS')
print(' - 3,000 unique named pitches')
print(' - 16 variants / 48,000 exact challenges')
print(' - launcher syntax')
print(' - JavaScript syntax' if node else ' - JavaScript syntax skipped (node unavailable)')
print(' - debug/release/GitHub files present')
