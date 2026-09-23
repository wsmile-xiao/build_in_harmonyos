#!/usr/bin/env python3
"""Conan recipe for libytnef 2.1.2 — TNEF (winmail.dat) decoding library.

libytnef decodes TNEF (Transport Neutral Encapsulation Format) streams, the
container Microsoft Outlook uses for the `winmail.dat` attachment that non
Outlook clients cannot open.  Yerase's TNEF Stream Reader ships the shared
library plus two small command line tools (`ytnef`, `ytnefprint`).

Adaptation notes
----------------
* The official tag tarball ships no generated `configure`, so `build()`
  bootstraps with `autoreconf -fi`; `automake`/`libtool` are declared as
  tool_requires so a clean CI worker also has them.
* E007/E072: the generated `config.guess` has no HarmonyOS branch, and both
  `config.guess` and `config.status` create their `mktemp -d` under
  `umask 077` — HMDFS hands that directory back unwritable, so the platform
  probe dies on `dummy.c` and config.status on `subs1.awk`.  Both generated
  scripts are normalised to `umask 022` before they run, and the build passes
  the `aarch64-unknown-linux-ohos` triplet that the generated `config.sub`
  already accepts, so nothing has to be guessed.  build == host keeps this a
  native build, so `AC_RUN_IFELSE` probes still execute.
* `make -j2` fails on OHOS ("jobserver mkfifo ... Operation not permitted");
  the build runs single job.
* Upstream registers no automake test suite (`make check` has an empty TESTS
  list).  Its only test entry point is `test-data/test.sh`: it extracts the
  attachments of the bundled sample messages, diffs them against the committed
  expected results and then asserts six decoded fields through `ytnefprint`.
  `build()` runs it and reports the executed checks.
"""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rm)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

UPSTREAM = "https://github.com/Yeraze/ytnef"


class LibytnefConan(ConanFile):
    name = "libytnef"
    version = "2.1.2"
    description = ("Yerase's TNEF Stream Reader — library and tools to decode TNEF "
                   "(winmail.dat) streams")
    license = "GPL-2.0-or-later"
    homepage = UPSTREAM
    url = UPSTREAM
    topics = ("tnef", "winmail", "outlook", "email", "mime", "mapi")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libytnef is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-dependency-tracking")
        if self.settings.os == "OHOS":
            # E007/E072: skip config.guess entirely with the triplet config.sub knows
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        apply_conandata_patches(self)
        autotools.autoreconf()
        self._normalise_hmdfs_umask()
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    def _normalise_hmdfs_umask(self):
        """E011/E114: `umask 077` mktemp dirs are unusable on HMDFS.

        autoconf's config.status machinery and config.guess both create their
        temporary directory with `umask 077`; on HMDFS the directory is then not
        writable by its own creator, which aborts the platform guess
        (`dummy.c`) and the config.status setup (`subs1.awk`).  The generated
        scripts are rewritten to `umask 022`, keeping the mktemp -d itself.
        """
        for name in ("configure", "config.guess"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            if "umask 077" not in content:
                raise ConanInvalidConfiguration(
                    f"expected 'umask 077' in {name} (E011 workaround anchor missing)")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content.replace("umask 077", "umask 022"))
            os.chmod(path, 0o755)
            self.output.info(f"  [ok] {name}: mktemp umask normalised to 022 (E011)")

    def _run_upstream_tests(self):
        """Run upstream's only test entry point: test-data/test.sh.

        The script drives the freshly built tools through relative
        `../<tool>/<tool>` paths, so it has to run inside the build tree with
        the sample messages and the committed expected results copied next to
        the generated test-data/Makefile (this is an out-of-source build).
        """
        import shutil

        src_data = os.path.join(self.source_folder, "test-data")
        build_data = os.path.join(self.build_folder, "test-data")
        shutil.copytree(src_data, build_data, dirs_exist_ok=True)
        script = os.path.join(build_data, "test.sh")
        if not os.path.isfile(script):
            raise ConanException("upstream test script test-data/test.sh is missing")

        tmp_dir = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        # automake generates a `check` target, but upstream registers no TESTS entry
        self.output.info("  [info] make check: upstream registers no TESTS; "
                         "running test-data/test.sh with sh (its only test entry point)")
        self.run("make check", cwd=self.build_folder, env="conanbuild")

        env = os.environ.copy()
        env["TMPDIR"] = tmp_dir
        proc = subprocess.run(["sh", "./test.sh"], cwd=build_data, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=1800)
        output = proc.stdout
        self.output.info(output if proc.returncode != 0 else output[-1500:])

        # `set -ex` traces every step: 1 attachment extraction + diff, then 6 greps
        extraction = len(re.findall(r"^\+\s*diff results data", output, re.M))
        # each assertion is a `ytnefprint ... | grep ... | grep ...` pipeline,
        # so one ytnefprint invocation == one upstream assertion group
        field_checks = len(re.findall(r"^\+\s*\.\./ytnefprint/ytnefprint ", output, re.M))
        executed = extraction + field_checks
        status = "passed" if proc.returncode == 0 and extraction == 1 \
            and field_checks == 6 else "failed"
        marker = {
            "status": status,
            "framework": "shell (upstream test-data/test.sh)",
            "command": "sh test-data/test.sh",
            "discovered": 7,
            "executed": executed,
            "passed": executed if status == "passed" else 0,
            "failed": 0 if status == "passed" else 7 - executed,
            "skipped": 0,
            "note": ("1 attachment-extraction diff over winmail.dat plus 6 ytnefprint "
                     "field assertions"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if status != "passed":
            self.output.error("upstream tests failed; tail:\n" + output[-3000:])
            raise ConanException("upstream tests failed")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["ytnef"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "libytnef")
