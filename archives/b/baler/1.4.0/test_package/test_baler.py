#!/usr/bin/env python3
"""Consumer test — import baler and exercise helper API."""

import os
import shutil
import sys
import tempfile

# Accept site-packages as argv[1] if provided (test_package passes it)
if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
    sp = sys.argv[1]
    if sp not in sys.path:
        sys.path.insert(0, sp)

# HMBS OHOS: helper is now patched to make heavy deps optional (0002-helper-optional-deps.patch)
# so import succeeds even without torch/numpy/sklearn wheels on aarch64.
# No Dummy stub needed — patch makes helper import pure-python.
from baler.modules import helper


def _get_tmpdir():
    # HMBS readonly /tmp fix: respect TMPDIR/TMP/TEMP (injected by hmbs, may be /data/tmp)
    for k in ("TMPDIR", "TMP", "TEMP"):
        v = os.environ.get(k)
        if v and os.path.isdir(v):
            # verify writable
            try:
                test = os.path.join(v, ".hmbs_write_test")
                with open(test, "w") as f:
                    f.write("1")
                os.unlink(test)
                return v
            except Exception:
                continue
    # Fallback: try tempfile.gettempdir() only if writable, else cwd
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


def test_import():
    assert hasattr(helper, "create_new_project"), "helper.create_new_project missing"
    assert hasattr(helper, "Config"), "helper.Config missing"
    print("import check passed")


def test_create_new_project():
    tmpdir = _get_tmpdir()
    tmp = tempfile.mkdtemp(prefix="baler-test-", dir=tmpdir)
    try:
        workspace = "test_ws"
        project = "test_proj"
        base = tmp
        helper.create_new_project(workspace, project, base_path=base)
        ws_path = os.path.join(base, workspace)
        proj_path = os.path.join(ws_path, project)
        assert os.path.isdir(ws_path), "workspace not created"
        assert os.path.isdir(proj_path), "project not created"
        expected = [
            os.path.join(ws_path, "data"),
            os.path.join(proj_path, "config"),
            os.path.join(proj_path, "output", "compressed_output"),
            os.path.join(proj_path, "output", "training"),
        ]
        for d in expected:
            assert os.path.isdir(d), f"missing {d}"
        print("create_new_project check passed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_import()
    test_create_new_project()
    print("All test_baler checks passed")
