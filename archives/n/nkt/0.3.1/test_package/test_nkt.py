#!/usr/bin/env python3
"""Exercise the installed nkt binary with a real note-taking workflow."""

import os
import pathlib
import subprocess
import sys


def run_checked(command, env=None):
    result = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
        env=env,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"command failed ({result.returncode}): {command!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_nkt.py <nkt> <workdir>")

    executable = pathlib.Path(sys.argv[1]).resolve()
    workdir = pathlib.Path(sys.argv[2]).resolve()
    assert executable.is_file(), f"missing nkt executable: {executable}"

    # 1) exact version via `nkt config`
    #    (`nkt --version` is silent upstream: the buffered writer is never
    #    flushed on the early-return path; `nkt config` reports the same
    #    version deterministically and is flushed by the command executor)
    config = run_checked([str(executable), "config"])
    assert "nkt version            : 0.3.1" in config, config
    assert "nkt schema version     : 0.5.0" in config, config

    # 2) command reference via `nkt help`
    help_text = run_checked([str(executable), "help"])
    for name in ("chains", "config", "edit", "find", "init", "list", "log",
                 "new", "read", "task"):
        assert f" {name:<12}" in help_text or f"- {name}" in help_text, (
            f"command {name!r} missing from help:\n{help_text}"
        )

    # 3) real workflow against an isolated NKT_ROOT_DIR
    root = workdir / "nkt-home"
    env = dict(os.environ)
    env["NKT_ROOT_DIR"] = str(root)

    init_out = run_checked([str(executable), "init"], env=env)
    assert "Home directory initialized" in init_out, init_out
    assert (root / "config.json").is_file(), "init did not create config.json"

    tag_out = run_checked([str(executable), "new", "tag", "smoketag"], env=env)
    assert "smoketag" in tag_out, tag_out

    log_out = run_checked(
        [str(executable), "log", "hello harmony @smoketag"], env=env
    )
    assert "journal 'diary'" in log_out, log_out

    read_out = run_checked([str(executable), "read"], env=env)
    assert "hello harmony @smoketag" in read_out, read_out

    ls_out = run_checked([str(executable), "ls"], env=env)
    assert "Journals:" in ls_out, ls_out
    assert "diary" in ls_out and "(1 day)" in ls_out, ls_out
    assert "Tasklists:" in ls_out, ls_out

    print("nkt consumer test passed: version, help, init, tag, log, read, ls")


if __name__ == "__main__":
    main()
