"""Run unchanged upstream C suite and bind all registrations to Check XML."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    source = a.source / 'c/tests/test_child.c'
    text = source.read_text(encoding='utf-8')
    declarations = re.findall(r'\bSTART_TEST\s*\(\s*(\w+)\s*\)', text)
    registrations = re.findall(r'\btcase_add_test\s*\(\s*tc_core\s*,\s*(\w+)\s*\)', text)
    if not declarations or len(set(registrations)) != len(registrations) or set(declarations) != set(registrations):
        raise RuntimeError('UPSTREAM_REGISTRATION_INVENTORY_MISMATCH')
    a.output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    for key in list(env):
        if key.startswith('CK_'):
            del env[key]
    tmp = a.output / 'tmp'
    tmp.mkdir()
    # Check 0.15.2 selects TEMP before P_tmpdir, which precedes TMPDIR.
    # Bind all three to this harness's private directory; no system fallback.
    env.update(TEMP=str(tmp.resolve()), TMPDIR=str(tmp.resolve()), TMPPREFIX=str(tmp.resolve()),
               CK_XML_LOG_FILE_NAME=str((a.output / 'check.xml').resolve()))
    # Keep upstream fork/timeout behavior; never filter cases or disable fork.
    r = subprocess.run([str(a.binary.resolve())], cwd=a.output, env=env,
                       capture_output=True, timeout=90)
    (a.output / 'stdout').write_bytes(r.stdout)
    (a.output / 'stderr').write_bytes(r.stderr)
    if not (a.output / 'check.xml').is_file():
        print(r.stdout.decode('utf-8', errors='replace'), end='')
        print(r.stderr.decode('utf-8', errors='replace'), end='', file=__import__('sys').stderr)
        raise RuntimeError(f'UPSTREAM_XML_MISSING: harness_rc={r.returncode}')
    xml = ET.parse(a.output / 'check.xml').getroot()
    tests = [node for node in xml.iter() if node.tag.split('}')[-1] == 'test']
    observed = []
    for node in tests:
        identity = next(child.text for child in node if child.tag.split('}')[-1] == 'id')
        observed.append(identity)
    total = len(registrations)
    summary = f'100%: Checks: {total}, Failures: 0, Errors: 0'
    passed = (r.returncode == 0 and len(observed) == total and
              set(observed) == set(registrations) and len(set(observed)) == total and
              all(node.get('result') == 'success' for node in tests) and
              summary in r.stdout.decode('utf-8').splitlines())
    result = {'total': total, 'passed': total if passed else 0,
              'failed': 0 if passed else total, 'skipped': 0, 'harness_count': 1,
              'rc': r.returncode, 'registered': registrations, 'observed': observed,
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'binary_sha256': hashlib.sha256(a.binary.read_bytes()).hexdigest(),
              'xml_sha256': hashlib.sha256((a.output / 'check.xml').read_bytes()).hexdigest()}
    (a.output / 'result.json').write_text(json.dumps(result, sort_keys=True)+'\n', encoding='utf-8')
    (a.output / 'inventory.txt').write_text('INVENTORY_COUNT='+str(total)+'\n'+'\n'.join(registrations)+'\n', encoding='utf-8')
    print(r.stdout.decode('utf-8'), end='')
    if not passed:
        raise RuntimeError('UPSTREAM_FRAMEWORK_FULL_EXECUTION_FAILED')
    print(f'UPSTREAM_TEST_PASS={total}/{total}')


if __name__ == '__main__':
    main()
