#!/usr/bin/env python3
"""Conan test_package for courier-unicode 2.6.0.

Consumer test builds test_courier_unicode.c against the packaged
courier-unicode library and runs it. The C program contains 14 real API
assertions (case mapping, HTML entities, character classes, widths,
general categories, charset conversion). Any failure exits non-zero and
fails `conan create`.
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CourierUnicodeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_ohos_compiler(self):
        """Prefer profile CC/CXX when present, else PATH clang (OHOS).

        Mirrors the main recipe _ensure_ohos_compiler: healthy CI workers
        keep the profile /data/service/hnp/bin/clang{,++} untouched;
        preflight runners where that path is absent fall back to PATH
        clang/clang++ (file/5.48.1 test_package precedent, but with an
        existence probe instead of a blind bare-name override).
        """
        import shutil

        conf = {}
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        conf_cc = conf.get("c", "") if isinstance(conf, dict) else ""
        conf_cxx = conf.get("cpp", "") if isinstance(conf, dict) else ""
        cc = conf_cc if conf_cc and os.path.isfile(conf_cc) else ""
        cxx = conf_cxx if conf_cxx and os.path.isfile(conf_cxx) else ""
        if not cc:
            cc = shutil.which("clang") or "clang"
        if not cxx:
            if cc and os.path.sep in cc:
                sib = os.path.join(os.path.dirname(cc), "clang++")
                if os.path.isfile(sib):
                    cxx = sib
            if not cxx:
                cxx = shutil.which("clang++") or "clang++"
        return cc, cxx, conf_cc, conf_cxx

    def build(self):
        if self.settings.os in ("OHOS",):
            cc, cxx, conf_cc, conf_cxx = self._resolve_ohos_compiler()
            if cc != conf_cc or cxx != conf_cxx:
                self.output.info(
                    "OHOS test_package compiler fallback: CC=%s CXX=%s "
                    "(profile %r absent)" % (cc, cxx, conf_cc))
            os.environ["CC"] = cc
            os.environ["CXX"] = cxx
            # Patch the aggregated build env so self.run time sees the
            # fallback even when the profile [buildenv] wins over
            # os.environ (main-recipe _override_conan_buildenv precedent).
            try:
                build_sh = os.path.join(self.generators_folder,
                                        "conanbuild.sh")
                if os.path.isfile(build_sh):
                    with open(build_sh, encoding="utf-8",
                              errors="surrogateescape") as handle:
                        content = handle.read()
                    orig = content
                    fix = ('\n# Override non-existent profile compiler\n'
                           'export CC="%s"\n'
                           'export CXX="%s"\n' % (cc, cxx))
                    if "Override non-existent profile compiler" not in content:
                        if not content.endswith("\n"):
                            content += "\n"
                        content += fix
                    if content != orig:
                        with open(build_sh, "w", encoding="utf-8",
                                  errors="surrogateescape") as handle:
                            handle.write(content)
            except OSError:
                pass
            # Patch the generated toolchain file: it bakes the profile
            # compiler path in (file/5.48.1 precedent). Replace only paths
            # that do not exist so healthy workers are untouched.
            try:
                toolchain = os.path.join(self.generators_folder,
                                         "conan_toolchain.cmake")
                if os.path.isfile(toolchain):
                    with open(toolchain, encoding="utf-8",
                              errors="surrogateescape") as handle:
                        tc_content = handle.read()
                    orig_tc = tc_content
                    for bad, good in ((conf_cc, cc), (conf_cxx, cxx)):
                        if bad and bad != good and bad in tc_content:
                            if not os.path.isfile(bad):
                                tc_content = tc_content.replace(bad, good)
                    if tc_content != orig_tc:
                        with open(toolchain, "w", encoding="utf-8",
                                  errors="surrogateescape") as handle:
                            handle.write(tc_content)
                        self.output.info(
                            "OHOS patch applied (test_package toolchain "
                            "compiler fallback)")
            except OSError:
                pass
            cmake = CMake(self)
            cmake.configure(variables={
                "CMAKE_C_COMPILER": cc,
                "CMAKE_CXX_COMPILER": cxx,
            })
            cmake.build()
        else:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if can_run(self):
            exe = os.path.join(self.cpp.build.bindir, "test_courier_unicode")
            self.run('"{}"'.format(exe), env="conanrun")
            marker = {
                "executed": True,
                "passed": True,
                "command": '"{}"'.format(exe),
                "discovered": 14,
                "passedCount": 14,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
            # Re-emit the upstream evidence persisted by build()/package()
            # on EVERY run: conan skips build() on a cached binary
            # ("Already installed!"), so the build-time marker alone
            # disappears on cache-hit rounds (abuild-sudo precedent).
            try:
                dep = self.dependencies["courier-unicode"]
                result_path = os.path.join(
                    dep.package_folder, "res", "upstream_test_result.json")
                if os.path.isfile(result_path):
                    with open(result_path, encoding="utf-8") as handle:
                        upstream = json.load(handle)
                    self.output.info(
                        "HMBS_UPSTREAM_TEST_RESULT="
                        + json.dumps(upstream, ensure_ascii=False))
                else:
                    self.output.warning(
                        "upstream_test_result.json not found in package "
                        "(%s); upstream evidence missing" % result_path)
            except Exception as exc:
                self.output.warning(
                    "could not re-emit upstream test result: %s" % exc)
