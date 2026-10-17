#!/usr/bin/env python3
"""Consumer test for vc-dwim/vc-chlog scripts (real API usage, R34).

Usage: python3 test_vc_dwim.py <bindir>
Exercises the two tools end-to-end; asserts 6 checks.
"""
import os
import shutil
import subprocess
import sys
import tempfile

bindir = sys.argv[1]
vc_dwim = os.path.join(bindir, "vc-dwim")
vc_chlog = os.path.join(bindir, "vc-chlog")

env = dict(os.environ)
home = os.path.expanduser("~")
for cand in (os.path.join(home, "usr", "local", "bin"),
             "/data/service/hnp/bin"):
    if os.path.isdir(cand) and cand not in env.get("PATH", ""):
        env["PATH"] = cand + os.pathsep + env.get("PATH", "")
env.setdefault("HOME", home)
env.setdefault("TMPDIR", tempfile.gettempdir())


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, env=env, **kw)


# 1/2: smoke — both tools report the right version
r = run([vc_dwim, "--version"])
assert r.returncode == 0 and "1.10" in r.stdout, (r.returncode, r.stdout, r.stderr)
print(f"OK vc-dwim --version: {r.stdout.strip()}")
r = run([vc_chlog, "--version"])
assert r.returncode == 0 and "1.10" in r.stdout, (r.returncode, r.stdout, r.stderr)
print(f"OK vc-chlog --version: {r.stdout.strip()}")

# 3/4: functional — vc-dwim --diff matches ChangeLog entry to the git diff
git = shutil.which("git")
if git:
    with tempfile.TemporaryDirectory() as td:
        repo = os.path.join(td, "repo")
        os.makedirs(repo)

        def g(*args):
            run([git, "-C", repo] + list(args))

        g("init", "-q", "-b", "master", ".")
        with open(os.path.join(repo, "file1"), "w") as fh:
            fh.write("a\nb\nc\n")
        with open(os.path.join(repo, "ChangeLog"), "w") as fh:
            fh.write("2020-01-01  T <t@t>\n\n\t* file1: init\n\n")
        g("add", "-A")
        g("-c", "user.email=t@t", "-c", "user.name=T", "commit", "-qm", "init")
        with open(os.path.join(repo, "file1"), "w") as fh:
            fh.write("a\nB\nc\n")
        with open(os.path.join(repo, "ChangeLog"), "w") as fh:
            fh.write("Fix b\n\n2020-01-01  T <t@t>\n\n\t* file1: change b\n\n")
        r = run([vc_dwim, "--diff", "ChangeLog"], cwd=repo)
        assert r.returncode == 0, r.stderr
        assert "+Fix b" in r.stdout and "@@" in r.stdout, r.stdout
        print("OK vc-dwim --diff showed the ChangeLog diff (git plumbing OK)")
else:
    print("SKIP vc-dwim --diff (git not found)")

# 5/6: functional — vc-chlog --stdin generates a GCS-style entry
diff = ("--- file1\t2020-01-01\n"
        "+++ file1\t2020-01-02\n"
        "@@ -1 +1,2 @@\n"
        " bla\n"
        "+new line\n")
with tempfile.TemporaryDirectory() as td:
    r = run([vc_chlog, "--stdin"], cwd=td, input=diff)
    assert r.returncode == 0, r.stderr
    assert "* file1:" in r.stdout, r.stdout
    print(f"OK vc-chlog --stdin generated entry:\n{r.stdout.strip()}")

print("vc-dwim test_package PASSED")
