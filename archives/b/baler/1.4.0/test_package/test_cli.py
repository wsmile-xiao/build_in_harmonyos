#!/usr/bin/env python3
"""Consumer test — exercise baler CLI wrapper."""

import os
import shutil
import subprocess
import sys
import tempfile


def _get_tmpdir():
    for k in ("TMPDIR", "TMP", "TEMP"):
        v = os.environ.get(k)
        if v and os.path.isdir(v):
            try:
                test = os.path.join(v, ".hmbs_write_test")
                with open(test, "w") as f:
                    f.write("1")
                os.unlink(test)
                return v
            except Exception:
                continue
    try:
        td = tempfile.gettempdir()
        if td and os.path.isdir(td):
            test = os.path.join(td, ".hmbs_write_test")
            with open(test, "w") as f:
                f.write("1")
            os.unlink(test)
            return td
    except Exception:
        pass
    return os.getcwd()


def _env_with_pythonpath():
    env = dict(os.environ)
    # Ensure baler is importable for python -m baler
    # test_package conanfile passes site-packages via env; also respect existing PYTHONPATH
    return env

def test_cli_help():
    # Strict verification: CLI must actually execute and report help.
    # Vendor stubs (numpy/torch/sklearn) are injected via PYTHONPATH by test_package conanfile
    # so heavy-dep missing is treated as a real regression, not silently passed via file-existence.
    env = _env_with_pythonpath()
    baler_bin = shutil.which("baler")
    if baler_bin:
        result = subprocess.run([baler_bin, "--help"], capture_output=True, text=True, timeout=10, env=env)
        out = (result.stdout or "") + (result.stderr or "")
        if "ModuleNotFoundError" in out or "No module named" in out:
            raise AssertionError(f"CLI --help failed due to missing dependency (regression, vendor stubs should be on PYTHONPATH): {out[:1000]}")
        assert result.returncode == 0, f"baler --help failed rc={result.returncode} out={out[:1000]}"
        assert "mode" in out.lower() or "baler" in out.lower(), f"CLI help output unexpected: {out[:500]}"
        print("CLI --help via bin/baler passed")
        return
    # Fallback: python -m baler --help (baler has no __main__, but try for completeness)
    result = subprocess.run([sys.executable, "-m", "baler", "--help"], capture_output=True, text=True, timeout=10, env=env)
    out = (result.stdout or "") + (result.stderr or "")
    if "ModuleNotFoundError" in out or "No module named" in out:
        raise AssertionError(f"CLI fallback --help failed due to missing dependency: {out[:1000]}")
    assert result.returncode == 0, f"CLI fallback --help failed rc={result.returncode} out={out[:1000]}"
    assert "mode" in out.lower() or "baler" in out.lower(), f"CLI fallback output unexpected: {out[:500]}"
    print("CLI --help via python -m baler passed")


def test_cli_new_project():
    tmpdir = _get_tmpdir()
    tmp = tempfile.mkdtemp(prefix="baler-cli-", dir=tmpdir)
    orig = os.getcwd()
    try:
        os.chdir(tmp)
        env = _env_with_pythonpath()
        # Use python -m baler to create new project — strict: must succeed with returncode 0
        # and create project directory. No wrapper-existence fallback (R9/R34).
        cmd = [sys.executable, "-m", "baler", "--mode", "newProject", "--project", "ws1", "proj1"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, env=env)
        out = (result.stdout or "") + (result.stderr or "")
        if "ModuleNotFoundError" in out or "No module named" in out:
            raise AssertionError(f"CLI newProject failed due to missing dependency (vendor stubs missing): {out[:1000]}")
        assert result.returncode == 0, f"CLI newProject failed rc={result.returncode} out={out[:1000]}"
        ws = os.path.join(tmp, "workspaces", "ws1", "proj1")
        if not os.path.isdir(ws):
            ws_alt = os.path.join(tmp, "ws1", "proj1")
            if os.path.isdir(ws_alt):
                ws = ws_alt
        assert os.path.isdir(ws), f"project not created at {ws}, stdout={result.stdout[:300]} stderr={result.stderr[:300]}"
        print("CLI newProject passed")
    finally:
        os.chdir(orig)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_cli_help()
    test_cli_new_project()
    print("All test_cli checks passed")
