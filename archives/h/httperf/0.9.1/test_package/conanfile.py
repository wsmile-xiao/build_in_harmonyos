#!/usr/bin/env python3
"""Conan test_package - httperf 0.9.1

R34: test_package must substantially exercise the tested package's functionality.
httperf is a command-line benchmark tool (not a library), so tests run the
binary directly against a local HTTP server.

Tests:
  1. httperf --version          - verify binary is installed and runnable
  2. httperf real benchmark     - run against local http.server on loopback,
                                  verify connections/replies are generated
"""
import subprocess
import sys
import time

from conan import ConanFile


class HttperfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test 1: httperf --version (smoke test - binary installed and runnable)
        self.run("httperf --version", env="conanrun")

        # Test 2: real benchmark against a local HTTP server on loopback.
        # self.run(env="conanrun") injects the package bin dir into PATH
        # (subprocess.run would miss it and fail with rc=127).
        server = subprocess.Popen(
            [sys.executable, "-m", "http.server", "18080", "--bind", "127.0.0.1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            time.sleep(2)  # wait for server to bind
            self.run(
                "httperf --server=127.0.0.1 --port=18080 "
                "--num-conns=3 --num-calls=2 --rate=5 "
                "| grep -q '^Total: connections 3\\b requests 6\\b replies 3\\b'",
                env="conanrun",
            )
        finally:
            server.terminate()
            server.wait()
