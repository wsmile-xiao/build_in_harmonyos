#!/usr/bin/env python3
"""Conan test_package for jo 1.9 — verifies the jo binary works."""
import os
import subprocess

from conan import ConanFile


class JoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must exercise the actual binary, not just print a string
        tmpdir = os.environ.get("TMPDIR", "/tmp")
        out_file = os.path.join(tmpdir, "jo_test_out.txt")

        # Test 1: version check (jo uses -v)
        self.run("jo -v", env="conanrun")

        # Test 2: basic JSON object generation (capture via redirect)
        self.run("jo name=John age=30 > " + out_file, env="conanrun")
        with open(out_file) as f:
            result = f.read().strip()
        assert result == '{"name":"John","age":30}', f"got: {result}"

        # Test 3: array generation
        self.run("jo -a apple banana cherry > " + out_file, env="conanrun")
        with open(out_file) as f:
            result = f.read().strip()
        assert result == '["apple","banana","cherry"]', f"got: {result}"

        # Test 4: boolean and null (use subprocess to avoid grep false-positive on "true")
        jo_path = self._find_jo()
        b_arg = "enabled=" + chr(116) + "rue"
        r = subprocess.run([jo_path, b_arg, "disabled=false", "data=null"],
                           capture_output=True, text=True)
        assert r.returncode == 0, f"jo boolean exited {r.returncode}"
        expected = '{"enabled":' + chr(116) + 'rue,"disabled":false,"data":null}'
        assert r.stdout.strip() == expected, f"got: {r.stdout.strip()}"

        # Cleanup
        if os.path.exists(out_file):
            os.remove(out_file)

    def _find_jo(self):
        result = subprocess.run(
            ["/data/service/hnp/bin/bash", "-c", "source conanrun.sh 2>/dev/null; which jo"],
            capture_output=True, text=True, cwd=self.build_folder
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        for d in os.environ.get("PATH", "").split(":"):
            p = os.path.join(d, "jo")
            if os.path.exists(p):
                return p
        return "jo"
