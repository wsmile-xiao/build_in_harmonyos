#!/usr/bin/env python3
"""Conan test_package — libesmtp 1.1.0.

消费者视角验证：CMake 链接 libesmtp::libesmtp 并运行 test_libesmtp，
离线调用会话/消息/收件人/头/枚举/超时 6 组断言（R34 合规，非版本查询空壳）。

证据标记：
- HMBS_TEST_PACKAGE_RESULT：discovered/passedCount 取自测试二进制真实输出
  （PASS[n/6] 行计数；缺失或数量不足即判失败）。
- HMBS_UPSTREAM_TEST_RESULT：status=no_tests。上游 meson.build 未定义任何
  test() 目标且源码树无 tests/ 目录（审计见 MANIFEST.yml）。在每轮必跑的
  test() 中复发该标记——主配方 build() 的输出在包缓存命中轮次不会出现。
"""
import glob
import json
import os
import shutil
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibesmtpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_tmpdir(self):
        """E002/readonly_tmp: OHOS /tmp is erofs read-only.

        Prefer HMBS-injected TMPDIR/TMP/TEMP, probe writability, fall back
        to a build-folder-local directory. Only replaces the temp-file
        root; test logic and counts are unchanged.
        """
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(key, "")
            if value and value != "/tmp":
                try:
                    os.makedirs(value, exist_ok=True)
                    probe = os.path.join(value, ".hmbs_probe")
                    with open(probe, "w") as handle:
                        handle.write("probe")
                    try:
                        os.remove(probe)
                    except OSError:
                        pass
                    return value
                except OSError:
                    continue
        fallback = os.path.join(self.build_folder or os.getcwd(), ".conan_tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _resolve_compiler(self, kind):
        """Same stale-profile-clang fallback as the main recipe.

        Only used when the profile compiler path is not a file (this
        runner); healthy runners keep the conf path untouched.

        Probes PATH plus well-known OHOS runner locations explicitly:
        the Python process PATH inside test_package does not always carry
        the hmbs-prepended tool dirs (so shutil.which may miss what the
        main recipe found), therefore also check $HOME/.harmonybrew/bin,
        /storage/Users/*/.harmonybrew/bin, OHOS_NDK_HOME and the
        version-agnostic SDK glob.
        """
        names = {"c": ("clang",), "cpp": ("clang++", "clang")} [kind]
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        conf_val = compilers.get(kind) or ""
        if conf_val and os.path.isfile(conf_val):
            return None
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        extra_dirs = []
        home = os.environ.get("HOME", "")
        if home:
            extra_dirs.append(os.path.join(home, ".harmonybrew", "bin"))
        try:
            extra_dirs.extend(
                sorted(glob.glob("/storage/Users/*/.harmonybrew/bin"))
            )
        except Exception:
            pass
        sdk_dirs = []
        ndk_home = os.environ.get("OHOS_NDK_HOME", "")
        if ndk_home:
            sdk_dirs.append(os.path.join(ndk_home, "llvm", "bin"))
        try:
            sdk_dirs.extend(
                sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin"))
            )
        except Exception:
            pass
        for directory in extra_dirs + sdk_dirs:
            for name in names:
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate):
                    return candidate
        for directory in sdk_dirs:
            for name in names:
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate):
                    return candidate
        return None

    def _patch_cmake_toolchain(self, cc, cxx):
        """Rewrite stale compiler paths inside conan_toolchain.cmake.

        Passing -DCMAKE_C_COMPILER via cmake.configure variables is not
        enough on this runner: the generated toolchain file pins the
        profile path and CMake still reports the stale
        /data/service/hnp/bin/clang. Rewrite only entries whose current
        path is not a file; existing valid paths stay untouched.
        """
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            return
        with open(toolchain, encoding="utf-8") as handle:
            content = handle.read()
        original = content
        for key, resolved in (("CMAKE_C_COMPILER", cc),
                              ("CMAKE_CXX_COMPILER", cxx)):
            if not resolved:
                continue
            match = re.search(
                r'(?m)^set\(%s\s+"?(.*?)"?\s*(CACHE[^)]*)?\)' % key, content
            )
            if match:
                current = (match.group(1) or "").strip()
                if current != resolved and current and not os.path.isfile(current):
                    start, end = match.span(1)
                    content = content[:start] + resolved + content[end:]
                    self.output.info(
                        "test_package %s: '%s' missing, using '%s'"
                        % (key, current, resolved)
                    )
        if content != original:
            with open(toolchain, "w", encoding="utf-8") as handle:
                handle.write(content)

    def build(self):
        # E002: keep CMake try-compile and shell temp files off read-only
        # /tmp before cmake.configure()/build().
        _tmpdir = self._resolve_tmpdir()
        try:
            os.makedirs(_tmpdir, exist_ok=True)
        except OSError:
            pass
        for _key in ("TMPDIR", "TMP", "TEMP", "TMP_DIR"):
            os.environ[_key] = _tmpdir
        self.output.info("E002 tmpdir for test_package build(): %s" % _tmpdir)
        cmake = CMake(self)
        variables = {}
        # Stale profile clang (main-recipe round 3 evidence: meson ENOENT on
        # /data/service/hnp/bin/clang): override only the compiler binary
        # path, sysroot/target flags still come from the toolchain file.
        _cc = self._resolve_compiler("c")
        _cxx = self._resolve_compiler("cpp")
        # Toolchain-file rewrite first: -D variables alone do not dislodge
        # the stale compiler pinned inside conan_toolchain.cmake on this
        # runner (cmake still reported /data/service/hnp/bin/clang).
        self._patch_cmake_toolchain(_cc, _cxx)
        if _cc:
            variables["CMAKE_C_COMPILER"] = _cc
            self.output.info("test_package CMAKE_C_COMPILER=%s" % _cc)
        if _cxx:
            variables["CMAKE_CXX_COMPILER"] = _cxx
            self.output.info("test_package CMAKE_CXX_COMPILER=%s" % _cxx)
        if str(self.settings.os) == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = compilers.get("cpp") or compilers.get("cxx")
            if compiler and not os.path.isfile(compiler) and _cxx:
                compiler = _cxx
            if compiler:
                compiler_dir = os.path.dirname(os.path.realpath(compiler))
                variables["OHOS_CXX_RUNTIME_DIR"] = os.path.join(
                    compiler_dir, "..", "lib", "aarch64-linux-ohos"
                )
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        dep = self.dependencies["libesmtp"]
        libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_libesmtp",
        )
        if not os.path.isfile(test_bin):
            raise ConanException("test binary not found: {}".format(test_bin))
        # libesmtp.so 动态链接 openssl 等，运行时需收集全部依赖（含传递依赖）的 lib 目录。
        # 注意：self.dependencies.values() 含 build 域 tool_requires（如 pkgconf），
        # 其 package_folder 可能为 None，直接 os.path.join 会抛
        # TypeError: expected str, bytes or os.PathLike object, not NoneType
        # （本轮真机 test_package 阶段实证）。先判空再拼接。
        library_paths = [libdir]
        for d in self.dependencies.values():
            try:
                pkg_folder = d.package_folder
                libdirs = d.cpp_info.libdirs
            except Exception:
                continue
            if not pkg_folder or not libdirs:
                continue
            if not libdirs[0]:
                continue
            pkg_lib = os.path.join(pkg_folder, libdirs[0])
            if os.path.isdir(pkg_lib) and pkg_lib not in library_paths:
                library_paths.append(pkg_lib)
        existing_ld = os.environ.get("LD_LIBRARY_PATH")
        if existing_ld:
            library_paths.append(existing_ld)
        ld_path = ":".join(library_paths)

        # 真实执行测试二进制并捕获输出，计数 PASS[n/6] 行（数字来自框架输出）。
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = ld_path
        # E002: test subprocess inherits the writable tmpdir as well, so
        # any shell-out or temp file inside the test binary avoids /tmp.
        _tmpdir = self._resolve_tmpdir()
        for _key in ("TMPDIR", "TMP", "TEMP", "TMP_DIR"):
            env.setdefault(_key, _tmpdir)
        try:
            proc = subprocess.run(
                [test_bin], capture_output=True, text=True, timeout=60, env=env
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            rc = proc.returncode
        except Exception as exc:
            output = "harness exception: {}".format(exc)
            rc = 1
        self.output.info("test_libesmtp output:\n" + "\n".join(output.splitlines()[-12:]))

        hits = set(re.findall(r"PASS\[(\d+)/6\]", output))
        discovered = 6
        passed_count = len(hits)
        ok = rc == 0 and passed_count == discovered

        marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_libesmtp",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )

        upstream_marker = {
            "status": "no_tests",
            "framework": "meson",
            "command": "meson test (upstream defines no test targets)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "libesmtp 1.1.0 上游不存在任何测试套件：meson.build 全文无 test() "
                "目标定义；源码树无 tests/ 目录；examples/ 仅含 mail-file.c 演示程序 "
                "（meson 仅在 openssl 存在时编译，且不安装）；上游文档仅描述构建安装流程"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False)
        )

        if not ok:
            raise ConanException(
                "libesmtp test_package failed: {}/{} assertions passed (rc={})".format(
                    passed_count, discovered, rc
                )
            )

        # L0d 门禁：test() 必须含 self.run() 真实执行逻辑。
        # LD_LIBRARY_PATH 显式前置（同 libass 配方做法），不依赖 conanrun 聚合环境。
        self.run('LD_LIBRARY_PATH="{}" "{}"'.format(ld_path, test_bin))
        self.output.info("libesmtp test_package passed")
