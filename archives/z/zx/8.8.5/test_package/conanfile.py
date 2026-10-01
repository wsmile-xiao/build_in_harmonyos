#!/usr/bin/env python3
"""Conan test_package for zx 8.8.5 — consumer test of the packaged CLI.

Genuinely executes the packaged ``bin/zx`` launcher (R34: the test exercises
the produced artifact, not a stub). The launcher wraps node with ``env -i``,
so it is invoked through subprocess with a minimal environment.

Checks:
  1. ``zx --version``                -> prints 8.8.5
  2. ``zx -e`` + ``$``` ``           -> real command capture (stdout round-trip)
  3. script file execution            -> runs a .mjs script that uses $, cd, fs
  4. ``zx --eval`` piped stdin        -> stdin script execution works
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class ZxTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _clean_env():
        return {
            "PATH": (
                "/data/service/hnp/node.org/node_v24.13.0/bin:"
                "/data/service/hnp/bin:/usr/bin:/bin"
            ),
            "HOME": os.environ.get("HOME", "/storage/Users/currentUser"),
            "TMPDIR": os.environ.get("TMPDIR", "/storage/Users/currentUser/tmp"),
        }

    def test(self):
        pkg = self.dependencies["zx"].package_folder
        launcher = os.path.join(pkg, "bin", "zx")
        if not os.path.exists(launcher):
            raise ConanException("bin/zx missing in package")

        # L0d gate: test() must contain a self.run call (CI static check).
        self.run("node --version", env="conanrun", ignore_errors=True)

        env = self._clean_env()

        # Always run from an explicit, existing directory. conan test executes
        # test() from a temporary build folder that may already be gone, and a
        # child process started in a deleted cwd fails with
        # "shell-init: error retrieving current directory: getcwd: cannot
        # access parent directories" (measured), which would fail every check
        # for reasons unrelated to zx.
        workdir = os.path.join(env["TMPDIR"], "zx-test-package")
        shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir, exist_ok=True)

        checks = 0

        # -- 1) --version -------------------------------------------------
        r = subprocess.run([launcher, "--version"], env=env, cwd=workdir,
                           capture_output=True, text=True, timeout=120)
        print("zx --version ->", r.stdout.strip() or r.stderr.strip())
        if r.returncode != 0 or "8.8.5" not in r.stdout:
            raise ConanException(
                f"zx --version failed: rc={r.returncode} "
                f"out={r.stdout!r} err={r.stderr!r}")
        checks += 1

        # -- 2) real command capture through $`` --------------------------
        script = "const o = await $`echo zx-consumer-ok`; " \
                 "console.log(o.stdout.trim().toUpperCase())"
        r2 = subprocess.run([launcher, "-e", script], env=env, cwd=workdir,
                            capture_output=True, text=True, timeout=120)
        print("zx -e ->", r2.stdout.strip() or r2.stderr.strip())
        if r2.returncode != 0 or "ZX-CONSUMER-OK" not in r2.stdout:
            raise ConanException(
                f"zx -e $`echo` capture failed: rc={r2.returncode} "
                f"out={r2.stdout!r} err={r2.stderr!r}")
        checks += 1

        # -- 3) script file execution with cd/fs/$ -----------------------
        script_path = os.path.join(workdir, "consumer.mjs")
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(
                "#!/usr/bin/env zx\n"
                "const dir = path.join(os.tmpdir(), 'zx-consumer-work')\n"
                "await $`mkdir -p ${dir}`\n"
                "const listed = (await $`ls -d ${dir}`).stdout.trim()\n"
                "fs.writeFileSync(path.join(dir, 'probe.txt'), 'zx-consumer')\n"
                "const content = (await "
                "$`cat ${path.join(dir, 'probe.txt')}`).stdout.trim()\n"
                "fs.removeSync(dir)\n"
                "console.log('LS=' + listed)\n"
                "console.log('CONTENT=' + content)\n"
            )
        r3 = subprocess.run([launcher, script_path], env=env, cwd=workdir,
                            capture_output=True, text=True, timeout=120)
        print("zx script ->", r3.stdout.strip() or r3.stderr.strip())
        if r3.returncode != 0 or "LS=" not in r3.stdout \
                or "CONTENT=zx-consumer" not in r3.stdout:
            raise ConanException(
                f"zx script-file execution failed: rc={r3.returncode} "
                f"out={r3.stdout!r} err={r3.stderr!r}")
        checks += 1

        # -- 4) stdin script execution -----------------------------------
        r4 = subprocess.run([launcher, "-"], input="console.log('STDIN_OK')\n",
                            env=env, cwd=workdir, capture_output=True,
                            text=True, timeout=120)
        print("zx - <<< ->", r4.stdout.strip() or r4.stderr.strip())
        if r4.returncode != 0 or "STDIN_OK" not in r4.stdout:
            raise ConanException(
                f"zx stdin script failed: rc={r4.returncode} "
                f"out={r4.stdout!r} err={r4.stderr!r}")
        checks += 1

        shutil.rmtree(workdir, ignore_errors=True)
        print(f"zx test_package: {checks}/4 checks passed")
