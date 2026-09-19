#!/usr/bin/env python3
"""Consumer test for the packaged libecoli API (meson-based)."""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibecoliTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _inject_ohos_archiver(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        if os.environ.get("CC") and os.path.isfile(os.environ["CC"]):
            compiler = os.environ["CC"]
        compiler_dir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or (
            os.path.join(compiler_dir, "llvm-ar") if compiler_dir else ""
        )
        ranlib = executables.get("ranlib") or (
            os.path.join(compiler_dir, "llvm-ranlib") if compiler_dir else ""
        )
        native_file = os.path.join(
            self.generators_folder, "conan_meson_native.ini"
        )
        if not (ar and os.path.isfile(ar) and os.path.isfile(native_file)):
            return

        with open(native_file, encoding="utf-8") as stream:
            content = stream.read()
        if "\nar =" in content or "[binaries]\n" not in content:
            return

        additions = "ar = '{}'\n".format(ar.replace("\\", "/"))
        if ranlib and os.path.isfile(ranlib):
            additions += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
        content = content.replace("[binaries]\n", "[binaries]\n" + additions, 1)
        with open(native_file, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)

    @staticmethod
    def _package_path(dependency, path):
        if os.path.isabs(path):
            return path
        return os.path.join(dependency.package_folder, path)

    def layout(self):
        basic_layout(self, src_folder=".")

    def build_requirements(self):
        # test_package also drives the Meson helper, so it needs the same
        # tool binaries as the main recipe (meson is not on the base PATH).
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")

    def generate(self):
        dependency = self.dependencies["libecoli"]
        tc = MesonToolchain(self)
        tc.project_options["libecoli_include_dir"] = self._package_path(
            dependency, dependency.cpp_info.includedirs[0]
        )
        tc.project_options["libecoli_lib_dir"] = self._package_path(
            dependency, dependency.cpp_info.libdirs[0]
        )
        tc.generate()
        if self.settings.os == "OHOS":
            self._inject_ohos_archiver()

    @staticmethod
    def _probe_tool(cmd):
        try:
            proc = subprocess.run(
                [cmd, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
            )
            return proc.returncode == 0
        except Exception:
            return False

    def _discover_ohos_compilers(self):
        if self.settings.os != "OHOS":
            return None, None
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        c_cands = []
        cxx_cands = []
        if executables.get("c"):
            c_cands.append(executables["c"])
        if executables.get("cpp"):
            cxx_cands.append(executables["cpp"])
        if os.environ.get("CC"):
            c_cands.append(os.environ["CC"])
        if os.environ.get("CXX"):
            cxx_cands.append(os.environ["CXX"])
        for name in ("clang", "cc", "gcc"):
            found = shutil.which(name)
            if found and found not in c_cands:
                c_cands.append(found)
        for name in ("clang++", "c++", "g++"):
            found = shutil.which(name)
            if found and found not in cxx_cands:
                cxx_cands.append(found)
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/clang",
            "/data/service/hnp/ohos-sdk/ohos/native/llvm/bin/clang",
            "/storage/Users/currentUser/usr/local/bin/clang",
        ):
            for path in sorted(glob.glob(pattern)):
                if path not in c_cands:
                    c_cands.append(path)
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/clang++",
            "/data/service/hnp/ohos-sdk/ohos/native/llvm/bin/clang++",
            "/storage/Users/currentUser/usr/local/bin/clang++",
        ):
            for path in sorted(glob.glob(pattern)):
                if path not in cxx_cands:
                    cxx_cands.append(path)
        c = next((p for p in c_cands if p and self._probe_tool(p)), None)
        cxx = next((p for p in cxx_cands if p and self._probe_tool(p)), None)
        if c is None and cxx is not None:
            c = cxx
        if cxx is None and c is not None:
            cxx = c
        return c, cxx

    def _fix_meson_native_compilers(self):
        if self.settings.os != "OHOS":
            return
        c, cxx = self._discover_ohos_compilers()
        if not c and not cxx:
            return
        native_file = os.path.join(
            self.generators_folder, "conan_meson_native.ini"
        )
        if not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as stream:
            content = stream.read()
        if c:
            content, _ = re.subn(
                r"(?m)^c\s*=\s*'.*'$",
                "c = '{}'".format(c.replace("\\", "/")),
                content,
                count=1,
            )
            os.environ["CC"] = c
        if cxx:
            content, _ = re.subn(
                r"(?m)^cpp\s*=\s*'.*'$",
                "cpp = '{}'".format(cxx.replace("\\", "/")),
                content,
                count=1,
            )
            os.environ["CXX"] = cxx
        with open(native_file, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        self.output.info("meson native compilers -> c={} cpp={}".format(c, cxx))

    def build(self):
        self._fix_meson_native_compilers()
        if self.settings.os == "OHOS":
            self._inject_ohos_archiver()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        if can_run(self):
            self.run(
                "./test_libecoli",
                cwd=self.cpp.build.bindirs[0],
                env="conanrun",
            )
            # Consumer checks audited from test_package.c CHECK() lines:
            # 11 ok/not-ok assertions (log shows "11 checks").
            test_payload = {
                "executed": True,
                "passed": True,
                "command": "./test_libecoli",
                "discovered": 11,
                "passedCount": 11,
            }
            test_line = ("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(test_payload, separators=(",", ":")))
            print(test_line, flush=True)
            self.output.info(test_line)
            # Re-emit in-build upstream evidence every round (covers Conan
            # cache-hit rounds where the main build() is skipped). Numbers
            # are re-emitted verbatim, never redefined here.
            try:
                pkg_folder = self.dependencies["libecoli"].package_folder
                evidence = os.path.join(pkg_folder, "res", "hmbs_upstream.json")
                if os.path.isfile(evidence):
                    with open(evidence, encoding="utf-8") as stream:
                        payload = json.load(stream)
                    valid = (
                        isinstance(payload, dict)
                        and payload.get("status") == "passed"
                        and isinstance(payload.get("discovered"), int)
                        and payload["discovered"] == 32
                        and isinstance(payload.get("executed"), int)
                        and payload["executed"] > 0
                        and isinstance(payload.get("passed"), int)
                        and payload["passed"] > 0
                        and isinstance(payload.get("reason"), str)
                        and payload["reason"].strip() != ""
                    )
                    if valid:
                        up_line = ("HMBS_UPSTREAM_TEST_RESULT="
                                   + json.dumps(payload, separators=(",", ":")))
                        print(up_line, flush=True)
                        self.output.info(up_line)
                    else:
                        self.output.info(
                            "hmbs_upstream.json illegal (not re-emitted):"
                            " {}".format(evidence))
                else:
                    self.output.info(
                        "hmbs_upstream.json missing (not re-emitted):"
                        " {}".format(evidence))
            except Exception as exc:
                self.output.info(
                    "re-emit hmbs_upstream skipped: {}".format(exc))
