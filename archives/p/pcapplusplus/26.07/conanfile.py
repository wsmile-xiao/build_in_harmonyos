#!/usr/bin/env python3
"""Conan recipe for pcapplusplus 26.07 — multiplatform C++ library for capturing,
parsing and crafting of network packets.

Upstream: https://github.com/seladb/PcapPlusPlus (MIT).

OHOS adaptation notes
---------------------
- E092: CMake ships no `Platform/HarmonyOS.cmake`, so the auto-detected target
  system (HarmonyOS) lands in the generic branch and `if(UNIX)` is false. Upstream
  gates the Linux-only `Pcap++/src/LinuxNicInformationSocket.cpp` behind `if(UNIX)`,
  so without this the translation unit is silently dropped and the installed
  libPcap++ misses `NicInformationSocket`. generate() forces `CMAKE_SYSTEM_NAME=Linux`
  (the same trick already used by libtins/4.5) so the Linux branch is compiled.
- libpcap: upstream consumes libpcap through its own `cmake/modules/FindPCAP.cmake`
  (`find_path`/`find_library`), not through a CMake config package. generate() feeds
  the Conan `libpcap` package `include/` + `lib/libpcap.a` directly into the
  `PCAP_INCLUDE_DIR` / `PCAP_LIBRARY` cache variables. No upstream file is patched.
- Upstream tests: PcapPlusPlus uses its own header-only PTF framework (no gtest),
  built as two binaries under `Tests/`. `Packet++Test` is fully offline (parses
  `PacketExamples/*.dat`), `Pcap++Test` is run with `-n` so only the `no_network`
  tagged cases execute. build() runs both and reports through
  `HMBS_UPSTREAM_TEST_RESULT`.
- OHOS: `/system/bin/sh` (mksh) cannot load dynamically linked binaries, so the test
  executables are launched through `CONFIG_SHELL` (hnp bash); every test binary is
  ELF self-signed with `binary-sign-tool` first, otherwise the kernel refuses to
  exec it. `LD_LIBRARY_PATH` injected by the OHOS build env is dropped for the host
  signing tools (they are linked against the system libc++).
"""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm


class PcapplusplusConan(ConanFile):
    name = "pcapplusplus"
    version = "26.07"
    description = ("Multiplatform C++ library for capturing, parsing and crafting of "
                   "network packets")
    license = "MIT"
    homepage = "https://pcapplusplus.github.io/"
    url = "https://github.com/seladb/PcapPlusPlus"
    topics = ("networking", "packet", "pcap", "sniffing", "pdu")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def requirements(self):
        # libpcap is a hard dependency for the Pcap++ project (PCAPPP_USE_PCAP=ON).
        self.requires("libpcap/1.10.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def _libpcap_file(dep):
        """Absolute path of the libpcap library inside the Conan package."""
        for libdir in dep.cpp_info.libdirs:
            for name in ("pcap", "wpcap"):
                for suffix in (".so", ".a", ".dylib"):
                    candidate = os.path.join(dep.package_folder, libdir,
                                             "lib" + name + suffix)
                    if os.path.isfile(candidate):
                        return candidate
        # Fall back to the link name; CMake will resolve it through the libdir.
        return os.path.join(dep.package_folder, dep.cpp_info.libdirs[0], "libpcap.a")

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: no HarmonyOS platform module in CMake — force the upstream Linux branch.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["PCAPPP_BUILD_PCAPPP"] = True
        tc.variables["PCAPPP_BUILD_EXAMPLES"] = False
        tc.variables["PCAPPP_BUILD_TESTS"] = True
        tc.variables["PCAPPP_USE_PCAP"] = True
        tc.variables["PCAPPP_INSTALL"] = True
        # Feed the Conan libpcap package to the upstream FindPCAP.cmake module.
        dep = self.dependencies["libpcap"]
        tc.variables["PCAP_INCLUDE_DIR"] = os.path.join(dep.package_folder, "include")
        tc.variables["PCAP_LIBRARY"] = self._libpcap_file(dep)
        tc.generate()
        VirtualRunEnv(self).generate()

    # ── build ──────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _test_binaries(self):
        """Locate the two upstream PTF test executables in the build tree."""
        found = {}
        for name in ("Packet++Test", "Pcap++Test"):
            for candidate in glob.glob(os.path.join(self.build_folder, "**", name),
                                       recursive=True):
                if os.path.isfile(candidate) and not os.path.islink(candidate):
                    found[name] = candidate
                    break
        return found

    @staticmethod
    def _ohos_tool(name, fallback):
        found = shutil.which(name)
        return found or (fallback if os.path.isfile(fallback) else None)

    @staticmethod
    def _host_tool_env():
        """Environment for host tools (signer).

        The OHOS build environment prepends the SDK libc++ directory to
        LD_LIBRARY_PATH; binary-sign-tool is a host binary linked against the
        system libc++ and fails to relocate in that environment.
        """
        env = dict(os.environ)
        env.pop("LD_LIBRARY_PATH", None)
        return env

    def _sign_elf(self, path):
        signer = self._ohos_tool("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
        readelf = self._ohos_tool("llvm-readelf", "/data/service/hnp/bin/llvm-readelf")
        if not signer or not readelf:
            raise ConanException("OHOS test execution requires binary-sign-tool and llvm-readelf")
        env = self._host_tool_env()
        signed = path + ".signed"
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed,
                        "-selfSign", "1"], check=True, timeout=300, env=env)
        sections = subprocess.run([readelf, "-SW", signed], check=True,
                                  capture_output=True, text=True, timeout=120,
                                  env=env).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"invalid .codesign section count for {path}")
        os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(signed, path)

    def _run_one(self, name, binary, extra_args):
        """Run one upstream test binary and return its parsed counters."""
        if not os.path.isfile(binary):
            raise ConanException(f"upstream test binary not built: {binary}")
        if self.settings.os == "OHOS":
            self._sign_elf(binary)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        runenv = os.path.join(self.generators_folder, "conanrun.sh")
        exe = "./" + os.path.basename(binary)
        log_path = os.path.join(self.build_folder, f"{name.replace('+', 'p')}.log")
        args = (" " + " ".join(extra_args)) if extra_args else ""
        cmd = (f'. "{runenv}" 2>/dev/null; {exe}{args} > "{log_path}" 2>&1')
        proc = subprocess.run([bash, "-c", cmd], cwd=os.path.dirname(binary),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=7200)
        output = ""
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                output = handle.read()
        self.output.info(f"=== {name} output tail ===")
        self.output.info("\n".join(output.splitlines()[-12:]))
        match = re.search(r"Test cases:\s*(\d+),\s*Passed:\s*(\d+),\s*Failed:\s*(\d+),"
                          r"\s*Skipped:\s*(\d+)", output)
        if not match:
            raise ConanException(
                f"could not parse {name} summary line (rc={proc.returncode}); "
                f"tail:\n" + output[-2000:])
        total, passed, failed, skipped = (int(g) for g in match.groups())
        return {
            "binary": exe,
            "discovered": total,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }

    def _run_upstream_tests(self):
        binaries = self._test_binaries()
        missing = {"Packet++Test", "Pcap++Test"} - set(binaries)
        if missing:
            raise ConanException(f"upstream test binaries not built (PCAPPP_BUILD_TESTS=ON): "
                                 f"missing {sorted(missing)}")
        runs = [
            # Packet++Test is fully offline: it parses the PacketExamples/*.dat fixtures.
            self._run_one("Packet++Test", binaries["Packet++Test"], []),
            # Pcap++Test -n runs only the `no_network` tagged cases. `live_device` is
            # excluded on top of that: enumerating live devices needs a readable
            # /sys/class/net and the SIOCETHTOOL(ETHTOOL_GLINK) ioctl, both denied in
            # the containerised build sandbox, so libpcap's pcap_findalldevs fails with
            # EPERM and the two live_device cases can never pass there. See notes.md.
            self._run_one("Pcap++Test", binaries["Pcap++Test"], ["-n", "-x", "live_device"]),
        ]
        total = sum(r["discovered"] for r in runs)
        passed = sum(r["passed"] for r in runs)
        failed = sum(r["failed"] for r in runs)
        skipped = sum(r["skipped"] for r in runs)
        executed = passed + failed
        # Skipped cases are legitimate (tags for features this build does not enable,
        # plus the two sandbox-limited live_device cases); only failures make it red.
        status = "passed" if total > 0 and executed > 0 and failed == 0 else "failed"
        marker = {
            "status": status,
            "framework": "PcapPlusPlus PTF",
            "command": "Packet++Test; Pcap++Test -n -x live_device",
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "binaries": len(runs),
            "details": runs,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        with open(os.path.join(self.build_folder, "upstream_test_result.json"), "w",
                  encoding="utf-8") as handle:
            json.dump(marker, handle, ensure_ascii=False, indent=2)
        if status != "passed":
            raise ConanException(
                f"upstream tests failed: {passed}/{total} passed, {failed} failed, "
                f"{skipped} skipped")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        for name in ("upstream_test_result.json",
                     "PacketppTest.log", "PcapppTest.log"):
            source = os.path.join(self.build_folder, name)
            if os.path.isfile(source):
                copy(self, name, src=self.build_folder,
                     dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PcapPlusPlus")
        self.cpp_info.set_property("cmake_target_name", "PcapPlusPlus::PcapPlusPlus")
        # Public headers are installed flat into include/pcapplusplus and include
        # each other by base name, so that directory must be on the include path.
        self.cpp_info.includedirs = ["include/pcapplusplus", "include"]
        self.cpp_info.libs = ["Pcap++", "Packet++", "Common++"]
        if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs.append("pthread")
