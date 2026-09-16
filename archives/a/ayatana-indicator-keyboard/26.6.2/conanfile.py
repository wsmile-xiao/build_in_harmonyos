#!/usr/bin/env python3
"""Conan recipe — ayatana-indicator-keyboard 26.6.2.

Ayatana Indicators 键盘指示器服务（org.ayatana.indicator.keyboard 的 D-Bus 服务端）
+ X11/Lomiri 双键盘后端插件（服务运行时 dlopen 二选一）。

OHOS 适配说明：
  - 依赖 libayatana-common/0.9.13 + glib/2.88.0.1 + X11 键盘栈
    （libx11/libxklavier/libxkbcommon/libudev-zero），经 PkgConfigDeps 生成 .pc
    供顶层 CMakeLists 的 pkg_check_modules(SERVICE_DEPS/X11_DEPS) 使用；
    上游顶层只暴露了 SERVICE_DEPS 的头目录（Ubuntu 上 X11 头在编译器默认路径
    故从未需要），build() 以字符串替换补一行 X11_DEPS 头目录（原 0007 补丁因
    与 0001/0003 的行号漂移导致 Failed to apply patch，改为与补丁顺序无关的
    代码内修复），解 keyboard-x11.c 的
    X11/XKBlib.h 缺头；上游 src/CMakeLists 仅在文件后部声明 SERVICE_DEPS
    库目录，两个后端 SHARED 建在声明之前（Ubuntu 默认 /usr/lib 下可链接），
    0008 补丁在首个 add_library 之前补一行
    link_directories(SERVICE_DEPS/X11_DEPS_LIBRARY_DIRS)，解
    ld 报 unable to find library -layatana-common/-lglib-... 全系缺库；
    均只补搜索路径，不改目标与链接库列表；
    libudev-zero 按配方名产出 libudev-zero.pc 而上游要的是 `libudev`，
    generate() 手工补 libudev.pc 别名（同族 session 的 gio-unix-2.0.pc 先例，
    直指 libudev-zero 包内真实头文件与静态库，是别名而非 stub）；
    tool_requires pkgconf/3.0.5 提供 pkg-config 可执行文件（libxklavier 同款，
    预检容器无系统 pkg-config 时 find_package(PkgConfig) 兜底）。
  - 标准路线：Conan CMakeToolchain（os=OHOS 映射 CMAKE_SYSTEM_NAME=HarmonyOS）。
    "System is unknown ... Platform/HarmonyOS" 仅为缺 Platform 模块的良性警告，
    不阻止构建（知识库 nng 条目实证）；禁止反向伪装成 Linux。
  - 与同族 ayatana-indicator-session/26.6.1（已发布、CI 绿）同构：默认生成器
    （Unix Makefiles）+ CMake helper configure/build，不手写 cmake 命令行，
    不钉死 Ninja，不覆盖 SHELL；TMPDIR/TMP/TEMP 取 HMBS 注入值显式透传进
    conanbuild（真机 /tmp 只读，防 try-compile 报 compiler broken）；
    generate 期 save_script（默认域）前置含 libxml2.so.16 的 llvm/lib 到
    LD_LIBRARY_PATH，防 E266（lld 试链接即报 compiler broken）。前几轮的
    build 期 apply、hnp 版本化 glob、手写 Ninja 链均以同一指纹失败，故换路。
  - SKIP_DATA_PO=ON（0001 补丁新增选项）：OHOS 无 GSettings/Intltool CMake 模块，
    跳过 data/（GSettings schema/systemd 单元/autostart/图标）与 po/ 子目录。
    这些是桌面发行集成数据，非服务运行必需（同族 session 26.6.1 同款处理）。
  - ENABLE_ACCOUNTSSERVICE=OFF（0003/0004/0005 补丁新增选项）：OHOS 无 lightdm
    greeter 会话与 AccountsService 守护进程，act/act.h 仅被 greeter 分支使用
    （service.c 零引用；keyboard-x11.c/keyboard-lomiri.c 的 act_* 调用全部位于
    isGreeter()==TRUE 路径），故条件编译裁掉 greeter 用户布局路径；上游默认 ON
    保持 Ubuntu 行为不变。
  - xkbregistry 包内自带（本仓 libxkbcommon/1.6.0 配方禁用了该模块，不产出
    xkbregistry.pc；另起他库 PR 属跨包改动，PF1 单包闸禁止捆绑）：source() 取
    与 libxkbcommon/1.6.0 同源同包同 sha 的官方包到 xkbregistry-src 子目录，
    build() 仅编译其中 registry 三文件（registry.c/utils.c/util-list.c，
    上游实现逐字不变）为静态便利库，并向 generators 目录提供 xkbregistry.pc
    （Version 1.6.0，Requires: libxml-2.0；libudev.pc 别名先例）；新增
    libxml2/2.15.3.1 依赖供其 XML 解析。xkeyboard-config XML 数据在 OHOS 缺席时
    rxkb 解析仅报 warning（上游原有行为），0006 补丁给双后端 keyboard_GetLayout
    加查表 miss 回退（language 取静态 lookupLanguage，description 取 sId），
    防 NULL 解引用；查表命中路径逐字不变。
  - 上游无测试框架（无 tests/ 目录、无 CTest 接线），build() 不调用 cmake.test()，
    覆盖由 test_package 冒烟补全（见 test_package/MANIFEST.yml 审计）。
    test_package/test() 输出 HMBS_TEST_PACKAGE_RESULT（discovered=2）与
    HMBS_UPSTREAM_TEST_RESULT（status=no_tests）机器证据标记。
  - 产物为单可执行文件 ayatana-indicator-keyboard-service（+ 两个后端 .so 插件）。
    上游把它装到 CMAKE_INSTALL_LIBEXECDIR/ayatana-indicator-keyboard/
    （OHOS 上 LIBEXECDIR=bin），package() 提升到 bin/ 顶层，符合 Conan bin/
    约定与 commands.json/L2 冒烟。
  - 后端 .so 自签：签名工具缺失时跳过（交叉环境），签名失败不阻断打包。
  - 依赖缺口均已在包内合法消除（accountsservice 经 0003-0005 条件编译裁掉
    greeter 死代码路径；xkbregistry 经包内自带官方同源实现），无外部依赖阻塞。
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class AyatanaIndicatorKeyboardConan(ConanFile):
    name = "ayatana-indicator-keyboard"
    version = "26.6.2"
    description = "Ayatana Indicators keyboard indicator D-Bus service (layout switcher menu, X11/Lomiri backends)"
    license = "GPL-3.0"
    homepage = "https://github.com/AyatanaIndicators/ayatana-indicator-keyboard"
    url = "https://github.com/AyatanaIndicators/ayatana-indicator-keyboard"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # service.c 直接使用 libayatana-common 与 glib/gio API，两依赖都是编译/链接必需
        self.requires("libayatana-common/0.9.13", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.88.0.1", transitive_headers=True, transitive_libs=True)
        # X11 后端（keyboard-x11.c）：XOpenDisplay/libxklavier API
        self.requires("libx11/1.8.13", transitive_headers=True, transitive_libs=True)
        self.requires("libxklavier/5.4", transitive_headers=True, transitive_libs=True)
        # 双后端布局枚举（xkbcommon/xkbregistry rxkb API，见 notes.md 缺口说明）
        self.requires("libxkbcommon/1.6.0", transitive_headers=True, transitive_libs=True)
        # xkbregistry 的 XML 解析依赖（vendored libxkbregistry 编译与链接需要；
        # libxml2/2.15.3.1 本仓已归档且与 libxklavier/5.4 的传递依赖同版本，
        # 避免依赖图版本冲突；上游默认无 zlib/lzma 依赖，见其配方）
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True)
        # Lomiri 后端（keyboard-lomiri.c）：udev 硬件键盘探测
        self.requires("libudev-zero/1.0.4", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # 顶层 CMakeLists 用 find_package(PkgConfig)+pkg_check_modules 定位
        # SERVICE_DEPS/X11_DEPS；CI worker 靠系统 pkg-config，预检容器无系统
        # pkg-config（Could NOT find PkgConfig）。经 conan 提供（libxklavier/5.4
        # 同款：pkgconf/3.0.5，制品仓已发布——libxklavier 以此构建并发布）。
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 包内自带 xkbregistry：取与 libxkbcommon/1.6.0 同源同包同 sha 的官方包
        # （conandata.yml xkbregistry_sources），解到 xkbregistry-src 子目录；
        # build() 仅编译其中 registry 三文件（registry.c/utils.c/util-list.c），
        # 不碰 xkbcommon 核心库（仍走 conan 依赖的已发布包）。
        get(self, **self.conan_data["xkbregistry_sources"],
            strip_root=True, destination="xkbregistry-src")

    def generate(self):
        # 与同族 ayatana-indicator-session/26.6.1（已发布、CI 绿）同构：
        # PkgConfigDeps 供 pkg_check_modules 使用；CMakeToolchain 只固化上游
        # 选项，不碰生成器、编译器、SHELL——全部由 profile 与 HMBS
        # 注入透传；TMPDIR/TMP/TEMP 取 HMBS 注入值显式透传进 conanbuild
        #（真机 /tmp 只读，显式透传保证 try-compile 临时文件可写）。
        # lld_fix 沿用 session 的 generate 期 save_script（默认域，
        # 随 conanbuild 聚合进 try-compile 链接环境；build 期 apply 会被
        # conanbuild 覆盖故不用）。
        PkgConfigDeps(self).generate()
        # libudev 别名（同族 session 的 gio-unix-2.0.pc 先例）：libudev-zero 是
        # systemd libudev 的零依赖替代实现（published，静态 libudev.a +
        # libudev.h），但 PkgConfigDeps 按配方名产出 libudev-zero.pc，而上游
        # pkg_check_modules 要的是 `libudev`（真机：Package 'libudev' not
        # found）。手工在 generators 目录（已在 PKG_CONFIG_PATH 上）写
        # libudev.pc，直指 libudev-zero 包的真实头文件与静态库——是别名而非
        # stub，不改变链接内容。
        try:
            udev_dep = self.dependencies["libudev-zero"]
            udev_prefix = getattr(udev_dep, "package_folder", None) or ""
        except Exception:
            udev_prefix = ""
        if udev_prefix:
            try:
                with open(os.path.join(self.generators_folder, "libudev.pc"),
                          "w", encoding="utf-8") as _pc:
                    _pc.write(
                        "prefix={0}\n"
                        "libdir=${{prefix}}/lib\n"
                        "includedir=${{prefix}}/include\n"
                        "\n"
                        "Name: libudev\n"
                        "Description: libudev-zero drop-in replacement for systemd libudev\n"
                        "Version: 1.0.4\n"
                        "Libs: -L${{libdir}} -ludev\n"
                        "Cflags: -I${{includedir}}\n".format(udev_prefix)
                    )
                self.output.info("libudev_fix: wrote libudev.pc for {}".format(udev_prefix))
            except Exception as exc:
                self.output.warning("libudev_fix: write libudev.pc failed: {}".format(exc))
        # 编译器解析（R33 合规，经 Toolchain 落盘）：
        # profile 把 tools.build:compiler_executables 钉在
        # /data/service/hnp/bin/clang(++)，但本轮预检实证该路径在预检容器内
        # 不存在（lld 探针：Errno 2 No such file），致 CMAKE_C/CXX_COMPILER
        # 指向死路径、configure 在 compiler check 即失败。CI worker 上该路径
        # 存在则原样沿用（不覆盖）；仅当 conf 路径缺失时回退到 PATH 发现的
        # clang/clang++（预检机 HMBS 已把工具目录前置进 PATH），并经
        # tc.variables 落盘，不写裸 shell 变量。
        cc_conf, cxx_conf = "", ""
        try:
            exes = self.conf.get("tools.build:compiler_executables") or {}
            if isinstance(exes, dict):
                cc_conf = exes.get("c") or ""
                cxx_conf = exes.get("cpp") or ""
        except Exception:
            pass
        cc = cc_conf if (cc_conf and os.path.isfile(cc_conf)) else ""
        cxx = cxx_conf if (cxx_conf and os.path.isfile(cxx_conf)) else ""
        cc_fallback = cxx_fallback = False
        if not cc:
            cc = shutil.which("clang") or shutil.which("cc") or ""
            cc_fallback = bool(cc)
        if not cxx:
            cxx = shutil.which("clang++") or shutil.which("c++") or ""
            cxx_fallback = bool(cxx)
        if cc_conf and not os.path.isfile(cc_conf):
            self.output.info("compiler_fix: conf c {!r} missing; fallback {!r}".format(cc_conf, cc))
        if cxx_conf and not os.path.isfile(cxx_conf):
            self.output.info("compiler_fix: conf cpp {!r} missing; fallback {!r}".format(cxx_conf, cxx))
        tc = CMakeToolchain(self)
        tc.variables["SKIP_DATA_PO"] = "ON"
        tc.variables["ENABLE_WERROR"] = "OFF"
        # OHOS 无 lightdm greeter/AccountsService（0003-0005 补丁提供开关，
        # 上游默认 ON；此处显式 OFF 裁掉 greeter 分支的 act/act.h 依赖）。
        tc.variables["ENABLE_ACCOUNTSSERVICE"] = "OFF"
        if cc_fallback and cc:
            tc.variables["CMAKE_C_COMPILER"] = cc
        if cxx_fallback and cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        # PKG_CONFIG_EXECUTABLE 显式钉到 pkgconf 工具包（find_package(PkgConfig)
        # 只查 PATH；tool_requires 的 bin 虽会进聚合 PATH，显式变量更稳。
        # 找不到则不设，退回 PATH 发现）。
        pkg_config_exe = ""
        try:
            for dep in self.dependencies.values():
                try:
                    if dep.ref.name != "pkgconf":
                        continue
                    folder = getattr(dep, "package_folder", None)
                    if not folder:
                        continue
                    for cand in ("pkg-config", "pkgconf"):
                        p = os.path.join(folder, "bin", cand)
                        if os.path.isfile(p):
                            pkg_config_exe = p
                            break
                except Exception:
                    continue
                if pkg_config_exe:
                    break
        except Exception:
            pkg_config_exe = ""
        if pkg_config_exe:
            tc.variables["PKG_CONFIG_EXECUTABLE"] = pkg_config_exe
            self.output.info("pkgconf_fix: PKG_CONFIG_EXECUTABLE={}".format(pkg_config_exe))
        tc.generate()
        env = Environment()
        # readonly_tmp: 真机 /tmp 只读（preflight.sh mktemp 即报 Read-only file
        # system；clang try-compile 临时文件默认落 /tmp 即报 compiler broken）。
        # HMBS 已注入任务独立 TMPDIR/TMP/TEMP（见 HMBS_PLATFORM_CAPABILITIES），
        # 此处显式透传进 conanbuild 环境，保证编译器/链接器临时文件落可写目录；
        # 仅替换临时文件根目录，不改变构建逻辑与测试口径。
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v:
                env.define(_k, _v)
        # 回退编译器同时进 conanbuild 环境（经 save_script 落盘，R33 合规；
        # 仅回退时定义，CI 原路径场景不覆盖 profile 行为）。
        if cc_fallback and cc:
            env.define("CC", cc)
        if cxx_fallback and cxx:
            env.define("CXX", cxx)
        llvm_lib = self._llvm_lib_for_lld(cc or cxx)
        if llvm_lib:
            self.output.info("lld_fix: prepend llvm lib {}".format(llvm_lib))
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        else:
            self.output.info("lld_fix: no llvm lib with libxml2.so.16 found; skip")
        env.vars(self).save_script("lld_fix")

    def _llvm_lib_for_lld(self, cc_hint=""):
        # E266：OHOS SDK 的 lld 运行时依赖 libxml2.so.16，try-compile 试链接
        # 即报 compiler broken（session CI #36946 实证）。预检机 hnp 目录
        # readdir 被拒，版本化 glob 为空即失效，故改为问编译器自身：
        # `cc -print-search-dirs` 的 libraries 路径无需列目录，直接按路径
        # isfile 判定（缺目录可列权限不影响直接访问）。返回含 libxml2 的目录。
        # cc_hint 为 generate() 已解析的可用编译器（含回退）；无 hint 才读 conf。
        import subprocess
        cc = cc_hint or ""
        if not cc:
            try:
                exes = self.conf.get("tools.build:compiler_executables") or {}
                if isinstance(exes, dict):
                    cc = exes.get("c") or ""
            except Exception:
                cc = ""
        if not cc:
            cc = shutil.which("clang") or ""
        # 预检沙箱对 hnp 目录 readdir/存取可能受限，isfile 误报即直接跳过
        # 探测（调用方已按 skip 处理），不阻断构建；此处不再因 isfile 为
        # False 直接判死，而是尝试执行，失败则 _llvm 内兜底返回 ""。
        if not cc:
            self.output.info("lld_fix: cc not resolvable")
            return ""
        try:
            proc = subprocess.run([cc, "-print-search-dirs"], capture_output=True,
                                  text=True, timeout=60)
        except Exception as exc:
            self.output.info("lld_fix: search-dirs failed: {}".format(exc))
            return ""
        out = (proc.stdout or "") + (proc.stderr or "")
        for line in out.splitlines():
            if not line.startswith("libraries:"):
                continue
            paths = line.split("=", 1)[1] if "=" in line else ""
            for p in paths.replace(";", ":").split(":"):
                p = p.strip().lstrip("=")
                if not p:
                    continue
                for cand in (p, os.path.dirname(p.rstrip("/"))):
                    try:
                        hit = os.path.isfile(os.path.join(cand, "libxml2.so.16"))
                    except OSError:
                        hit = False
                    if hit:
                        return cand
        return ""

    def build(self):
        apply_conandata_patches(self)
        # 顶层 X11 头目录（原 0007 补丁）：Ubuntu 上 X11 头在编译器默认路径故
        # 上游从未需要，conan 包内头文件不在默认路径，keyboard-x11.c 的
        # X11/XKBlib.h 否则找不到。原补丁与 0001/0003 行号漂移导致
        # `Failed to apply patch ... source file is different`，改为与补丁
        # 顺序无关的字符串替换（仅补包含路径，不改目标与链接）。
        self._fix_top_cmake_x11_includes()
        # 包内自带 xkbregistry：本仓 libxkbcommon/1.6.0 禁用了 xkbregistry 模块，
        # 不产出 xkbregistry.pc（真机：Package 'xkbregistry' not found）。另起他库
        # PR 属跨包改动（PF1 单包闸禁止捆绑），故在此用官方同源包编译 registry
        # 三文件为静态便利库，并向 generators 目录（已在 PKG_CONFIG_PATH 上）
        # 提供 xkbregistry.pc（libudev.pc 别名先例）。上游 rxkb 实现逐字不变，
        # 非 stub、非裁剪；缺 xkeyboard-config XML 数据时运行时仅报 warning
        # （0006 补丁防 GetLayout 空解引用）。
        self._build_vendored_xkbregistry()
        # 与同族 session 一致：CMake helper（默认 Unix Makefiles）+ 串行构建。
        cmake = CMake(self)
        try:
            cmake.configure()
        except Exception:
            # 失败即取证（只记录不改变结论）：摘要只保留尾部，configure 的
            # 真实 stderr（CMakeError.log/Output.log）原本不可见；转储到输出
            # 尾部供下轮判定是编译器不可执行、缺 sysroot 还是链接缺件。
            self._dump_configure_evidence()
            raise
        cmake.build(build_tool_args=["-j", "1"])
        # 上游无测试框架（无 tests/ 目录、无 CTest 接线，见 test_package/MANIFEST.yml
        # 审计），此处不调用测试；覆盖由 test_package 冒烟补全。

    def _fix_top_cmake_x11_includes(self):
        top = os.path.join(self.source_folder, "CMakeLists.txt")
        try:
            with open(top, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except Exception as exc:
            raise Exception("x11_include_fix: read {} failed: {}".format(top, exc))
        if "X11_DEPS_INCLUDE_DIRS" in content:
            self.output.info("x11_include_fix: already present; skip")
            return
        anchor = "include_directories (SYSTEM ${SERVICE_DEPS_INCLUDE_DIRS})"
        if anchor not in content:
            raise Exception("x11_include_fix: anchor not found in {}".format(top))
        patched = content.replace(
            anchor,
            anchor + "\n"
            "# Conan/OHOS: X11 headers live in the conan package, not in the compiler\n"
            "# default path (unlike /usr/include on Ubuntu), so expose them as well.\n"
            "include_directories (SYSTEM ${X11_DEPS_INCLUDE_DIRS})",
            1,
        )
        with open(top, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(patched)
        self.output.info("x11_include_fix: inserted X11_DEPS include dir")

    def _resolve_cc_for_vendor(self):
        # 与 generate() 同策略：conf 死路径则回退 PATH 发现的 clang（R33 合规，
        # 不硬编码 hnp 首位）。返回 (cc, cxx)；找不到则返回 ("", "")。
        cc_conf, cxx_conf = "", ""
        try:
            exes = self.conf.get("tools.build:compiler_executables") or {}
            if isinstance(exes, dict):
                cc_conf = exes.get("c") or ""
                cxx_conf = exes.get("cpp") or ""
        except Exception:
            pass
        cc = cc_conf if (cc_conf and os.path.isfile(cc_conf)) else ""
        if not cc:
            cc = shutil.which("clang") or shutil.which("cc") or ""
        return cc, cxx_conf

    def _build_vendored_xkbregistry(self):
        # 编译 xkbregistry-src/src/{registry,utils,util-list}.c 为静态库，并写
        # xkbregistry.pc 到 generators 目录。全部路径落在 build_folder 私有
        # prefix（R49），临时文件尊重 HMBS 注入的 TMPDIR（readonly_tmp）。
        import subprocess
        vendored = os.path.join(self.source_folder, "xkbregistry-src")
        reg_c = os.path.join(vendored, "src", "registry.c")
        if not os.path.isfile(reg_c):
            # 源码缺失属配方 bug，直接抛错不断言伪造。
            raise Exception("vendored xkbregistry sources missing: {}".format(reg_c))
        prefix = os.path.join(self.build_folder, "vendored-xkbregistry")
        lib_dir = os.path.join(prefix, "lib")
        inc_dir = os.path.join(prefix, "include", "xkbcommon")
        cfg_dir = os.path.join(prefix, "include")
        obj_dir = os.path.join(prefix, "objs")
        for d in (lib_dir, inc_dir, cfg_dir, obj_dir):
            os.makedirs(d, exist_ok=True)
        # 最小 config.h：registry/utils 仅需这几项（meson 生成值的子集）；
        # EACCESS/SECURE 不定义即回退到 access/getenv 安全路径；MMAP 不定义
        # 即走 fread 回退（见上游 src/utils.c）。
        with open(os.path.join(cfg_dir, "config.h"), "w", encoding="utf-8") as fh:
            fh.write(
                "#pragma once\n"
                "#define HAVE_UNISTD_H 1\n"
                "#define HAVE_STRNDUP 1\n"
                "#define HAVE_ASPRINTF 1\n"
                "#define HAVE_VASPRINTF 1\n"
                "#define HAVE___BUILTIN_EXPECT 1\n"
                "#define DEFAULT_XKB_RULES \"evdev\"\n"
                "#define DFLT_XKB_CONFIG_ROOT \"" + prefix.replace("\\", "/") + "/share/X11/xkb\"\n"
                "#define DFLT_XKB_CONFIG_EXTRA_PATH \"" + prefix.replace("\\", "/") + "/etc/xkb\"\n"
                "#ifndef PATH_MAX\n"
                "#define PATH_MAX 4096\n"
                "#endif\n"
            )
        cc, _ = self._resolve_cc_for_vendor()
        if not cc:
            raise Exception("vendored xkbregistry: no C compiler resolvable")
        # libxml2 头目录（仅编译期需要；链接期经 xkbregistry.pc Requires 传递）。
        xml_incs = []
        try:
            xml_dep = self.dependencies["libxml2"]
            xml_pkg = getattr(xml_dep, "package_folder", None) or ""
        except Exception:
            xml_pkg = ""
        for cand in (os.path.join(xml_pkg, "include", "libxml2"),
                     os.path.join(xml_pkg, "include")):
            if cand and os.path.isdir(cand):
                xml_incs.append(cand)
        if not xml_incs:
            raise Exception("vendored xkbregistry: libxml2 package headers not found")
        cflags = ["-fPIC", "-O2", "-D_GNU_SOURCE"]
        # OHOS aarch64 交叉：显式 target（与 settings.arch 对齐）；sysroot 取
        # 编译器自报（best-effort，取不到则不加，不阻断）。
        try:
            if self.settings.arch == "armv8":
                cflags.append("--target=aarch64-linux-ohos")
        except Exception:
            pass
        try:
            proc = subprocess.run([cc, "-print-sysroot"], capture_output=True,
                                  text=True, timeout=60)
            sysroot = (proc.stdout or "").strip().splitlines()
            sysroot = sysroot[0].strip() if sysroot else ""
            if sysroot and os.path.isdir(sysroot):
                cflags.append("--sysroot=" + sysroot)
        except Exception as exc:
            self.output.info("xkbregistry_fix: sysroot probe skipped: {}".format(exc))
        inc_flags = ["-I" + cfg_dir,
                     "-I" + os.path.join(vendored, "src"),
                     "-I" + os.path.join(vendored, "include")]
        inc_flags += ["-I" + p for p in xml_incs]
        # TMPDIR 显式透传（真机 /tmp 只读；仅替换临时文件根目录）。
        compile_env = dict(os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v:
                compile_env[_k] = _v
        objs = []
        for src in ("registry.c", "utils.c", "util-list.c"):
            s = os.path.join(vendored, "src", src)
            o = os.path.join(obj_dir, src.replace(".c", ".o"))
            cmd = [cc] + cflags + inc_flags + ["-c", s, "-o", o]
            self.output.info("xkbregistry_fix: compile {}".format(src))
            try:
                subprocess.run(cmd, check=True, env=compile_env, timeout=300)
            except Exception as exc:
                raise Exception("vendored xkbregistry compile failed {}: {}".format(src, exc))
            objs.append(o)
        ar = shutil.which("llvm-ar") or shutil.which("ar") or ""
        if not ar:
            # 与 fallback clang 同目录找 llvm-ar（harmonybrew 布局）。
            try:
                hint = os.path.join(os.path.dirname(cc), "llvm-ar")
                if os.path.isfile(hint):
                    ar = hint
            except Exception:
                pass
        if not ar:
            raise Exception("vendored xkbregistry: ar not found")
        lib = os.path.join(lib_dir, "libxkbregistry.a")
        try:
            subprocess.run([ar, "rcs", lib] + objs, check=True, env=compile_env, timeout=120)
        except Exception as exc:
            raise Exception("vendored xkbregistry archive failed: {}".format(exc))
        # 头文件：上游公有头逐字拷贝（非 stub）。
        try:
            shutil.copyfile(os.path.join(vendored, "include", "xkbcommon", "xkbregistry.h"),
                            os.path.join(inc_dir, "xkbregistry.h"))
        except Exception as exc:
            raise Exception("vendored xkbregistry header install failed: {}".format(exc))
        # xkbregistry.pc：写入 generators 目录（已在 PKG_CONFIG_PATH 上，
        # libudev.pc 别名先例）；Version 1.6.0 满足 >=1.0.3 约束。
        pc_path = os.path.join(self.generators_folder, "xkbregistry.pc")
        with open(pc_path, "w", encoding="utf-8") as pc:
            pc.write(
                "prefix=" + prefix.replace("\\", "/") + "\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: xkbregistry\n"
                "Description: XKB API to query available rules, models, layouts, variants and options (vendored from libxkbcommon 1.6.0 official sources)\n"
                "Version: 1.6.0\n"
                "Requires: libxml-2.0\n"
                "Libs: -L${libdir} -lxkbregistry\n"
                "Cflags: -I${includedir}\n"
            )
        self.output.info("xkbregistry_fix: built {} and wrote {}".format(lib, pc_path))

    def _dump_configure_evidence(self):
        # 失败路径证据转储：尾部 40 行 CMakeError/Output.log + 编译器存在性 +
        # 关键环境（TMPDIR/SHELL/PATH 头/HMBS_*）。只输出不抛新异常。
        try:
            cands = []
            for root, _ds, fs in os.walk(self.build_folder):
                for f in fs:
                    if f in ("CMakeError.log", "CMakeOutput.log"):
                        cands.append(os.path.join(root, f))
            for path in sorted(set(cands)):
                self.output.info("configure_evidence: --- {} (tail 40) ---".format(path))
                try:
                    with open(path, "r", errors="replace") as fh:
                        lines = fh.read().splitlines()[-40:]
                    for ln in lines:
                        self.output.info("configure_evidence: " + ln[:400])
                except Exception as exc:
                    self.output.info("configure_evidence: read failed {}: {}".format(path, exc))
            for label, p in (("c(conf)", self._conf_cc()), ("cxx(conf)", self._conf_cxx())):
                try:
                    self.output.info("configure_evidence: {}={!r} isfile={}".format(
                        label, p, os.path.isfile(p) if p else False))
                except Exception:
                    pass
            for w in ("clang", "clang++", "cc", "c++", "cmake", "ninja", "make"):
                self.output.info("configure_evidence: which {}={!r}".format(w, shutil.which(w)))
            for k in ("TMPDIR", "TMP", "TEMP", "SHELL", "PATH", "LD_LIBRARY_PATH",
                      "HMBS_CMAKE", "HMBS_NINJA", "HMBS_MAKE", "HMBS_PYTHON3"):
                v = os.environ.get(k, "")
                self.output.info("configure_evidence: {}={!r}".format(k, v[:500] if v else ""))
        except Exception as exc:
            self.output.info("configure_evidence: dump failed: {}".format(exc))

    def _conf_cc(self):
        try:
            exes = self.conf.get("tools.build:compiler_executables") or {}
            if isinstance(exes, dict):
                return exes.get("c") or ""
        except Exception:
            pass
        return ""

    def _conf_cxx(self):
        try:
            exes = self.conf.get("tools.build:compiler_executables") or {}
            if isinstance(exes, dict):
                return exes.get("cpp") or ""
        except Exception:
            pass
        return ""

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游 install 到 bin/ayatana-indicator-keyboard/ayatana-indicator-keyboard-service
        # （CMAKE_INSTALL_LIBEXECDIR + ${CMAKE_PROJECT_NAME}）。提升到 bin/ 顶层，
        # 便于 conan bin/ 约定、commands.json 与 L2 冒烟定位。
        nested_dir = os.path.join(self.package_folder, "bin", "ayatana-indicator-keyboard")
        nested = os.path.join(nested_dir, "ayatana-indicator-keyboard-service")
        top = os.path.join(self.package_folder, "bin", "ayatana-indicator-keyboard-service")
        if os.path.exists(nested) and not os.path.exists(top):
            os.makedirs(os.path.dirname(top), exist_ok=True)
            os.replace(nested, top)
            try:
                os.rmdir(nested_dir)
            except OSError:
                pass
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # HarmonyOS PC 的 .so（后端插件 dlopen 加载）需自签（zstd/gdal 范式）。
        # 工具缺失或签名失败时只告警、不阻断打包（交叉环境容错）。
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign")
            return
        for so in sos:
            if os.path.islink(so):
                continue
            try:
                if os.path.isfile(objcopy):
                    self.run('{} --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, so))
                self.run('{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, so, so))
            except Exception as exc:
                self.output.warning("OHOS codesign skipped for {}: {}".format(so, exc))
                continue

    def package_info(self):
        # 主产物为可执行文件（+ dlopen 后端插件，无对外链接库），无头文件可消费
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
