#!/usr/bin/env python3
"""Conan test_package — libmythes 1.2.6 消费者测试（R34，直接编译）。

Vanilla CMake（真机 4.4.3）无 Platform/HarmonyOS 模块，CMakeToolchain
的 test_package 在 cmake.configure 死于 "System is unknown to cmake" +
CMAKE_CXX_COMPILER identification unknown（主包 Autotools 已编译通过，
test_package 独立复现；libseqlib/1.2.0 同指纹先例）。generate() 内覆盖
CMAKE_CXX_COMPILER 也救不了未知平台的 try_compile。
本消费者改用 profile C++ 编译器直接编译 test_mythes.cpp（cthreadpool /
libseqlib 先例），链接打包态静态/共享库及传递依赖，不执行任何
CMake project()，从根上避开该失败模式。
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout

CONSUMER_CHECK_COUNT = 9


class LibmythesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _resolve_tool(self, name, fallback):
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
                    "conf tools.build:compiler_executables:{}={} not a file, "
                    "fallback to '{}' via PATH".format(name, value, fallback)
                )
                return fallback
            if not os.access(value, os.X_OK):
                self.output.warning(
                    "conf tools.build:compiler_executables:{}={} not executable, "
                    "fallback to '{}' via PATH".format(name, value, fallback)
                )
                return fallback
        return value

    def _writable_tmpdir(self):
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
        ordered = []
        for dep in self.dependencies.values():
            try:
                dep_name = dep.ref.name
            except Exception:
                continue
            if dep_name not in ordered:
                ordered.append(dep_name)
        if "libmythes" in ordered:
            ordered.remove("libmythes")
        ordered.insert(0, "libmythes")
        includes, libdirs, libs, syslibs = [], [], [], []
        for dep_name in ordered:
            if dep_name not in self.dependencies:
                continue
            info = self.dependencies[dep_name].cpp_info
            includes += [
                '"-I{}"'.format(str(p).replace("\\", "/"))
                for p in info.includedirs
            ]
            # 上游 hunspell 头在 include/hunspell 子目录而 example 风格为
            # 扁平 #include；消费者 test 仅用 mythes.hxx，此处额外补后缀
            # 以兼容直接/间接包含 hunspell 头的场景。
            try:
                pf = self.dependencies[dep_name].package_folder
                sub = os.path.join(pf, "include", "hunspell").replace("\\", "/")
                if os.path.isdir(os.path.join(pf, "include", "hunspell")):
                    includes.append('"-I{}"'.format(sub))
            except Exception:
                pass
            libdirs += [
                '"-L{}"'.format(str(p).replace("\\", "/"))
                for p in info.libdirs
            ]
            # Fallback (libmythes only): if the header layout differs (e.g.
            # installed under a subdirectory), locate mythes.hxx under the
            # package folder and add its directory so <mythes.hxx> still
            # resolves. Does not change the primary -I<package>/include path.
            if dep_name == "libmythes":
                try:
                    pf = self.dependencies[dep_name].package_folder
                    if pf and os.path.isdir(pf):
                        for root, _, files in os.walk(pf):
                            if "mythes.hxx" in files:
                                found = str(root).replace("\\", "/")
                                flag = '"-I{}"'.format(found)
                                if flag not in includes:
                                    includes.append(flag)
                                break
                except Exception:
                    pass
            libs += ["-l{}".format(str(l)) for l in info.libs]
            syslibs += ["-l{}".format(str(l)) for l in info.system_libs]
        return " ".join(includes), " ".join(libdirs), " ".join(libs), " ".join(syslibs)

    def build(self):
        cxx = self._resolve_tool("cpp", "clang++")
        includes, libdirs, libs, syslibs = self._compile_args()
        self.output.info(
            "direct-cxx: cxx=%s includes=%s libdirs=%s libs=%s syslibs=%s"
            % (cxx, includes, libdirs, libs, syslibs)
        )
        # Pre-link evidence: list what the -L dirs actually contain so the
        # next preflight log shows whether libmythes-1.2.so/.a is present
        # (previous failure: ld.lld unable to find library -lmythes-1.2).
        try:
            for dep in self.dependencies.values():
                try:
                    name = dep.ref.name
                except Exception:
                    continue
                if name != "libmythes":
                    continue
                pf = getattr(dep, "package_folder", "") or ""
                self.output.info("libmythes package_folder={}".format(pf))
                for sub in ("lib", "lib64"):
                    d = os.path.join(pf, sub) if pf else sub
                    try:
                        entries = sorted(os.listdir(d))
                    except OSError:
                        self.output.info("libdir {}: <missing>".format(d))
                        continue
                    hits = [e for e in entries if e.startswith("libmythes")]
                    self.output.info(
                        "libdir {}: {}".format(d, hits or entries[:20]))
        except Exception as exc:
            self.output.warning("libdir diagnostic failed: {}".format(exc))
        build = self.build_folder.replace("\\", "/")
        src = os.path.join(self.source_folder, "test_mythes.cpp").replace("\\", "/")
        if not os.path.isfile(src):
            raise ConanException("test source missing: {}".format(src))
        self.run(
            self._with_tmpdir(
                '{cxx} -std=c++17 -O2 {inc} "{src}" -o "{build}/test_mythes" '
                "{libdir} {libs} {sys}".format(
                    cxx=cxx,
                    inc=includes,
                    src=src,
                    build=build,
                    libdir=libdirs,
                    libs=libs,
                    sys=syslibs,
                )
            ),
            cwd=self.build_folder,
        )
        # 消费者词库随包运行，落到 build 目录。
        for name in ("test_thes.idx", "test_thes.dat"):
            src_f = os.path.join(self.source_folder, name)
            dst_f = os.path.join(self.build_folder, name)
            if os.path.isfile(src_f) and not os.path.isfile(dst_f):
                try:
                    shutil.copy(src_f, dst_f)
                except Exception as exc:
                    raise ConanException("copy fixture failed: {}".format(exc))

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: run on device only")
            return
        tmp = self._writable_tmpdir()
        os.environ["TMPDIR"] = tmp
        os.environ["TMP"] = tmp
        os.environ["TEMP"] = tmp
        path = os.path.join(self.build_folder, "test_mythes").replace("\\", "/")
        # R34: test() 内显式 self.run 编译产物。
        self.run('"{0}"'.format(path), env="conanrun", cwd=self.build_folder)
        # 捕获输出做机器证据计数（退出码 0 不等于真跑）。
        # 注意：必须带 conanrun 运行环境重跑，否则 musl loader 报
        # Error loading shared library libmythes-1.2.so.0 /
        # libhunspell-1.7.so.0 + Error relocating _ZN6MyThes...。
        # self.run(env="conanrun") 已带 LD_LIBRARY_PATH，但下方的
        # subprocess 若只用 dict(os.environ) 会丢掉它而复现装载失败。
        import subprocess

        cap_env = dict(os.environ)
        try:
            _lib_paths = []
            for _dep in self.dependencies.values():
                try:
                    _pf = getattr(_dep, "package_folder", "") or ""
                except Exception:
                    _pf = ""
                if _pf:
                    for _sub in ("lib", "lib64"):
                        _d = os.path.join(_pf, _sub)
                        try:
                            if os.path.isdir(_d) and _d not in _lib_paths:
                                _lib_paths.append(_d)
                        except Exception:
                            pass
                try:
                    for _ld in (_dep.cpp_info.libdirs or []):
                        try:
                            if _ld and os.path.isdir(_ld) and _ld not in _lib_paths:
                                _lib_paths.append(_ld)
                        except Exception:
                            pass
                except Exception:
                    pass
            _existing = cap_env.get("LD_LIBRARY_PATH", "") or ""
            if _existing and _existing not in _lib_paths:
                _lib_paths.append(_existing)
            if _lib_paths:
                cap_env["LD_LIBRARY_PATH"] = ":".join(_lib_paths)
        except Exception as _env_exc:
            self.output.warning("runenv LD_LIBRARY_PATH fallback failed: {}".format(_env_exc))
        try:
            proc = subprocess.run(
                [path],
                cwd=self.build_folder,
                env=cap_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=60,
            )
            output = proc.stdout or ""
        except Exception as exc:
            raise ConanException("test_mythes capture failed: {}".format(exc))
        self.output.info(output[-2000:])
        for name in ("test_thes.idx", "test_thes.dat"):
            p = os.path.join(self.build_folder, name)
            try:
                if os.path.getsize(p) == 0:
                    raise ConanException("fixture {} is empty".format(name))
            except OSError:
                raise ConanException("fixture {} missing".format(name))
        ok_count = output.count("ok:")
        ok_tail = "libmythes consumer test: OK" in output
        passed = proc.returncode == 0 and ok_tail and ok_count == CONSUMER_CHECK_COUNT
        marker = {
            "executed": True,
            "passed": passed,
            "command": "./test_mythes",
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        marker_text = json.dumps(marker, ensure_ascii=False)
        print("HMBS_TEST_PACKAGE_RESULT=" + marker_text, flush=True)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + marker_text)
        upstream = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "mythes-1.2.6.tar.xz audited (sha256 97bd2ba5738aebdba1bc31f30"
                "f1be42f1404386c94105ad5990d839a1311c8a5): Makefile.am defines "
                "check_PROGRAMS=example with no TESTS variable, no tests/ or "
                "test/ directory, no gtest/pytest/ctest/meson wiring; "
                "make check only builds the manual example binary"
            ),
        }
        up_text = json.dumps(upstream, ensure_ascii=False)
        print("HMBS_UPSTREAM_TEST_RESULT=" + up_text, flush=True)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + up_text)
        if not passed:
            raise ConanException(
                "consumer test failed: rc={} ok={}/{} tail={}".format(
                    proc.returncode, ok_count, CONSUMER_CHECK_COUNT, ok_tail
                )
            )
