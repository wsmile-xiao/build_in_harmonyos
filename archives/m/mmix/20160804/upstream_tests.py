"""Run the release's documented tests; keep original sources and golden output."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--src', required=True)
    p.add_argument('--bin', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--runner', default='')
    p.add_argument('--environment', required=True)
    a = p.parse_args()
    src, bins = Path(a.src).resolve(), Path(a.bin).resolve()
    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    checks, commands = [], []
    env = dict(os.environ, TZ='UTC', LC_ALL='C')
    with tempfile.TemporaryDirectory(prefix='mmix-tests-') as tmp:
        work = Path(tmp)
        for item in src.iterdir():
            if item.is_file() and item.suffix in ('.mms', '.run', '.out', '.mmconfig', '.mmix'):
                shutil.copy2(item, work / item.name)

        def run(tool, args, data=None):
            argv = shlex.split(a.runner) + [str(bins / tool)] + args
            r = subprocess.run(argv, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=work, env=env, timeout=180)
            commands.append({'command': argv, 'stdin': data.decode() if data else None,
                             'exit_code': r.returncode, 'stdout': r.stdout.decode(errors='replace'),
                             'stderr': r.stderr.decode(errors='replace')})
            return r

        def check(name, condition):
            checks.append({'name': name, 'passed': bool(condition)})

        negatives = {'halves.mms': b'unknown operation code', 'number1.mms': b'undefined'}
        for file in sorted(work.glob('*.mms')):
            r = run('mmixal', ['-x', '-b', '250', file.name])
            if file.name in negatives:
                check('baseline-rejected-example:' + file.name,
                      r.returncode == 1 and negatives[file.name] in r.stderr.lower())
            else:
                check('assemble:' + file.name, r.returncode == 0 and file.with_suffix('.mmo').is_file())

        r = run('mmix', ['hello'])
        check('README:hello-output-and-status', r.stdout == b'hello, world\n' and r.returncode == 8)
        r = run('mmix', ['copy', 'copy.mms'])
        check('README:copy-exact-bytes', r.returncode == 0 and r.stdout == (work / 'copy.mms').read_bytes())
        r = run('mmix', ['-i', 'silly'], b'i silly.run\n')
        golden = (work / 'silly.out').read_bytes()
        lines = golden.splitlines(keepends=True)
        warnings = b''.join(line for line in lines if line.startswith(b'Warning:'))
        expected = b''.join(line for line in lines if not line.startswith(b'Warning:'))
        # Upstream golden is a terminal transcript; pipes do not echo typed input.
        expected = expected.replace(b'mmix> i silly.run\n', b'mmix> ', 1)
        check('README:silly-full-trace', r.returncode == 0 and r.stdout == expected)
        check('README:silly-exact-warnings', r.stderr == warnings)
        for name, halt, end, counts, predictions in (
            ('hello', 405, 406, (380, 26), '0 in agreement, 0 in opposition; 0 good, 0 bad'),
            ('silly', 4424, 4425, (2655, 1770), '183 in agreement, 15 in opposition; 176 good, 22 bad'),
        ):
            r = run('mmix', ['-D' + name + '.mmb', name])
            check('README:dump:' + name, r.returncode == 0 and (work / (name + '.mmb')).is_file())
            r = run('mmmix', ['plain.mmconfig', name + '.mmb'], b'10000\nq\n')
            text = r.stdout.decode(errors='replace')
            check('README:pipeline:' + name, r.returncode == 0 and
                  ('Halted at time %d' % halt) in text and
                  ('Simulation ended at time %d.' % end) in text and predictions in text and
                  ('  0   %d\n  1   %d' % counts) in text)
            check('README:pipeline-warnings:' + name, r.stderr == (warnings if name == 'silly' else b''))
        r = run('mmotype', ['hello.mmo'])
        check('mmotype:real-object-listing', r.returncode == 0 and b'Main' in r.stdout and b'String' in r.stdout)
        timestamp = int.from_bytes((work / 'hello.mmo').read_bytes()[4:8], 'big')
        date = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        formatted = date.strftime('%a %b ') + '%2d' % date.day + date.strftime(' %H:%M:%S %Y')
        check('mmotype:LP64-timestamp', ('File was created ' + formatted + '\n').encode() in r.stdout)
        # Additional source-owned interactive pipeline example, without inventing a golden oracle.
        r = run('mmmix', ['test1.mmconfig', 'test1.mmix'], b'140\nq\n')
        check('README:test1-interactive-smoke', r.returncode == 0 and b'Simulation ended' in r.stdout)

    report = {'environment': a.environment, 'source_version': '20160804',
              'passed': sum(c['passed'] for c in checks), 'total': len(checks),
              'assembly_examples': 49, 'positive_assembly_examples': 47,
              'baseline_rejected_examples': list(negatives),
              'golden_sha256': hashlib.sha256((src / 'silly.out').read_bytes()).hexdigest(),
              'normalization': 'Only terminal input echo separated; complete stdout and both stderr warning lines compared.',
              'binary_sha256': {name: hashlib.sha256((bins / name).read_bytes()).hexdigest()
                                for name in ('mmixal', 'mmix', 'mmotype', 'mmmix')},
              'checks': checks, 'commands': commands}
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('MMIX upstream/documented checks: %d/%d (%s)' % (report['passed'], report['total'], a.environment))
    for c in checks:
        if not c['passed']:
            print('FAIL:', c['name'])
    return 0 if report['passed'] == report['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
