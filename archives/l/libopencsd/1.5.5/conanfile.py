#!/usr/bin/env python3
"""Conan recipe for libopencsd 1.5.5 — ARM CoreSight trace decode library (OpenCSD).

HarmonyOS adaptation:
- Custom Makefile build (decoder/build/linux/makefile + unix_common/makefile.common),
  no autotools/cmake. Toolchain is injected through make command-line variables
  MASTER_CC / MASTER_CXX / MASTER_LINKER / MASTER_LIB (R33: values come from the
  Conan conf tools.build:compiler_executables, never the raw shell ${CC}).
- OHOS: test executables produced by the upstream makefile must be code-signed
  (binary-sign-tool) before they can exec on the HarmonyOS kernel; the packaged
  shared libraries need no signature to be loaded.
- Upstream test suite (61 command-line scenarios declared by
  run_pkt_decode_tests.bash / run_pkt_decode_tests-ete.bash / run_capi_test.bash)
  runs inside build() through a driver that executes each scenario and checks rc.
- macOS local verification: ld64 does not accept -soname / -Wl,-z,defs, so the
  local build uses -install_name and drops PLATFORM_LDFLAGS; OHOS/CI keep the
  upstream link flags (lld accepts both).
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibopencsdConan(ConanFile):
    name = "libopencsd"
    version = "1.5.5"
    package_type = "library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Linaro/OpenCSD"
    url = "https://github.com/Linaro/OpenCSD"
    description = "OpenCSD: ARM CoreSight trace decode library (ETMv3/ETMv4/ETE/PTM/STM) with C and C++ APIs"
    topics = ("coresight", "trace", "decode", "etm", "stm")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"
    short_paths = True

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Macos"):
            raise ConanInvalidConfiguration(
                "libopencsd supports Linux / OHOS / macOS only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ---------------------------------------------------------------- build

    def _toolchain(self):
        """Resolve CC/CXX/AR from Conan conf (R33); never the shell ${CC}."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or shutil.which("clang") or "clang"
        cxx = compilers.get("cpp") or shutil.which("clang++") or "clang++"
        ar = (compilers.get("ar") or shutil.which("llvm-ar")
              or shutil.which("ar") or "ar")
        return cc, cxx, ar

    def _build_make_command(self):
        cc, cxx, ar = self._toolchain()
        cmd = (f"make MASTER_CC={cc} MASTER_CXX={cxx} "
               f"MASTER_LINKER={cxx} MASTER_LIB={ar} -j1")
        if self.settings.os == "Macos":
            # ld64 does not understand -soname / -Wl,-z,defs
            cmd += " SONAME_FLAG=-install_name PLATFORM_LDFLAGS="
        return cmd

    def build(self):
        apply_conandata_patches(self)
        make_dir = os.path.join(self.source_folder, "decoder", "build", "linux")
        self.run(self._build_make_command(), cwd=make_dir)
        if self.settings.os == "OHOS":
            self._sign_test_binaries()
        self._run_upstream_tests()

    # ------------------------------------------------- OHOS code signing

    def _sign_tools(self):
        fixed = "/data/service/hnp/bin"
        sign = shutil.which("binary-sign-tool") or os.path.join(fixed, "binary-sign-tool")
        objcopy = shutil.which("llvm-objcopy") or os.path.join(fixed, "llvm-objcopy")
        if not os.path.exists(sign) or not os.path.exists(objcopy):
            raise ConanInvalidConfiguration(
                "OHOS build requires binary-sign-tool and llvm-objcopy "
                "(expected under /data/service/hnp/bin or PATH)")
        return sign, objcopy

    def _sign_test_binaries(self):
        """HarmonyOS kernel only execs code-signed ELF; sign upstream test binaries."""
        sign, objcopy = self._sign_tools()
        bindir = os.path.join(self.source_folder, "decoder", "tests", "bin", "builddir")
        for name in ("trc_pkt_lister", "c_api_pkt_print_test", "frame-demux-test",
                     "mem-buffer-eg", "mem-acc-test", "ocsd-perr", "echo_test_dcd"):
            path = os.path.join(bindir, name)
            if not os.path.exists(path):
                continue
            self.run(f"{objcopy} --remove-section .codesign {path}",
                     quiet=True)
            self.run(f"{sign} sign -inFile {path} -outFile {path} -selfSign 1",
                     quiet=True)
        self.output.info("OHOS: test binaries code-signed with binary-sign-tool")

    # ------------------------------------------- upstream test suite (R51)

    def _run_upstream_tests(self):
        """Execute the 61 scenarios declared by the upstream bash scripts.

        Counting basis (unified): one scenario per upstream script invocation
        line — run_pkt_decode_tests.bash (24) + run_pkt_decode_tests-ete.bash
        (36) + run_capi_test.bash (1) = 61. Each scenario's pass criterion is
        rc==0, same as the upstream scripts' "Done : Return N" checks.
        """
        tests_dir = os.path.join(self.source_folder, "decoder", "tests")
        snap = os.path.join(tests_dir, "snapshots")
        bin_dir = os.path.join(tests_dir, "bin", "builddir")
        binp = bin_dir + os.sep
        logdir = os.path.join(self.build_folder, "ocsd-test-logs")
        os.makedirs(logdir, exist_ok=True)

        scenarios = []

        def add(tag, cmd, env=None):
            scenarios.append((tag, cmd, env or {}))

        # -- run_pkt_decode_tests.bash: 15 snapshot decode scenarios ---------
        decode_dirs = [
            "juno-ret-stck", "a57_single_step", "bugfix-exact-match",
            "juno-uname-001", "juno-uname-002", "juno_r1_1",
            "tc2-ptm-rstk-t32", "trace_cov_a15", "stm_only", "stm_only-2",
            "stm_only-juno", "stm-issue-27", "TC2", "Snowball",
            "test-file-mem-offsets",
        ]
        for d in decode_dirs:
            add(f"decode:{d}", [binp + "trc_pkt_lister", "-ss_dir",
                                os.path.join(snap, d), "-decode",
                                "-no_time_print",
                                "-logfilename", os.path.join(logdir, f"{d}.ppl")])
        # -- range-limit / bad-opcode / init-short-addr / tpiu ---------------
        add("decode:juno_r1_1-rangelimit",
            [binp + "trc_pkt_lister", "-ss_dir", os.path.join(snap, "juno_r1_1"),
             "-decode", "-no_time_print",
             "-logfilename", os.path.join(logdir, "rangelimit.ppl")],
            {"OPENCSD_INSTR_RANGE_LIMIT": "100"})
        add("decode:juno_r1_1-badopcode-env",
            [binp + "trc_pkt_lister", "-ss_dir", os.path.join(snap, "juno_r1_1"),
             "-decode", "-no_time_print",
             "-logfilename", os.path.join(logdir, "badopcode-env.ppl")],
            {"OPENCSD_ERR_ON_AA64_BAD_OPCODE": "1"})
        add("decode:juno_r1_1-badopcode-flag",
            [binp + "trc_pkt_lister", "-ss_dir", os.path.join(snap, "juno_r1_1"),
             "-decode", "-no_time_print", "-aa64_opcode_chk",
             "-logfilename", os.path.join(logdir, "badopcode-flag.ppl")])
        add("decode:init-short-addr",
            [binp + "trc_pkt_lister", "-ss_dir", os.path.join(snap, "init-short-addr"),
             "-pkt_mon", "-no_time_print",
             "-logfilename", os.path.join(logdir, "init-short-addr.ppl")])
        add("decode:a55-test-tpiu",
            [binp + "trc_pkt_lister", "-ss_dir", os.path.join(snap, "a55-test-tpiu"),
             "-dstream_format", "-o_raw_packed", "-o_raw_unpacked",
             "-no_time_print", "-logfilename", os.path.join(logdir, "tpiu.ppl")])
        # -- C-API / frame demux / memory accessor ---------------------------
        add("capi:c_api_pkt_print_test", [binp + "c_api_pkt_print_test",
                                          "-ss_path", snap, "-decode"])
        add("frame:frame-demux-test", [binp + "frame-demux-test"])
        add("mem:mem-buffer-eg-buffer", [binp + "mem-buffer-eg", "-logfile",
                                         "-ss_path", "./snapshots", "-noprint"])
        add("mem:mem-buffer-eg-callback", [binp + "mem-buffer-eg", "-logfile",
                                           "-ss_path", "./snapshots", "-noprint",
                                           "-callback"])

        # -- run_pkt_decode_tests-ete.bash: 26 + 3 + 7 = 36 ------------------
        ete_dirs = [
            "001-ack_test", "002-ack_test_scr", "ete-bc-instr", "ete_ip",
            "ete-ite-instr", "ete_mem", "ete_spec_1", "ete_spec_2", "ete_spec_3",
            "ete_wfet", "event_test", "infrastructure", "pauth_lr", "pauth_lr_Rm",
            "q_elem", "rme_test", "s_9001", "src_addr", "ss_ib_el1ns",
            "tme_simple", "tme_tcancel", "tme_test", "trace_file_cid_vmid",
            "trace_file_vmid", "ts_bit64_set", "ts_marker",
        ]
        for d in ete_dirs:
            add(f"ete-decode:{d}", [binp + "trc_pkt_lister", "-ss_dir",
                                    os.path.join(snap, d), "-decode",
                                    "-no_time_print",
                                    "-logfilename", os.path.join(logdir, f"{d}.ppl")])
        for d in ("002-ack_test_scr", "ete_ip", "src_addr"):
            add(f"ete-srcaddr:{d}", [binp + "trc_pkt_lister", "-ss_dir",
                                     os.path.join(snap, d), "-decode",
                                     "-no_time_print", "-src_addr_n",
                                     "-logfilename", os.path.join(logdir, f"{d}-sa.ppl")])
        for d in ("ss_ib_el1ns", "ete-ite-instr", "pauth_lr", "pauth_lr_Rm",
                  "q_elem", "rme_test", "s_9001"):
            add(f"ete-multisess:{d}", [binp + "trc_pkt_lister", "-ss_dir",
                                       os.path.join(snap, d), "-decode",
                                       "-no_time_print", "-multi_session",
                                       "-logfilename", os.path.join(logdir, f"{d}-ms.ppl")])

        # -- run_capi_test.bash: 1 scenario (same C-API command) -------------
        add("capi:run_capi_test.bash", [binp + "c_api_pkt_print_test",
                                        "-ss_path", snap, "-decode"])

        libenv_key = ("DYLD_LIBRARY_PATH" if self.settings.os == "Macos"
                      else "LD_LIBRARY_PATH")
        results, failed = {}, []
        for tag, cmd, extra_env in scenarios:
            env = dict(os.environ)
            env[libenv_key] = bin_dir
            env.update(extra_env)
            try:
                proc = subprocess.run(cmd, cwd=tests_dir, env=env,
                                      stdout=subprocess.DEVNULL,
                                      stderr=subprocess.PIPE)
                ok = proc.returncode == 0
            except Exception as exc:  # noqa: BLE001
                ok, proc = False, None
                self.output.warning(f"scenario {tag}: {exc}")
            results[tag] = {"ok": ok, "rc": proc.returncode if proc else "ERR"}
            if not ok:
                failed.append(tag)
                self.output.warning(f"upstream test FAILED: {tag} rc={results[tag]['rc']}")
        total, passed = len(scenarios), len(scenarios) - len(failed)
        report = {
            "status": "passed" if not failed else "failed",
            "framework": "upstream bash test scripts (custom makefile tests)",
            "counting": "one scenario per upstream script invocation line: "
                        "run_pkt_decode_tests.bash(24) + "
                        "run_pkt_decode_tests-ete.bash(36) + "
                        "run_capi_test.bash(1) = 61; pass = rc 0",
            "discovered": total, "executed": total, "passed": passed,
            "failed": len(failed), "skipped": 0, "failed_scenarios": failed,
            "results": results,
        }
        report_path = os.path.join(self.build_folder, "ocsd-upstream-tests.json")
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        self.output.info(f"upstream tests: {passed}/{total} passed "
                         f"(report: {report_path})")
        if failed:
            raise ConanInvalidConfiguration(
                f"upstream tests failed: {failed}")

    # -------------------------------------------------------------- package

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        lib_src = os.path.join(self.source_folder, "decoder", "lib", "builddir")
        lib_dst = os.path.join(self.package_folder, "lib")
        # Copy versioned shared objects and rebuild the .so / .so.1 symlink
        # chain (copy() dereferences symlinks, so the links are recreated).
        for lib in ("libopencsd.so.1.5.5", "libopencsd_c_api.so.1.5.5"):
            copy(self, lib, src=lib_src, dst=lib_dst)
            base = lib[:-len(".1.5.5")]          # e.g. "libopencsd.so"
            so1 = base + ".1"                    # e.g. "libopencsd.so.1"
            os.symlink(lib, os.path.join(lib_dst, so1))
            os.symlink(so1, os.path.join(lib_dst, base))
        copy(self, "*.a", src=lib_src, dst=lib_dst)
        inc_src = os.path.join(self.source_folder, "decoder", "include")
        copy(self, "opencsd/**", src=inc_src,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["opencsd_c_api", "opencsd"]
        if self.settings.os == "Linux" and self.settings.compiler in ("gcc", "clang"):
            self.cpp_info.system_libs = ["m"]
