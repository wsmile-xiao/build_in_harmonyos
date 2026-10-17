#!/usr/bin/env python3
"""Test package for ts — verifies the ts-node CLI tools work.

L1 test: runs `ts-node --version` and executes a real TypeScript file
through the installed wrapper, proving that the packaged dist/, the
bundled node_modules (incl. peer typescript) and the wrapper all work.

Assertions are implemented with Python subprocess instead of a shell
script: some CI workers cannot fork subshells ("can't fork - try again"),
which breaks `$(...)` command substitution in test_ts.sh, while Python
subprocess (used by conan itself for every self.run) works fine there.
"""
import os
import subprocess

from conan import ConanFile

SMOKE_TS = (
    'const answer: number = 40 + 2;\n'
    'function greet(name: string): string {\n'
    '    return `hello ${name}`;\n'
    '}\n'
    'if (answer !== 42) { process.exit(1); }\n'
    'console.log(`ts-node-ok:${answer}:${greet("ohos")}`);\n'
)

BAD_TS = 'const n: number = "not a number";\n'


class TsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _run(self, wrapper, args, expect_ok=True):
        """Run the wrapper via `sh` and return the CompletedProcess.

        HMDFS denies the exec bit on scripts (E087) and `command -v`
        cannot see non-executable files, so the wrapper path comes from
        the dependency info and is invoked through `sh` explicitly.
        The wrapper itself is fork-free (${0%/*} parameter expansion).
        `sh` is resolved to its absolute path: conan's test environment
        may scrub PATH, and a bare "sh" then raises FileNotFoundError.
        """
        sh = "/system/bin/sh" if os.path.isfile("/system/bin/sh") else "sh"
        proc = subprocess.run([sh, wrapper] + args,
                              capture_output=True, text=True, timeout=300)
        if expect_ok and proc.returncode != 0:
            raise AssertionError(
                "expected success: sh %s %s\nstdout:\n%s\nstderr:\n%s"
                % (wrapper, " ".join(args), proc.stdout, proc.stderr))
        return proc

    def test(self):
        wrapper = os.path.join(
            self.dependencies["ts"].package_folder, "bin", "ts-node")

        # Assertion 1: --version outputs 10.9.2
        proc = self._run(wrapper, ["--version"])
        if "10.9.2" not in proc.stdout:
            raise AssertionError("expected 10.9.2 in --version output, got: %s"
                                 % proc.stdout)

        # Assertion 2: a real TypeScript file compiles and runs
        with open("smoke.ts", "w", encoding="utf-8") as f:
            f.write(SMOKE_TS)
        proc = self._run(wrapper, ["smoke.ts"])
        if "ts-node-ok:42:hello ohos" not in proc.stdout:
            raise AssertionError("unexpected smoke.ts output: %s" % proc.stdout)

        # Assertion 3: a type error must be rejected (compiler engaged)
        with open("bad.ts", "w", encoding="utf-8") as f:
            f.write(BAD_TS)
        proc = self._run(wrapper, ["bad.ts"], expect_ok=False)
        if proc.returncode == 0:
            raise AssertionError("type error was not reported")
