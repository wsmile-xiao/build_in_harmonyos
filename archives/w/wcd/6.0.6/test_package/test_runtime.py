"""Independent consumer smoke test; no source-tree paths are used."""

import os
import pathlib
import shlex
import subprocess
import sys
import tempfile


package = pathlib.Path(sys.argv[1])
binary = package / "bin" / "wcd"
wrapper = package / "share" / "wcd" / "wcd.sh"
assert binary.is_file() and wrapper.is_file()

with tempfile.TemporaryDirectory(prefix="wcd-consumer-", dir=os.getcwd()) as td:
    root = pathlib.Path(td)
    home = root / "home"
    target = root / "tree" / "alpha"
    home.mkdir()
    target.mkdir(parents=True)
    env = os.environ.copy()
    env["WCDHOME"] = str(home)
    env["PATH"] = str(package / "bin") + os.pathsep + env.get("PATH", "")

    subprocess.run([str(binary), "-S", str(root / "tree")], env=env,
                   cwd=root, check=True, capture_output=True, text=True)
    assert (home / ".treedata.wcd").is_file()

    selected = subprocess.run([str(binary), "alpha"], env=env, cwd=root,
                              check=True, capture_output=True, text=True)
    go = home / "bin" / "wcd.go"
    assert go.is_file() and str(target) in go.read_text()
    assert "alpha" in selected.stdout

    command = ". {}; wcd alpha; pwd".format(shlex.quote(str(wrapper)))
    shell = subprocess.run(["sh", "-c", command], env=env, cwd=root,
                           check=True, capture_output=True, text=True)
    assert pathlib.Path(shell.stdout.splitlines()[-1]) == target, shell.stdout
    print("WCD packaged binary, isolated scan, go script and shell function: PASS")
