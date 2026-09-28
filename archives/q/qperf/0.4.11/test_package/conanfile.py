#!/usr/bin/env python3
"""Consumer test for qperf 0.4.11.

Executes the packaged qperf binary (R34: the test drives the product itself,
not a stub):

* ``--version`` / ``--help tests`` output is parsed for the packaged version
  and the socket transport inventory,
* the dynamic dependencies are cross-checked against the advertised RDMA
  transports, so a build that silently dropped or gained libibverbs fails,
* a real server/client pair is run over the loopback interface for tcp_bw,
  tcp_lat, udp_lat and udp_bw, and the numeric measurement is required to be
  present and non-zero,
* the six remaining transports this build registers (sctp_bw, sctp_lat,
  sdp_bw, sdp_lat, rds_bw, rds_lat) are driven over loopback too, each against
  its own dedicated server (own port, own log, reaped by its own PID), and the
  assertion for each requires either a real measurement or that transport's
  genuine kernel-level refusal ("unable to make SCTP socket", "unable to make
  SDP socket", "socket failed: Address family not supported") read from the
  server or client log; the downstream artifact "getaddrinfo failed:
  Unrecognized service" is not accepted as evidence,
* the server is torn down through upstream's own ``quit`` test and must exit.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import load


class QperfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "run_tests.sh"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keep generators and logs out of the archived test_package directory.
        self.folders.build = "build"
        self.folders.generators = "build/conan"

    def test(self):
        if not can_run(self):
            raise ConanException(
                "qperf consumer test executes the packaged binary; "
                "it cannot be skipped in a non-runnable environment")

        package = self.dependencies["qperf"].package_folder
        binary = os.path.join(package, "bin", "qperf")
        if not os.path.isfile(binary):
            raise ConanException(f"packaged qperf missing: {binary}")
        if not os.path.isfile(os.path.join(package, "licenses", "COPYING")):
            raise ConanException("packaged license missing: licenses/COPYING")

        work = os.path.join(self.build_folder, "work")
        os.makedirs(work, exist_ok=True)
        shell = shutil.which("sh") or "/bin/sh"
        script = os.path.join(self.source_folder, "run_tests.sh")
        out = os.path.join(work, "run_tests.out")

        self.run(f'"{shell}" "{script}" "{binary}" "{work}" >"{out}" 2>&1',
                 env="conanrun")

        text = load(self, out)
        self.output.info(text)
        match = re.search(r"RESULT pass=(\d+) fail=(\d+) total=(\d+)", text)
        if not match:
            raise ConanException("run_tests.sh produced no RESULT summary")
        passed, failed, total = (int(g) for g in match.groups())
        # The harness scores 31 assertions and turns anything it cannot
        # evaluate into a failure rather than a skip, so the floor is the
        # exact expected count: a silently weakened harness cannot pass.
        # 7 version/inventory + 1 link coherence + 3 server lifecycle
        # + 14 loopback measurements + 6 attributable transport attempts = 31,
        # identical to test_package/MANIFEST.yml (assertion_count), the
        # [PASS] lines run_tests.sh prints, notes.md's five-dimension ledger
        # and reports/test-report.md.
        if failed or passed < 31 or total != 31:
            raise ConanException(
                f"qperf consumer test incomplete (expected 31 assertions): "
                f"pass={passed} fail={failed} total={total}")
        self.output.info(f"qperf consumer test: {passed}/{total} assertions pass")
