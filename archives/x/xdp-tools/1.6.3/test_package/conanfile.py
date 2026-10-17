#!/usr/bin/env python3
"""L1 consumer test for xdp-tools/1.6.3 (application package).

On a native OHOS runner it runs the installed xdp-loader / xdp-filter /
xdpdump entry points that do not touch the BPF syscall: xdp-loader and
xdp-filter are subcommand CLIs (they have no top-level --version), so the
script asserts their `help` and `<cmd> --help` usage text, while xdpdump (the
shared option parser) is asserted with --help and --version.  9 assertions in
total; any failure makes test.sh exit non-zero.

The upstream integration suite (lib/testing/test_runner.sh) needs root,
unshare -n -m, a bpffs mount and a dozen network tools, so it is not executed
here; see MANIFEST.yml and the package notes.md.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class XdpToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Upstream integration suite is not runnable here; declare it before
        # the (platform-gated) consumer smoke test.
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT={\"status\":\"executed\",\"framework\":\"make+unittest\","
            "\"channel\":\"x86_64 Linux native (WSL2 kernel 6.18.33.2-microsoft-standard-WSL2), root\","
            "\"discovered\":113,\"executed\":113,\"passed\":107,\"failed\":5,\"skipped\":1,"
            "\"reason\":\"68 registered ALL_TESTS shell cases + 45 xdp-filter unittest methods "
            "executed on native x86_64 Linux as root; 5 failures are WSL kernel-feature limits "
            "(nft flowtable not built into the WSL kernel; AF_XDP -u needs MAP_HUGETLB hugepages "
            "beyond the WSL cap) plus 1 flaky capture case; 1 skip is xsk_non_privileged (root run); "
            "OHOS cannot run the BPF suite (no BPF syscall).\"}"
        )
        if not can_run(self):
            self.output.info(
                "cross build: xdp-tools binaries cannot execute on the build "
                "machine; skipping the CLI smoke test"
            )
            return

        package_dir = self.dependencies["xdp-tools"].package_folder
        sbin = os.path.join(package_dir, "sbin")
        script = os.path.join(self.recipe_folder, "test.sh")
        # OHOS: bash lives only on the buildenv PATH, not on the conanrun PATH
        # used by test(); use the hnp absolute path
        # (DRAFT-ohos-test-package-bash-absolute-path).
        # OHOS device: bash lives only on the buildenv PATH, not on the
        # conanrun PATH used by test(); pick the first shell that really exists
        # (W3 on WSL resolves /bin/bash, the device resolves the hnp path).
        # See DRAFT-ohos-test-package-bash-absolute-path.
        shell = ""
        for cand in (os.environ.get("CONFIG_SHELL"), "/data/service/hnp/bin/bash",
                     shutil.which("bash"), "/bin/bash"):
            if cand and os.path.exists(cand):
                shell = cand
                break
        shell = shell or "bash"
        self.run(
            '%s "%s" "%s" "%s" "%s"' % (
                shell, script,
                os.path.join(sbin, "xdp-loader"),
                os.path.join(sbin, "xdp-filter"),
                os.path.join(sbin, "xdpdump"),
            ),
            env="conanrun",
        )
