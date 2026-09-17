#!/usr/bin/env python3
"""Smoke tests for the packaged lesspipe tools on OHOS."""
import gzip as gzip_mod
import os
import stat
import subprocess
import sys
import tempfile


def system_env():
    """CI runs test_package under a conanrun environment whose PATH may not
    include the system tool directories. lesspipe and its helpers (file, tar,
    gzip) live in the system paths, so extend PATH before spawning them."""
    env = os.environ.copy()
    for p in (
        "/data/service/hnp/bin",
        "/system/bin",
        "/bin",
        "/usr/bin",
        "/vendor/bin",
    ):
        if p not in env.get("PATH", ""):
            env["PATH"] = env.get("PATH", "") + os.pathsep + p
    return env


def assert_executable(path):
    if not os.path.isfile(path):
        raise AssertionError(f"Missing file: {path}")
    mode = os.stat(path).st_mode
    if not mode & stat.S_IXUSR:
        raise AssertionError(f"File is not executable: {path}")


def run_command(args, *, cwd=None, env=None):
    if env is None:
        env = system_env()
    try:
        return subprocess.run(
            args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=60,
            cwd=cwd,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(f"Command timed out after 60 seconds: {args[0]}") from exc


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_lesspipe.py <package-folder>", file=sys.stderr)
        return 2

    pkg = sys.argv[1]
    bin_dir = os.path.join(pkg, "bin")
    libexec = os.path.join(pkg, "libexec", "lesspipe")
    man_dir = os.path.join(pkg, "share", "man", "man1")

    # 1. required deliverables exist and are executable
    for script in ("lesspipe.sh", "archive_color"):
        assert_executable(os.path.join(bin_dir, script))
    assert_executable(os.path.join(libexec, "lesscomplete"))
    manpage = os.path.join(man_dir, "lesspipe.1")
    if not os.path.isfile(manpage):
        raise AssertionError(f"Missing man page: {manpage}")

    lesspipe = os.path.join(bin_dir, "lesspipe.sh")

    # 2. no-argument invocation prints the LESSOPEN setup hint (upstream behavior)
    result = run_command([lesspipe])
    if result.returncode != 0:
        raise AssertionError(f"lesspipe.sh setup hint failed: rc={result.returncode}\n{result.stdout}")
    if "LESSOPEN" not in result.stdout:
        raise AssertionError(f"LESSOPEN hint missing from setup output:\n{result.stdout}")
    if lesspipe not in result.stdout:
        raise AssertionError(f"setup hint does not reference installed path:\n{result.stdout}")

    # 3. version marker: lesspipe prints its version in messages (lesspipe 2.27)
    with open(lesspipe, "r", encoding="utf-8", errors="replace") as handle:
        content = handle.read()
    if "lesspipe_version=2.27" not in content:
        raise AssertionError("Packaged lesspipe.sh is not version 2.27")

    # 4. OHOS toybox file(1) fallback present (the core platform adaptation)
    if "OHOS (toybox) fallback" not in content:
        raise AssertionError("Packaged lesspipe.sh lacks the toybox mime fallback adaptation")

    # 5. real end-to-end run on OHOS: gzip file preview through LESSOPEN protocol
    with tempfile.TemporaryDirectory(prefix="lesspipe-test-") as tmp:
        inner = os.path.join(tmp, "hello.txt")
        with open(inner, "w", encoding="utf-8") as fh:
            fh.write("ohos lesspipe smoke test\n")
        gz = os.path.join(tmp, "hello.txt.gz")
        with open(inner, "rb") as fh_in, gzip_mod.open(gz, "wb") as fh_out:
            fh_out.write(fh_in.read())

        env = system_env()
        env["LESSOPEN"] = f"|{lesspipe} %s"
        env.pop("LESSCOLORIZER", None)
        result = run_command([lesspipe, gz], env=env)
        if result.returncode != 0:
            raise AssertionError(f"lesspipe.sh failed on gzip file: rc={result.returncode}\n{result.stdout}")
        if "ohos lesspipe smoke test" not in result.stdout:
            raise AssertionError(f"gzip content not extracted on OHOS:\n{result.stdout[:500]}")

        # 6. tar archive content listing through the fallback path
        import tarfile
        tarball = os.path.join(tmp, "bundle.tar.gz")
        with tarfile.open(tarball, "w:gz") as tf:
            tf.add(inner, arcname="hello.txt")
        result = run_command([lesspipe, tarball], env=env)
        if result.returncode != 0:
            raise AssertionError(f"lesspipe.sh failed on tar.gz listing: rc={result.returncode}\n{result.stdout}")
        if "hello.txt" not in result.stdout:
            raise AssertionError(f"tar listing does not show member:\n{result.stdout[:500]}")

    print("lesspipe OHOS smoke tests: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
