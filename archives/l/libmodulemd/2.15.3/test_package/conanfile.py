#!/usr/bin/env python3
"""Conan test_package for libmodulemd 2.15.3 — direct-cc build, no CMake.

Vanilla CMake (e.g. 4.4.3 on the device) has no Platform/HarmonyOS file, so a
CMakeToolchain-based test_package dies in cmake.configure with
"System is unknown to cmake" plus a CMAKE_C_COMPILER sanity-check failure on
/data/service/hnp/bin/clang (same failure that blocks the libyaml/0.2.5
dependency build in this preflight). OHOS /tmp is also a read-only erofs
mount, which breaks CMake try-compile temp files. This consumer therefore
compiles test_modulemd.c with the Conan-profile compiler directly (same
approach as archives/c/cthreadpool/0.0-git20231218.4eb5a69/test_package),
linking the packaged library plus its transitive deps via cpp_info.

Covers 8 explicit checks in test_modulemd.c (real ModulemdModuleStream /
ModulemdModuleIndex API calls) plus 1 modulemd-validator --version smoke,
and emits the HMBS_TEST_PACKAGE_RESULT marker with the real case count.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibmodulemdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _resolve_tool(self, name, fallback):
        # conf-first / PATH-fallback, same policy as the main recipe and the
        # cthreadpool precedent: only an absolute conf path that is missing
        # or not executable falls back to the bare tool name via PATH.
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        value = compilers.get(name) or fallback
        if "/" in value or "\\" in value:
            if not os.path.isfile(value):
                self.output.warning(
                    "HMBS: conf tools.build:compiler_executables:{}={} is not a file, "
                    "falling back to '{}' via PATH".format(name, value, fallback)
                )
                return fallback
            if not os.access(value, os.X_OK):
                self.output.warning(
                    "HMBS: conf tools.build:compiler_executables:{}={} is not executable, "
                    "falling back to '{}' via PATH".format(name, value, fallback)
                )
                return fallback
        return value

    def _writable_tmpdir(self):
        # OHOS /tmp is a read-only erofs mount; prefer the HMBS-injected
        # TMPDIR/TMP/TEMP, otherwise use a tmp dir inside the writable build
        # folder. Only the temp-file root is replaced; no test is skipped.
        for key in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(key)
            if value and os.path.isdir(value):
                return value.replace("\\", "/")
        fallback = os.path.join(self.build_folder, "tmp").replace("\\", "/")
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        return fallback

    def _with_tmpdir(self, command):
        tmp = self._writable_tmpdir()
        return 'TMPDIR="{t}" TMP="{t}" TEMP="{t}" {c}'.format(t=tmp, c=command)

    def _compile_args(self):
        # Aggregate include/lib dirs and link items from the direct dep and
        # its transitive host deps (glib2, libyaml, and their own deps).
        # Paths are made absolute against each package_folder because
        # cpp_info dirs are package-relative.
        includes, libdirs, libs, sysflags, defines = [], [], [], [], []
        seen = set()

        def _abs(pkg_folder, entry):
            entry = str(entry).replace("\\", "/")
            if os.path.isabs(entry):
                return entry
            return os.path.join(pkg_folder, entry).replace("\\", "/")

        for dep in self.dependencies.host.values():
            info = dep.cpp_info
            folder = str(dep.package_folder).replace("\\", "/")
            for inc in info.includedirs:
                path = _abs(folder, inc)
                if path not in seen:
                    seen.add(path)
                    includes.append('"-I{}"'.format(path))
            for libdir in info.libdirs:
                # Emit -L unconditionally (cthreadpool precedent): existence
                # cannot be probed meaningfully here and a missing dir is
                # harmless to the linker, while dropping dirs breaks static
                # transitive linkage (glib2/libyaml/libffi/intl).
                path = _abs(folder, libdir)
                libdirs.append('"-L{}"'.format(path))
            for lib in info.libs:
                libs.append("-l{}".format(str(lib)))
            for define in info.defines:
                defines.append("-D{}".format(str(define)))
            for system_lib in info.system_libs:
                if system_lib == "pthread":
                    sysflags.append("-pthread")
                else:
                    sysflags.append("-l{}".format(str(system_lib)))
        # Deduplicate libdirs while keeping order.
        dedup_libdirs = list(dict.fromkeys(libdirs))
        return " ".join(includes), " ".join(dedup_libdirs), " ".join(libs), " ".join(sysflags), " ".join(defines)

    def build(self):
        cc = self._resolve_tool("c", "clang")
        includes, libdirs, libs, sysflags, defines = self._compile_args()
        build = self.build_folder.replace("\\", "/")
        src = os.path.join(self.source_folder, "test_modulemd.c").replace("\\", "/")
        self.run(
            self._with_tmpdir(
                '{cc} -O2 {defines} {inc} "{src}" -o "{build}/test_modulemd" '
                "{libdir} {libs} {sys}".format(
                    cc=cc, defines=defines, inc=includes, src=src,
                    build=build, libdir=libdirs, libs=libs, sys=sysflags,
                )
            ),
            cwd=self.build_folder,
        )

    def _reemit_upstream_result(self):
        # 缓存命中跳过主包 build() 时，由 test_package 重发持久化上游证据
        # （cthreadpool/ayatana-ido 经验）。数字来自包内真实 meson test 结果，
        # 不伪造；缺失则显式失败，拒绝静默通过。
        try:
            pkg_folder = self.dependencies["libmodulemd"].package_folder
        except Exception:
            pkg_folder = None
        candidates = []
        if pkg_folder:
            candidates.append(os.path.join(str(pkg_folder), "res", "hmbs_upstream_result.json"))
        for _cand in candidates:
            if _cand and os.path.isfile(_cand):
                try:
                    with open(_cand, encoding="utf-8") as _f:
                        data = json.load(_f)
                except Exception as _exc:
                    raise RuntimeError("cannot parse persisted upstream result {}: {}".format(_cand, _exc))
                for _k in ("status", "discovered", "executed", "passed", "failed", "skipped"):
                    if _k not in data:
                        raise RuntimeError("persisted upstream result missing key: {}".format(_k))
                if data.get("status") != "passed" or not data.get("discovered"):
                    raise RuntimeError("persisted upstream result not passed: {}".format(data))
                if data.get("executed") != data.get("discovered") or data.get("failed") or data.get("skipped"):
                    raise RuntimeError("persisted upstream counters inconsistent: {}".format(data))
                _msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data, ensure_ascii=False)
                print(_msg, flush=True)
                self.output.info(_msg)
                return
        raise RuntimeError("persisted upstream result missing (res/hmbs_upstream_result.json); refusing silent pass")

    def test(self):
        # 8 explicit checks in test_modulemd + 1 validator --version smoke.
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "./test_modulemd && modulemd-validator --version",
            "discovered": 9,
            "passedCount": 9,
        }
        if not can_run(self):
            test_pkg["passed"] = False
            marker = json.dumps(test_pkg, ensure_ascii=False)
            print("HMBS_TEST_PACKAGE_RESULT=" + marker, flush=True)
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + marker)
            raise RuntimeError("test_package cannot run on this host; refusing silent pass")
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly,
        # so wrap the test commands with a shell. Prefer bash, fall back to
        # sh (21:18 preflight proves no standalone bash on device; sh runs
        # both test commands, which use no bashisms).
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if bash is None:
            for _cand in ("/data/service/hnp/bin/bash", shutil.which("sh"),
                          "/bin/sh", "/system/bin/sh"):
                if _cand and os.path.isfile(_cand) and os.access(_cand, os.X_OK):
                    bash = _cand
                    break
        if bash is None:
            bash = "sh"
        _tmp = self._writable_tmpdir()
        for _key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_key] = _tmp
        passed_count = 0
        try:
            # 1) 真实调用库 API（流创建/属性/NSVC/拷贝/索引/导出 YAML）
            self.run('{} -c "./test_modulemd"'.format(bash), env="conanrun", cwd=self.build_folder)
            passed_count += 8
            # 2) 随包 validator CLI 真实运行（--version 走 GOption 解析）
            self.run('{} -c "modulemd-validator --version"'.format(bash), env="conanrun", cwd=self.build_folder)
            passed_count += 1
        except Exception as exc:
            self.output.info("test_package failed: {}".format(exc))
            test_pkg["passed"] = False
            test_pkg["passedCount"] = 0 if passed_count == 0 else passed_count
            marker = json.dumps(test_pkg, ensure_ascii=False)
            print("HMBS_TEST_PACKAGE_RESULT=" + marker, flush=True)
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + marker)
            raise
        test_pkg["passed"] = passed_count == 9
        test_pkg["passedCount"] = passed_count
        # 先重发持久化上游证据（缓存命中时本轮唯一上游标记来源），再发本包标记。
        self._reemit_upstream_result()
        marker = json.dumps(test_pkg, ensure_ascii=False)
        print("HMBS_TEST_PACKAGE_RESULT=" + marker, flush=True)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + marker)
        if passed_count != 9:
            raise RuntimeError("test_package failed: {}/9 passed".format(passed_count))
