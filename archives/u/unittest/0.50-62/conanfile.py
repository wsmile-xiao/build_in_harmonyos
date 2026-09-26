#!/usr/bin/env python3
"""Conan recipe — unittest 0.50-62 (C++ unit test framework, autotools).

上游：https://unittest.red-bean.com/ （David Carlton 的 xUnit 风格 C++ 测试框架，
BSD-3-Clause；版本 0.50 修订 62，tarball 内 print-version 恒输出 62）

OHOS 适配要点（零补丁文件；1 处构建期源码兼容改写见 build()）：
- 上游为经典 Autotools 工程（configure + Makefile.in 已随包发布，无需 autoreconf）；
  默认目标 all 依赖 test：构建 lib/libunittest.a 后自动运行 test/unittesttest，
  任一用例失败则 make 直接报错（第一道咽喉）。
- 与 Homebrew 公式一致，以 -std=c++03 编译 2015 年 era 的 C++ 源码。
- 上游只构建/安装静态库 libunittest.a（无 shared 规则），shared 选项显式拒绝。
- 平台适配面：纯用户态 C++03 + sigaction/siglongjmp 信号捕获（测试以 raise()
  注入信号，非硬件 fault，AArch64 语义一致）+ abi::__cxa_demangle；
  execinfo.h 缺失时 configure（AC_CHECK_HEADERS）自动降级，dumpStack 为空实现。
  以上在 OHOS musl 上均原生可用。
- build() 末尾显式重跑 test/unittesttest，解析确定性汇总行
  "Tests finished with N passes and M failures." 并输出
  HMBS_UPSTREAM_TEST_RESULT（conan 输出 + stdout 双通道）；任一失败、
  汇总行缺失或用例数漂移即中止构建。
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class UnittestConan(ConanFile):
    name = "unittest"
    version = "0.50-62"
    description = "C++ unit testing framework in the xUnit style"
    license = "BSD-3-Clause"
    homepage = "https://unittest.red-bean.com/"
    url = "https://unittest.red-bean.com/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # 上游测试审计（源码静态清点，待真机运行确认）：
    # test/ 内 6 个 All 套件共注册 63 个叶子用例（existing 2 + registry 12 +
    # suite 22 + testholder 5 + testptr 7 + test 15，见 notes.md 清单）；
    # Registry::run 为 6 个套件容器各计 1 pass，全绿时汇总行应为 69 passes。
    UPSTREAM_TEST_PASSES = 69

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # 上游 Makefile 只构建/安装 libunittest.a，无共享库规则
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "unittest upstream only builds a static library (libunittest.a)")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 与 Homebrew 公式一致：2015 年 era 源码以 C++03 编译。
        # 注意上游 Makefile.utils.in 用 $(CFLAGS) 编译 .cpp（而非
        # CXXFLAGS），真机日志证实仅 tc.cxxflags 时编译行无 -std 标志；
        # 故 CFLAGS/CXXFLAGS 双通道追加（链接行同样用 $(CFLAGS)）。
        tc.cflags.append("-std=c++03")
        tc.cxxflags.append("-std=c++03")
        # 静态库位置无关代码（供下游链接进共享库）
        if self.options.get_safe("fPIC", True):
            tc.cxxflags.append("-fPIC")
        # HMBS 真机兼容：复用守护进程注入的可写 tmpdir（E002），避免
        # configure/mktemp 落到只读 /tmp；同时做编译器存在性探测回退
        #（聚合经验 #1：profile 钉死的绝对路径在部分 runner 上缺失）。
        tmpdir = self._hmbs_writable_tmpdir()
        cc, cxx = self._hmbs_resolve_compilers()
        # profile [buildenv] 把 SHELL/CONFIG_SHELL 钉死到
        # /data/service/hnp/bin/bash，本轮 runner 上该路径
        # "inaccessible or not found"（configure 重 exec 直接 Error 1）。
        # 按文件存在性探测可用 shell，绝不复用坏值（经验 2）。
        shell = self._hmbs_detect_shell()
        env = tc.environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        # 存在即用、缺失才覆盖：健康机上 resolved == conf 原值，零改动。
        if cc:
            env.define("CC", cc)
        if cxx:
            env.define("CXX", cxx)
        tc.generate(env=env)
        self._hmbs_persist_shell_tmp(tmpdir, shell)

    def _hmbs_writable_tmpdir(self):
        """复用 HMBS 注入的可写 tmpdir，绝不返回裸 /tmp（E002）。"""
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            value = os.environ.get(var)
            if not value or value in ("0", "/tmp"):
                continue
            try:
                os.makedirs(value, exist_ok=True)
            except OSError:
                continue
            try:
                probe = os.path.join(value, ".hmbs_probe")
                with open(probe, "w") as handle:
                    handle.write("probe")
                os.remove(probe)
                return value
            except OSError:
                continue
        fallback = os.path.join(self.build_folder or os.getcwd(), "tmp_hmbs")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _hmbs_resolve_compilers(self):
        """存在即用、缺失时经 PATH 回退（聚合经验 #1，非致命探针）。

        只覆盖 CC/CXX 导出，不碰 CFLAGS/LDFLAGS；健康机零改动。
        """
        conf = {}
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        conf_cc = conf.get("c")
        conf_cxx = conf.get("cpp")

        def _usable(path):
            return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)

        cc = conf_cc if _usable(conf_cc) else None
        cxx = conf_cxx if _usable(conf_cxx) else None
        if cc is None:
            for cand in ("clang", "cc", "gcc"):
                found = shutil.which(cand)
                if found:
                    cc = found
                    break
            else:
                cc = conf_cc
        if cxx is None:
            for cand in ("clang++", "c++", "g++"):
                found = shutil.which(cand)
                if found:
                    cxx = found
                    break
            else:
                cxx = conf_cxx
        # 同目录兄弟编译器优先：cc 与 cxx 尽量成对（clang/clang++）。
        try:
            if cxx and cc and os.path.basename(cxx).startswith("clang") \
                    and os.path.basename(cc) != "clang":
                sibling = os.path.join(os.path.dirname(cxx), "clang")
                if _usable(sibling):
                    cc = sibling
            if cc and cxx and os.path.basename(cc) == "clang":
                sibling = os.path.join(os.path.dirname(cc), "clang++")
                if _usable(sibling):
                    cxx = sibling
        except Exception:
            pass
        try:
            self.output.info("[hmbs] compiler probe: conf_c=%s conf_cxx=%s "
                             "resolved_c=%s resolved_cxx=%s"
                             % (conf_cc, conf_cxx, cc, cxx))
        except Exception:
            pass
        return cc, cxx

    def _hmbs_detect_shell(self):
        """按文件存在性探测可用 shell，不复用坏的 CONFIG_SHELL 值。

        profile [buildenv] 钉死的 /data/service/hnp/bin/bash 在本轮
        runner 上 "inaccessible or not found"；HMBS 注入 SHELL=/bin/sh。
        HMDFS 上 chmod/X_OK 不可靠，故只判存在性（经验 2）。
        """
        for cand in ("/bin/sh", "/system/bin/sh"):
            try:
                if os.path.isfile(cand):
                    return cand
            except OSError:
                continue
        return os.environ.get("SHELL") or "sh"

    def _hmbs_persist_shell_tmp(self, tmpdir, shell):
        """把可写 TMPDIR 与可用 SHELL 持久化进 conanbuild scope。

        conanbuild.sh 会重导出 profile 的坏 SHELL/CONFIG_SHELL，
        后生成的 hmbs_tmp 脚本以同名覆盖兜底；真正咽喉仍是
        build() 内联 CONFIG_SHELL/SHELL 显式调用（最近作用域获胜）。
        """
        try:
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.define("SHELL", shell)
            env.define("CONFIG_SHELL", shell)
            for key in ("HMBS_AUTOCONF_MKTEMP_FALLBACK",
                        "HMBS_CAP_LOCAL_MKTEMP", "HMBS_TMPDIR",
                        "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD",
                        "HMBS_CAP_SYMLINK", "HMBS_INSTALL"):
                value = os.environ.get(key)
                if value:
                    env.define(key, value)
            env.vars(self, scope="build").save_script("hmbs_tmp")
            self.output.info("[hmbs] persisted SHELL=%s TMPDIR=%s"
                             % (shell, tmpdir))
        except Exception as exc:
            self.output.warning("[hmbs] persist shell/tmp failed: %s" % exc)

    def _hmbs_patch_bad_shell_refs(self):
        """把坏 shell 字面量替换为可用 shell（字符串替换，不改逻辑）。

        仅设 os.environ 不够：坏值由 conanbuild/toolchain 脚本在
        Python env 之后重导出，configure 约 139 行重 exec
        $CONFIG_SHELL 时仍取到坏值。把 source 与 build 树下
        configure、config.status、libtool 与生成 Makefile 中的坏字面量
        替换为探测到的可用 shell。
        """
        try:
            shell = self._hmbs_detect_shell()
        except Exception:
            shell = "/bin/sh"
        bad = "/data/service/hnp/bin/bash"
        roots = []
        for attr in ("build_folder", "base_build_folder"):
            try:
                value = getattr(self.folders, attr, None) \
                    or getattr(self, attr, None)
            except Exception:
                value = None
            if value and os.path.isdir(value) and value not in roots:
                roots.append(value)
        try:
            if self.source_folder and os.path.isdir(self.source_folder):
                if self.source_folder not in roots:
                    roots.append(self.source_folder)
        except Exception:
            pass
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    if not (name == "configure" or name == "config.status"
                            or name == "libtool" or name == "Makefile"
                            or name.endswith(".sh") or name.endswith(".mk")):
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="ignore", newline="") as handle:
                            text = handle.read()
                    except OSError:
                        continue
                    if bad in text:
                        try:
                            with open(path, "w", encoding="utf-8",
                                      newline="\n") as handle:
                                handle.write(text.replace(bad, shell))
                            self.output.info(
                                "[hmbs] rewrote bad shell ref in %s" % path)
                        except OSError:
                            continue

    def _hmbs_run_configure_explicit(self, tmpdir, shell, cc, cxx):
        """用可用 shell 显式调用 configure，内联 env 覆盖 conanbuild 导出。

        不用 Autotools.configure() 直接 exec：其重 exec 会读到
        conanbuild.sh 重导出的坏 CONFIG_SHELL。改为
        `"<shell>" "<src_configure>" ...` 并以内联
        CONFIG_SHELL/SHELL/TMPDIR 赋值覆盖（最近作用域获胜），
        env=conanbuild 保留原有 CFLAGS/LDFLAGS/CC 等工具链导出。
        前缀参数为 AutotoolsToolchain 默认值；本配方无额外
        configure 标志，保持原行为。

        上游为 2015 年手写 Makefile.in，不支持 VPATH 异地构建
        （build-release 下 `make lib/libunittest.a` 报
        No rule to make target），故一律在 source_folder 内
        in-source 配置/构建（emacs/zsv 同惯例）。
        """
        src_configure = os.path.join(self.source_folder, "configure")
        parts = [
            'TMPDIR="%s" TMP="%s" TEMP="%s"' % (tmpdir, tmpdir, tmpdir),
            'CONFIG_SHELL="%s" SHELL="%s"' % (shell, shell),
            '"%s" "%s"' % (shell, src_configure),
            '--prefix=/ "--bindir=${prefix}/bin" "--sbindir=${prefix}/bin"',
            '"--libdir=${prefix}/lib" "--includedir=${prefix}/include"',
            '"--oldincludedir=${prefix}/include"',
            '"CC=%s"' % cc if cc else "",
            '"CXX=%s"' % cxx if cxx else "",
            '"TMPDIR=%s" "TMP=%s" "TEMP=%s"' % (tmpdir, tmpdir, tmpdir),
            '"SHELL=%s" "CONFIG_SHELL=%s"' % (shell, shell),
        ]
        cmd = " ".join(p for p in parts if p)
        self.output.info("[hmbs] explicit configure: SHELL=%s TMPDIR=%s"
                         % (shell, tmpdir))
        # in-source：旧手写 Makefile 不支持 VPATH，cwd 必须为源码根。
        self.run(cmd, cwd=self.source_folder, env="conanbuild")

    def _hmbs_patch_werror_deprecated(self):
        """clang -Werror 将新告警变为错误，需最小豁免。

        上游 Makefile.utils.in 写死 `CFLAGS = @CFLAGS@ -Wall -Werror`，
        test/ExistingBaseTest.cpp 用 std::auto_ptr，OHOS libc++ 头已标记
        deprecated，-Werror 下直接 Error 2（与 notes.md 问题 3 预判一致）；
        test/TestHolderTest.cpp 的 Helper 析构故意 throw（供
        ExceptionOnTearDown 用例捕获），新 clang 以
        [-Werror,-Wexceptions] 拒绝（2026-09-24 真机）。
        因 -Wall -Werror 写在 @CFLAGS@ 之后，tc.cxxflags 追加的
        -Wno-error 排在 -Werror 之前会被覆盖，故必须在构建脚本中把
        `-Werror` 原地扩展为 `-Werror -Wno-error=deprecated-declarations`
        `-Wno-error=exceptions`（幂等：已含词元逐个跳过；仅降级这两类
        告警为警告，其余 -Werror 保留；不改源码、不动测试口径）。
        """
        token = "-Wno-error=deprecated-declarations"
        extra = "-Wno-error=exceptions"
        tokens = (token, extra)
        roots = []
        try:
            if self.source_folder and os.path.isdir(self.source_folder):
                roots.append(self.source_folder)
        except Exception:
            pass
        try:
            if self.build_folder and os.path.isdir(self.build_folder):
                if self.build_folder not in roots:
                    roots.append(self.build_folder)
        except Exception:
            pass
        names = ("Makefile.utils.in", "Makefile.utils", "Makefile.in",
                 "Makefile", "Makefile.utils.mk")
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    if name not in names and not name.endswith(".mk"):
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="ignore", newline="") as handle:
                            text = handle.read()
                    except OSError:
                        continue
                    if "-Werror" not in text:
                        continue
                    # 仅追加缺失词元，避免重复（幂等）。
                    missing = [t for t in tokens if t not in text]
                    if not missing:
                        continue
                    new = text.replace("-Werror", "-Werror " + " ".join(missing))
                    if new == text:
                        continue
                    try:
                        with open(path, "w", encoding="utf-8",
                                  newline="\n") as handle:
                            handle.write(new)
                        self.output.info(
                            "[hmbs] patched -Werror -> -Werror %s in %s"
                            % (" ".join(missing), path))
                    except OSError:
                        continue

    def _hmbs_patch_testholder_noexcept(self):
        """ExceptionOnTearDown 在新 libc++ 下 terminate，需声明析构可抛。

        上游 test/TestHolderTest.cpp 的 Helper 析构故意
        `throw std::runtime_error`（供 ASSERT_EXCEPTION 捕获），C++11 起
        析构隐式 noexcept(true)，OHOS libc++ 下直接 terminate（真机
        68 passes / 1 failure，abort 于本用例）。改写为按 __cplusplus
        守卫的显式可抛声明（C++11+ 用 noexcept(false)，C++03 用动态
        throw 规格），只恢复“析构异常可被捕获”的原语义，不断言改动、
        不跳过用例。行级字符串替换（非 conandata 补丁）：tarball 与
        SVN trunk 视图行号不一致，unified diff hunk 在真机上对不上
        （hunk no.1 doesn't match at line 148），故用正则按实际内容
        定位替换，幂等（已含 noexcept(false) 则跳过）。
        """
        import re
        rel = os.path.join("test", "TestHolderTest.cpp")
        path = os.path.join(self.source_folder, rel)
        try:
            with open(path, "r", encoding="utf-8", errors="replace",
                      newline="") as handle:
                text = handle.read()
        except OSError as exc:
            raise ConanException(
                "Helper 析构兼容改写失败：无法读取 %s：%s" % (rel, exc))
        if "noexcept(false)" in text:
            self.output.info(
                "[hmbs] testholder noexcept already patched, skip")
            return
        pattern = re.compile(
            r"^([ \t]*)~Helper\(\)\s*\{\s*throw\s+"
            r"std::runtime_error\(\"Helper destructor\"\);\s*\}[ \t]*$",
            re.M)
        replacement = (
            "\\1#if __cplusplus >= 201103L\n"
            "\\1~Helper() noexcept(false)"
            " { throw std::runtime_error(\"Helper destructor\"); }\n"
            "\\1#else\n"
            "\\1~Helper() throw(std::runtime_error)"
            " { throw std::runtime_error(\"Helper destructor\"); }\n"
            "\\1#endif")
        new_text, count = pattern.subn(replacement, text)
        if count != 1:
            # 回退：子串级替换（忽略前导空白差异）
            needle = ("~Helper() { throw std::runtime_error"
                      "(\"Helper destructor\"); }")
            if text.count(needle) == 1:
                new_text = text.replace(
                    needle,
                    "#if __cplusplus >= 201103L\n"
                    "      ~Helper() noexcept(false)"
                    " { throw std::runtime_error(\"Helper destructor\"); }\n"
                    "#else\n"
                    "      ~Helper() throw(std::runtime_error)"
                    " { throw std::runtime_error(\"Helper destructor\"); }\n"
                    "#endif")
                count = 1
        if count != 1:
            for line in text.splitlines():
                if "Helper destructor" in line:
                    self.output.warning(
                        "[hmbs] unexpected Helper dtor line: %s"
                        % line[:200])
            raise ConanException(
                "Helper 析构兼容改写失败：在 %s 中未定位到唯一的 "
                "~Helper() throw 行（count=%s），已如实报错不伪造通过"
                % (rel, count))
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(new_text)
            self.output.info(
                "[hmbs] patched Helper dtor noexcept(false) in %s" % rel)
        except OSError as exc:
            raise ConanException(
                "Helper 析构兼容改写失败：无法写回 %s：%s" % (rel, exc))

    def _hmbs_patch_configure_umask(self):
        """E011：configure 内 umask 077 在 HMDFS 上建不出可写临时目录。

        生成文件程序化改写（不进补丁），仅做 umask 077 -> 022 替换。
        """
        for name in ("configure",):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.output.info("[hmbs] patched %s: umask 077 -> 022" % name)
                except OSError:
                    pass

    def _hmbs_dump_config_log(self):
        """configure 失败时转储 config.log 尾部与编译器段，供下轮定位。"""
        for base in (self.build_folder, self.source_folder):
            if not base:
                continue
            for root, _dirs, files in os.walk(base):
                if "config.log" not in files:
                    continue
                path = os.path.join(root, "config.log")
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.read().splitlines()
                except OSError:
                    continue
                self.output.info("[hmbs] config.log: %s (last 40 lines)" % path)
                for line in lines[-40:]:
                    self.output.info("  config.log| " + line[:500])
                # 编译器段：找出 C++ compiler 检查附近行
                for i, line in enumerate(lines):
                    if "checking for C++ compiler" in line or "cannot create executables" in line:
                        lo = max(0, i - 5)
                        hi = min(len(lines), i + 15)
                        self.output.info("[hmbs] config.log compiler section @%d:" % i)
                        for ctx in lines[lo:hi]:
                            self.output.info("  config.log| " + ctx[:500])
                        break
                return

    def build(self):
        apply_conandata_patches(self)
        # E002：进程级可写 TMPDIR，configure/conftest/mktemp 避开只读 /tmp。
        # SHELL/CONFIG_SHELL 不复用 profile 坏值，按存在性探测（经验 2）。
        tmpdir = self._hmbs_writable_tmpdir()
        try:
            shell = self._hmbs_detect_shell()
        except Exception:
            shell = "/bin/sh"
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        os.environ["SHELL"] = shell
        os.environ["CONFIG_SHELL"] = shell
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        self.output.info("[hmbs] writable tmpdir: %s SHELL=%s"
                         % (tmpdir, shell))
        # E011 + 双通道编译器覆盖（generate 已烘焙，os.environ 同步）。
        self._hmbs_patch_configure_umask()
        self._hmbs_patch_werror_deprecated()
        self._hmbs_patch_testholder_noexcept()
        self._hmbs_patch_bad_shell_refs()
        cc, cxx = self._hmbs_resolve_compilers()
        if cc:
            os.environ["CC"] = cc
        if cxx:
            os.environ["CXX"] = cxx
        try:
            self._hmbs_run_configure_explicit(tmpdir, shell, cc, cxx)
        except Exception:
            self._hmbs_dump_config_log()
            raise
        # configure 会生成带 SHELL 的 build 树文件，再清一次坏引用。
        # 同时把生成的 Makefile.utils 中的 -Werror 同样豁免（幂等）。
        try:
            self._hmbs_patch_bad_shell_refs()
        except Exception:
            pass
        try:
            self._hmbs_patch_werror_deprecated()
        except Exception:
            pass
        # OHOS 内核对无 .codesign 的 ELF 直接 SIGKILL（Signal 9）。
        # 上游默认目标会立即执行未签名的 unittesttest，故分子目录构建：
        # lib/ 默认目标即 libunittest.a（无测试执行），test/ 显式目标
        # unittesttest 只链接不运行（`test` 目标才会 ./unittesttest）。
        # 顶层 `make lib/libunittest.a` 在此工程不存在（真机
        # No rule to make target），且异地 build-release 下 VPATH
        # 不可用，故一律 in-source 按子目录构建，签名后再显式运行。
        make_vars = ('make -j1 SHELL="%s" CONFIG_SHELL="%s" '
                     'TMPDIR="%s" TMP="%s" TEMP="%s"'
                     % (shell, shell, tmpdir, tmpdir, tmpdir))
        lib_dir = os.path.join(self.source_folder, "lib")
        test_dir = os.path.join(self.source_folder, "test")
        self.output.info("[hmbs] in-source subdir build in %s"
                         % self.source_folder)
        try:
            self.run(make_vars + ' libunittest.a',
                     cwd=lib_dir, env="conanbuild")
        except Exception:
            # 目标名若与上游版本有出入，回退到 lib/ 默认目标
            # （all: libunittest.a，同样不触发测试执行）。
            self.output.warning(
                "[hmbs] make libunittest.a failed, retry default target")
            self.run(make_vars, cwd=lib_dir, env="conanbuild")
        self.run(make_vars + ' unittesttest',
                 cwd=test_dir, env="conanbuild")
        self._hmbs_sign_build_binaries()
        self._run_upstream_tests()

    def _hmbs_sign_one_elf(self, path):
        import shutil as _shutil
        import subprocess as _subp
        try:
            is_ohos = str(self.settings.os) == "OHOS"
        except Exception:
            is_ohos = False
        if not is_ohos:
            return False
        if not path or not os.path.isfile(path):
            return False
        try:
            with open(path, "rb") as _h:
                if _h.read(4) != b"\x7fELF":
                    return False
        except OSError:
            return False
        for _tool in ("/data/service/hnp/bin/llvm-objcopy", _shutil.which("llvm-objcopy") or "llvm-objcopy"):
            try:
                _subp.run([_tool, "--remove-section", ".codesign", path], stdout=_subp.DEVNULL, stderr=_subp.DEVNULL, check=False, timeout=10)
                break
            except Exception:
                continue
        signed = False
        for _tool in ("/data/service/hnp/bin/binary-sign-tool", _shutil.which("binary-sign-tool") or "binary-sign-tool"):
            try:
                _r = _subp.run([_tool, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"], stdout=_subp.PIPE, stderr=_subp.PIPE, check=False, timeout=15)
                if _r.returncode == 0:
                    signed = True
                    try:
                        self.output.info("[hmbs] self-signed ELF")
                    except Exception:
                        pass
                    break
            except Exception:
                continue
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass
        return signed

    def _hmbs_sign_build_binaries(self):
        try:
            binary = self._find_test_binary()
        except Exception:
            return False
        try:
            ok = self._hmbs_sign_one_elf(binary)
        except Exception as exc:
            try:
                self.output.warning("[hmbs] sign failed")
            except Exception:
                pass
            return False
        return ok

    def _find_test_binary(self):
        for folder in (self.build_folder, self.source_folder):
            if not folder:
                continue
            for root, _dirs, files in os.walk(folder):
                if "unittesttest" in files:
                    return os.path.join(root, "unittesttest")
        raise ConanException(
            "上游测试可执行文件 unittesttest 未找到（构建可能未包含 test/）")

    def _emit_upstream(self, payload):
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(payload)
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        return line

    def _run_upstream_tests(self):
        """显式重跑上游测试并输出结构化结果（HMBS_UPSTREAM_TEST_RESULT）。

        被测对象是本次刚构建出的静态库。唯一计数来源是测试二进制输出的
        确定性汇总行；汇总行缺失、任一用例失败或用例数漂移即抛错，
        使 conan create 失败（CI 与真机预检同一咽喉）。
        """
        binary = self._find_test_binary()
        log = os.path.join(self.build_folder, "upstream-test-run.log")
        rc = self.run('"%s" > "%s" 2>&1' % (binary, log),
                      cwd=os.path.dirname(binary), ignore_errors=True)
        output = load(self, log)

        passed = failed = None
        for line in output.splitlines():
            m = re.match(
                r"^Tests finished with (\d+) passes and (\d+) failures\.$",
                line.strip())
            if m:
                passed, failed = int(m.group(1)), int(m.group(2))

        if passed is None or failed is None:
            marker = {
                "status": "failed",
                "framework": "custom",
                "command": "test/unittesttest",
                "discovered": self.UPSTREAM_TEST_PASSES,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "missing summary line "
                          "'Tests finished with N passes and M failures' "
                          "(exit code %s)" % rc,
            }
            self._emit_upstream(marker)
            raise ConanException(
                "上游测试未输出汇总行（exit code %s）：\n%s"
                % (rc, output[-2000:]))

        executed = passed + failed
        ok = (rc == 0 and failed == 0 and passed == self.UPSTREAM_TEST_PASSES)
        marker = {
            "status": "passed" if ok else "failed",
            "framework": "custom",
            "command": "test/unittesttest",
            "discovered": executed,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self._emit_upstream(marker)
        if not ok:
            raise ConanException(
                "上游测试未全部通过（exit code %s, passes=%s, failures=%s, "
                "期望 passes=%d）：\n%s"
                % (rc, passed, failed, self.UPSTREAM_TEST_PASSES,
                   output[-2000:]))

    def package(self):
        # 上游手写 Makefile.in 的 install 目标不支持 DESTDIR（真机证据：
        # `make install DESTDIR=<pkg>` 仍执行 `mkdir -p //share/unittest`
        # 直写主机根并 Permission denied，Makefile:31: install Error 1）。
        # 故不再调用 `make install`（亦避开其 `install: test` 依赖重跑
        # 测试二进制）。in-source 构建产物布局固定，手动复制与上游
        # install 等效的消费者子集（库 + 公共头；datadir 下 docs 仅文档，
        # 不影响消费者编译链接）：
        #   lib/libunittest.a → <pkg>/lib/
        #   include/*.hpp|*.tpp → <pkg>/include/unittest/
        #   COPYING → <pkg>/licenses/
        copy(self, "libunittest.a",
             src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include", "unittest"),
             keep_path=False)
        copy(self, "*.tpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include", "unittest"),
             keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["unittest"]
