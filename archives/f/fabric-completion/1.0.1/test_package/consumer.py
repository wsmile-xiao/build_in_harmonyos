"""Functional consumer; deterministic external fab command, real product/loader."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

SCRIPT = r'''
set -e -o pipefail
stage=initialization
trap 'rc=$?; printf "FAIL stage=%s line=%s rc=%s\n" "$stage" "$LINENO" "$rc" >&2' ERR
root=$(cd "$1" && pwd)
export BASH_COMPLETION_USER_DIR="$root/user"
export BASH_COMPLETION_COMPAT_DIR="$root/empty-compat"
export BASH_COMPLETION_USER_FILE=/dev/null
export XDG_DATA_DIRS="$root/empty-data"
export PATH="$root/bin:$PATH"
stage=loader_source
source "$2" || { printf 'FAIL loader_source\n' >&2; exit 1; }
stage=dynamic_load
# The real interactive completion loader is invoked conditionally, so its
# internal probe failures do not acquire artificial errexit semantics.
_comp_load -- fab || { printf 'FAIL dynamic_load\n' >&2; exit 1; }
stage=registration
complete -p fab | grep -F -- '-F __fab_completion' >/dev/null
cd "$root/补全 空间"
touch fabfile.py
COMP_WORDS=(fab dep); COMP_CWORD=1
stage=cached_task_completion
__fab_completion
[[ ${#COMPREPLY[@]} -eq 1 && ${COMPREPLY[0]} == deploy ]]
[[ -s .fab_tasks~ ]]
printf 'PASS cached_task_completion\n'
printf 'changed\n' > "$root/tasks.txt"
stage=cache_reuse
COMP_WORDS=(fab dep); COMP_CWORD=1
__fab_completion
[[ ${#COMPREPLY[@]} -eq 1 && ${COMPREPLY[0]} == deploy ]]
printf 'PASS cache_reuse\n'
# Deterministic mtime invalidation, no sleeps or inferred timestamp ordering.
stage=cache_invalidation
"$3" -c 'import os;os.utime("fabfile.py",(2000000010,2000000010));os.utime(".fab_tasks~",(2000000000,2000000000))'
COMP_WORDS=(fab cha); COMP_CWORD=1
__fab_completion
[[ ${#COMPREPLY[@]} -eq 1 && ${COMPREPLY[0]} == changed ]]
printf 'PASS cache_invalidation\n'
COMP_WORDS=(fab --ver); COMP_CWORD=1
stage=option_completion
__fab_completion
[[ ${#COMPREPLY[@]} -eq 1 && ${COMPREPLY[0]} == --version ]]
printf 'PASS option_completion\n'
'''

def main():
    import sys
    parser = argparse.ArgumentParser()
    for name in ("bash", "product", "loader", "work"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--harmony", action="store_true")
    args = parser.parse_args()
    root = Path(args.work).absolute()
    if args.harmony:
        assert os.uname().sysname == "HarmonyOS" and os.uname().machine == "aarch64"
        assert str(root).startswith("/storage/Users/currentUser/"), "HMDFS task root required"
        root = root.with_name(root.name + "-harmony")
    assert not root.exists(), "create-new functional work required"
    root.mkdir(parents=True)
    try:
        for directory in ("user/completions", "bin", "补全 空间", "empty-compat", "empty-data"):
            (root / directory).mkdir(parents=True)
        shutil.copyfile(args.product, root / "user/completions/fab")
        (root / "tasks.txt").write_text("deploy\nstatus\n", encoding="utf-8")
        fab = root / "bin/fab"
        # A deterministic replacement for the external Fabric program, not for
        # the completion product, framework, assertions or loader.
        shell = shutil.which("sh")
        assert shell and " " not in shell, "external command fixture needs a native sh"
        fab.write_text("#!" + shell + "\ncase \"$1\" in --shortlist) cat \"$FAB_TEST_TASKS\";; --help) printf '%s\\n' --version --help;; *) exit 64;; esac\n", encoding="utf-8")
        fab.chmod(0o700)
        program = root / "functional.sh"
        program.write_text(SCRIPT, encoding="utf-8")
        env = dict(os.environ, FAB_TEST_TASKS=str(root / "tasks.txt"), BASH_ENV="", ENV="")
        process = subprocess.run([args.bash, str(program).replace("\\", "/"), str(root).replace("\\", "/"),
                                  str(Path(args.loader).absolute()).replace("\\", "/"), sys.executable.replace("\\", "/")],
                                 capture_output=True, timeout=20, env=env)
        sys.stdout.buffer.write(process.stdout); sys.stderr.buffer.write(process.stderr)
        assert process.returncode == 0, "completion execution RC=" + str(process.returncode)
        assert process.stdout.count(b"PASS ") == 4, "functional denominator mismatch"
        if args.harmony:
            cache = root / "补全 空间/.fab_tasks~"
            projected_uid = cache.stat().st_uid
            assert projected_uid != os.getuid(), "HMDFS projected-owner mismatch not exercised"
            assert cache.read_text(encoding="utf-8") == "changed\n"
            print(json.dumps({"uid": os.getuid(), "projected_uid": projected_uid, "cache_recreated": True}))
            print("HARMONY_TEST_PASS=1/1")
        else:
            print("CONSUMER_TEST_PASS=4/4")
    finally:
        assert not root.is_symlink()
        shutil.rmtree(root)
    assert not root.exists(), "task test cleanup failed"

if __name__ == "__main__":
    main()
