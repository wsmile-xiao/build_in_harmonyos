"""Exercise installed commands using a new MMIX program."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--package', required=True)
    p.add_argument('--runner', default='')
    p.add_argument('--out', required=True)
    a = p.parse_args()
    package = Path(a.package).resolve()
    results, commands = [], []
    with tempfile.TemporaryDirectory(prefix='mmix-consumer-') as tmp:
        work = Path(tmp)
        (work / 'consumer.mms').write_text('''        LOC #100
Main    SETL $0,19
        SETL $1,23
        ADDU $255,$0,$1
        TRAP 0,Halt,0
''')
        (work / 'bad.mms').write_text('Main    INVALID_OPCODE $0,0\n')

        def run(tool, args, data=None):
            argv = shlex.split(a.runner) + [str(package / 'bin' / tool)] + args
            r = subprocess.run(argv, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=work, timeout=180, env=dict(os.environ, TZ='UTC', LC_ALL='C'))
            commands.append({'command': argv, 'stdin': data.decode() if data else None,
                             'exit_code': r.returncode, 'stdout': r.stdout.decode(errors='replace'),
                             'stderr': r.stderr.decode(errors='replace')})
            return r

        def check(name, value):
            results.append({'name': name, 'passed': bool(value)})

        r = run('mmixal', ['-l', 'consumer.lst', 'consumer.mms'])
        check('assemble-consumer', r.returncode == 0)
        check('object-created', (work / 'consumer.mmo').is_file())
        check('listing-created', (work / 'consumer.lst').is_file())
        r = run('mmix', ['consumer'])
        check('19-plus-23-exit-status', r.returncode == 42)
        check('consumer-no-unexpected-output', r.stdout == b'' and r.stderr == b'')
        r = run('mmotype', ['consumer.mmo'])
        check('inspect-real-object', r.returncode == 0 and b'Main' in r.stdout)
        check('inspect-consumer-instructions', b'e3000013' in r.stdout.lower() and b'e3010017' in r.stdout.lower())
        r = run('mmix', ['-Dconsumer.mmb', 'consumer'])
        check('create-pipeline-dump', r.returncode == 0 and (work / 'consumer.mmb').is_file())
        config = package / 'share' / 'mmix' / 'examples' / 'plain.mmconfig'
        r = run('mmmix', [str(config), 'consumer.mmb'], b'10000\nq\n')
        check('pipeline-halts', r.returncode == 0 and b'Halted at time' in r.stdout)
        check('pipeline-statistics', b'Instructions issued per cycle:' in r.stdout)
        r = run('mmixal', ['bad.mms'])
        check('invalid-opcode-rejected', r.returncode != 0 and b'unknown operation code' in r.stderr.lower())
        r = run('mmotype', ['consumer.mms'])
        check('non-object-rejected', r.returncode != 0 and b'not an MMO file' in r.stderr)
    report = {'environment': 'QEMU AArch64 on Linux; not HarmonyOS device' if a.runner else 'native consumer',
              'passed': sum(c['passed'] for c in results), 'total': len(results), 'checks': results,
              'commands': commands, 'binary_sha256': {n: hashlib.sha256((package / 'bin' / n).read_bytes()).hexdigest()
                                                     for n in ('mmixal', 'mmix', 'mmotype', 'mmmix')}}
    Path(a.out).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Installed MMIX consumer checks: %d/%d' % (report['passed'], report['total']))
    for c in results:
        if not c['passed']:
            print('FAIL:', c['name'])
    return 0 if report['passed'] == report['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
