import json
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibnvmeConan(ConanFile):
    name = "libnvme"
    version = "1.16.2"
    description = (
        "NVMe storage device management library: the core library used by "
        "nvme-cli for enumerating and managing NVMe controllers, namespaces "
        "and fabrics connections"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/linux-nvme/libnvme"
    url = "https://github.com/linux-nvme/libnvme"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tls": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_tls": True,
    }

    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libnvme requires a Linux kernel UAPI environment, "
                f"unsupported os: {self.settings.os}"
            )

    def requirements(self):
        # The JSON config file format (nvme_read_config / nvme_dump_config /
        # json tree serialization) is resolved through json-c.
        self.requires("json-c/0.18")
        if self.options.with_tls:
            # OpenSSL backs the DH-HMAC-CHAP and NVMe-TLS PSK derivation
            # APIs (nvme_gen_dhchap_key, nvme_generate_tls_key_identity,
            # nvme_export/import_tls_key ...). It is linked statically
            # (PIC) into libnvme and is a private dependency: consumers
            # do not link against it (accountsservice precedent for the
            # visible=False private-dep pattern).
            self.requires("openssl/3.5.7", visible=False)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_jsonc_pc_include_subdir()
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nofallback",
            "default_library": "shared" if self.options.shared else "static",
            # python bindings need swig + Python.h; out of scope here
            "python": "disabled",
            "openssl": "enabled" if self.options.with_tls else "disabled",
            # OHOS has no libkeyutils / keyctl syscall: force-disable so
            # the auto-probe cannot pick up random host artifacts.
            "keyutils": "disabled",
            "libdbus": "disabled",
            "liburing": "disabled",
            "docs": "false",
            "docs-build": "false",
            "examples": "false",
            "tests": "true",
        })
        tc.generate()
        self._inject_meson_tools()

    def build(self):
        apply_conandata_patches(self)
        self._ensure_meson_available()
        with self._build_env().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            if not cross_building(self) and can_run(self):
                self._run_upstream_tests()

    def package(self):
        with self._build_env().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """meson install rewrites DT_RUNPATH in the installed libraries,
        which invalidates the link-time .codesign section. The OHOS musl
        loader refuses to map such an ELF ("Error loading shared library
        libnvme.so.1"), so every installed shared object has to be
        stripped of the stale signature and re-signed (atk precedent).
        Verified: unsigned install output cannot be dlopen'd at all,
        re-signed output loads and relocates cleanly."""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(
                    f"Required OHOS signing tool not found: {tool}"
                )
        import glob as _glob
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "*.so"),
            os.path.join(self.package_folder, "lib", "*.so.*"),
        ):
            targets.extend(_glob.glob(pattern))
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["nvme", "nvme-mi"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["json-c::json-c"]
        self.cpp_info.set_property("cmake_file_name", "libnvme")
        self.cpp_info.set_property("cmake_target_name", "libnvme::libnvme")
        self.cpp_info.set_property("pkg_config_name", "libnvme")
        # openssl (with_tls=True) is statically linked into libnvme with
        # PIC and does not need to propagate to consumers at link time.

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _fix_jsonc_pc_include_subdir(self):
        """libnvme sources include <json.h>, while the json-c Conan package
        installs its headers into include/json-c/. The PkgConfigDeps
        generated json-c.pc only carries -I${includedir}; add the json-c
        subdirectory so `dependency('json-c')` resolves correctly."""
        pc_file = os.path.join(self.generators_folder, "json-c.pc")
        if not os.path.isfile(pc_file):
            return
        with open(pc_file, encoding="utf-8") as handle:
            content = handle.read()
        match = re.search(r"(?m)^Cflags:\s*(.*)$", content)
        if not match or "json-c" in match.group(1):
            return
        new_flags = match.group(1).rstrip() + ' -I"${includedir}/json-c"'
        content = content[:match.start(1)] + new_flags + content[match.end(1):]
        with open(pc_file, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _inject_meson_tools(self):
        """meson needs explicit ar/ranlib/pkg-config entries in the machine
        files: the OHOS toolchain directory (llvm-ar) is not always on the
        default PATH and conan may only know bare tool names."""
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (
                bindir,
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin",
            ):
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
            pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
            if not pkg_config or not os.path.isfile(str(pkg_config)):
                pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            if ar and os.path.isabs(str(ar)):
                content = self._set_machine_binary(content, "ar", ar)
            if ranlib and os.path.isabs(str(ranlib)):
                content = self._set_machine_binary(content, "ranlib", ranlib)
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                content = content.replace(
                    "[binaries]\n", f"[binaries]\npkg-config = '{pkg_config}'\n", 1
                )
            with open(machine_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    @staticmethod
    def _set_machine_binary(content, key, value):
        pattern = re.compile(rf"(?m)^{re.escape(key)}\s*=.*$")
        line = f"{key} = '{value}'"
        if pattern.search(content):
            return pattern.sub(line, content, count=1)
        return content.replace("[binaries]\n", f"[binaries]\n{line}\n", 1)

    def _ensure_meson_available(self):
        # CI workers are not guaranteed to ship meson; install it on demand
        # (babl precedent). _build_env() puts ~/.local/bin on PATH so the
        # freshly installed launcher is found by the Meson helper.
        if not shutil.which("meson"):
            self.output.warning("meson not found on PATH, installing via pip")
            self.run(f"{sys.executable} -m pip install --user meson")

    def _build_env(self):
        """Writable TMPDIR (OHOS /tmp is read-only) + tool discovery paths
        + SDK runtime library paths (libc++_shared.so for the optional C++
        sanity check and the cpp test binaries)."""
        env = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        local_bin = os.path.expanduser("~/.local/bin")
        if os.path.isdir(local_bin):
            env.prepend_path("PATH", local_bin)
        for sdk_lib in (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
            "/system/lib64",
        ):
            if os.path.isdir(sdk_lib):
                env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    # meson test marks these targets with should_fail: true; a non-zero
    # exit status for them is the expected outcome (EXPECTEDFAIL).
    _SHOULD_FAIL_TESTS = frozenset((
        "NBFT-bad-oldspec",
        "NBFT-random-noise",
    ))

    def _run_upstream_tests(self):
        """Run the upstream meson test suite. On the OHOS build host this
        executes for real (native build): 38 registered targets covering
        MI, ioctl mocking, NBFT table parsing, sysfs/config/tree dumping,
        psk/TLS key handling, C++ include hygiene and kernel-doc checks.
        meson test exits non-zero on any unexpected failure, so the exit
        code is the authoritative pass/fail gate."""
        cmd = (
            "meson test -C {build} --print-errorlogs "
            "--num-processes 2 --timeout-multiplier 4"
        ).format(build=self.build_folder)
        self.output.info(f"=== upstream test suite: {cmd}")
        self.run(cmd)
        self._report_upstream_results()

    def _report_upstream_results(self):
        """Parse meson-logs/testlog.txt (the machine-readable log: one
        'test:' + 'result:' pair per target) and emit the test summary.
        Exit status 0 -> OK; non-zero for a should_fail target ->
        EXPECTEDFAIL; anything else would already have failed meson test.
        """
        log_path = os.path.join(self.build_folder, "meson-logs", "testlog.txt")
        if not os.path.isfile(log_path):
            self.output.warning("meson testlog.txt not found; skipping report")
            return
        entry = re.compile(
            r"(?ms)^test:\s+(?P<name>\S+)\s*$.*?^result:\s+(?P<result>.*?)\s*$"
        )
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        counts = {"OK": 0, "EXPECTEDFAIL": 0, "FAIL": 0, "SKIP": 0,
                  "ERROR": 0, "TIMEOUT": 0}
        for match in entry.finditer(content):
            name = match.group("name").split(":")[-1]
            result = match.group("result")
            if result.startswith("exit status 0") or result.startswith("OK"):
                counts["OK"] += 1
            elif result.startswith("SKIP"):
                counts["SKIP"] += 1
            elif name in self._SHOULD_FAIL_TESTS:
                counts["EXPECTEDFAIL"] += 1
            elif result.startswith("TIMEOUT"):
                counts["TIMEOUT"] += 1
            else:
                counts["FAIL"] += 1
        executed = sum(counts.values())
        passed = counts["OK"] + counts["EXPECTEDFAIL"]
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps({
                "status": "passed" if counts["FAIL"] == 0 and executed > 0 else "failed",
                "framework": "meson",
                "command": "meson test",
                "discovered": executed,
                "executed": executed,
                "passed": passed,
                "failed": counts["FAIL"],
                "skipped": counts["SKIP"],
            })
        )
        if counts["FAIL"] or counts["ERROR"] or counts["TIMEOUT"] or executed == 0:
            raise ConanException(
                "upstream meson tests failed: " + json.dumps(counts)
            )
