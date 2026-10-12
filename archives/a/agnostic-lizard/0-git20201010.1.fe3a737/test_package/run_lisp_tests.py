"""Installed-library ASDF regressions and a separate HMDFS functional case.

ASDF's supported load-source-op is appropriate for this source-only library.
No upstream source/assertion is changed, no ASDF function is stubbed, and each
official regression entry runs in a fresh real ECL process. The two entry files
are the denominator, not the 27 integrity assets or a guessed assertion count.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess


def lisp_string(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'runtime', 'work', 'libraries'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    source = Path(args.source).resolve()
    runtime = Path(args.runtime).resolve()
    work = Path(args.work).resolve()
    assert platform.system() == 'HarmonyOS' and platform.machine() == 'aarch64'
    assert not work.exists(), 'Evidence root must be create-new'
    work.mkdir(parents=True)
    private = work / 'ecl'
    # Never sign or alter a published provider's cache in place.
    shutil.copytree(runtime, private, symlinks=False)
    signer = shutil.which('binary-sign-tool')
    assert signer
    executable = private / 'bin/ecl'
    for path in [executable, *sorted((private / 'lib/ecl-24.5.10').glob('*.fas'))]:
        signed = path.with_name(path.name + '.task-signed')
        subprocess.run([signer, 'sign', '-inFile', str(path), '-outFile',
                        str(signed), '-selfSign', '1'], check=True, timeout=60)
        os.chmod(signed, 0o755)
        os.replace(signed, path)
    env = os.environ.copy()
    env['ECLDIR'] = str(private / 'lib/ecl-24.5.10') + '/'
    env['LD_LIBRARY_PATH'] = ':'.join([str(private / 'lib'),
                                      *json.loads(args.libraries),
                                      env.get('LD_LIBRARY_PATH', '')])
    (work / 'tmp').mkdir()
    for key in ('TMPDIR', 'TMP', 'TEMP'):
        env[key] = str(work / 'tmp')
    common = ('(require :asdf)\n'
              '(setf asdf:*load-system-operation* \'asdf:load-source-op)\n'
              '(asdf:load-asd ' + lisp_string(source / 'agnostic-lizard.asd') + ')\n'
              '(asdf:load-system :agnostic-lizard)\n')

    def run(label, body, expected):
        script = work / (label + '.lisp')
        script.write_text(common + '(handler-case (progn\n' + body + '\n'
                          '(ext:quit 0)) (error (e) (format *error-output*'
                          ' "TEST-ERROR ~A~%" e) (ext:quit 1)))\n', encoding='utf-8')
        command = [str(executable), '-norc', '-shell', str(script)]
        with (work / (label + '.stdout')).open('xb') as out, \
             (work / (label + '.stderr')).open('xb') as err:
            rc = subprocess.run(command, cwd=work, env=env, stdout=out,
                                stderr=err, timeout=300).returncode
        text = (work / (label + '.stdout')).read_text(errors='replace') + \
               (work / (label + '.stderr')).read_text(errors='replace')
        assert rc == 0 and expected in text, f'{label}: rc={rc}; {text[-3000:]}'
        print('AGNOSTIC_CASE=' + json.dumps({'case': label, 'rc': rc,
              'command': command, 'stdout_sha256': hashlib.sha256(
              (work / (label + '.stdout')).read_bytes()).hexdigest(),
              'stderr_sha256': hashlib.sha256(
              (work / (label + '.stderr')).read_bytes()).hexdigest()}), flush=True)

    # The official unmatched throws and assertions propagate as errors and RC1.
    for name in ('examples.lisp', 'walking-examples.lisp'):
        run(name[:-5], '(load ' + lisp_string(source / name) + ')',
            'Example run complete.')
    print('UPSTREAM_TEST_PASS=2/2', flush=True)
    run('consumer', '(assert (= (eval (agnostic-lizard:macroexpand-all '
        "'(macrolet ((twice (x) `(+ ,x ,x))) (twice 21)))) 42))\n"
        '(format t "CONSUMER_OK~%")', 'CONSUMER_OK')
    print('CONSUMER_TEST_PASS=1/1', flush=True)

    # HMDFS real file reads/writes through Lisp, Unicode + spaces and projected
    # file ownership checked against the directory, never against process UID.
    hmdfs = work / '鸿蒙 文件交换'
    hmdfs.mkdir()
    before = set(hmdfs.iterdir())
    input_path = hmdfs / '输入 表达式.lisp'
    output_path = hmdfs / '结果 42.txt'
    payload = '(macrolet ((twice (x) `(+ ,x ,x))) (twice 21))\n'.encode()
    with input_path.open('xb') as stream:
        stream.write(payload)
    run('harmony', '(with-open-file (i ' + lisp_string(input_path) +
        ' :direction :input) (let ((v (eval (agnostic-lizard:macroexpand-all'
        ' (read i))))) (assert (= v 42)) (with-open-file (o ' +
        lisp_string(output_path) + ' :direction :output :if-exists :error'
        ' :if-does-not-exist :create) (format o "~D" v))))\n'
        '(format t "HARMONY_FILE_OK~%")', 'HARMONY_FILE_OK')
    assert input_path.read_bytes() == payload and output_path.read_bytes() == b'42'
    assert input_path.stat().st_uid == output_path.stat().st_uid == hmdfs.stat().st_uid
    detail = {'platform': platform.system(), 'machine': platform.machine(),
              'uid': os.getuid(), 'projected_file_uid': input_path.stat().st_uid,
              'parent_uid': hmdfs.stat().st_uid,
              'input_sha256': hashlib.sha256(payload).hexdigest(),
              'output_sha256': hashlib.sha256(b'42').hexdigest()}
    input_path.unlink()
    output_path.unlink()
    assert set(hmdfs.iterdir()) == before
    hmdfs.rmdir()
    print('AGNOSTIC_HARMONY_DETAIL=' + json.dumps(detail), flush=True)
    print('HARMONY_TEST_PASS=1/1', flush=True)


if __name__ == '__main__':
    main()
