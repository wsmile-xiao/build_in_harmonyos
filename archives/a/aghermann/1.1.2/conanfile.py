#!/usr/bin/env python3
"""Conan recipe for aghermann 1.1.2 — sleep research experiment manager (GTK+3).

HarmonyOS PC (aarch64) adaptation:
- GTK+3 stack (gtk/glib/cairo/vte) from ohpcd conan registry, private prefix.
- musl fixes: realpath() instead of canonicalize_file_name(), <sys/time.h>,
  argp-standalone for glibc argp.
- clang 15 explicit-template-instantiation order fix in mc-artifacts.cc.
- Upstream bug fix: CEDFFile write mmap MAP_PRIVATE -> MAP_SHARED (edfcat prune
  produced all-zero files).
- AX_PATH_GSL macro re-implemented (removed from modern autoconf-archive).
"""
import os
import re
import glob
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AghermannConan(ConanFile):
    name = "aghermann"
    version = "1.1.2"
    description = "Aghermann — a sleep research experiment manager (GTK+3, EDF/EEG processing)"
    license = "GPL-2.0-or-later"
    homepage = "https://johnhommer.com/academic/code/aghermann"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "os={} not supported (only Linux/OHOS)".format(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GTK+3 stack from ohpcd registry. gtk/3.24.43 already requires
        # glib/2.84.0.1 + cairo/1.18.4 transitively; we depend on those .pc
        # modules directly, so declare them (no version conflict).
        self.requires("gtk/3.24.43")
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("vte/0.74.2")
        self.requires("fftw/3.3.11")
        self.requires("gsl/2.8")
        self.requires("libconfig/1.7.3")
        self.requires("itpp/4.3.1")
        self.requires("libsamplerate/0.2.2")
        self.requires("lua/5.5.0")
        # musl has no glibc argp; edfhed/agh-profile-gen use argp.
        self.requires("argp-standalone/1.5.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    #  generate(): .pc shims + .la fix + toolchain                        #
    # ------------------------------------------------------------------ #
    def generate(self):
        PkgConfigDeps(self).generate()
        self._derive_pc_shims()
        la_dir = self._fix_la_files()
        tc = AutotoolsToolchain(self)
        if la_dir:
            # 前置 _la_fix，保证 libtool 先命中修正版 .la，而不是依赖包 lib 目录
            # 里仍带损坏 libdir='//lib' 的原始 .la（否则会退化为 //lib/libxxx.a 错误）。
            tc.extra_ldflags.insert(0, "-L{}".format(la_dir))
        if self.settings.os == "OHOS":
            # CI #51119：部分 CI worker 的系统路径（~/usr/local/lib）存在
            # libcairo-gobject.so，pkg-config/链接器可能命中它而非 conan 包内
            # 版本；该库引用的 ffi_* 符号（libffi）未随链接传入，ld.lld 默认
            # --no-allow-shlib-undefined 直接报错。本地机器无此系统库故无法
            # 复现。参照 address-standardizer/3.7.0（周期 27，ld.lld 验证过）
            # 注入 --allow-shlib-undefined：容忍共享库的未定义符号，运行时
            # 由系统加载器解析（glib/gobject 已实际加载 libffi）。
            tc.extra_ldflags.append("-Wl,--allow-shlib-undefined")
        tc.configure_args.append("--disable-dependency-tracking")  # HMDFS depcomp bootstrap fails
        # Lua precious variables (AX_PROG_LUA/AX_LUA_LIBS/AX_LUA_HEADERS).
        lua = self.dependencies.get("lua")
        if lua is not None and lua.package_folder:
            tc.configure_args.append("LUA_INCLUDE=-I{}".format(
                os.path.join(lua.package_folder, "include")))
            tc.configure_args.append("LUA_LIB=-L{} -llua".format(
                os.path.join(lua.package_folder, "lib")))
        # argp include + lib (musl).
        argp = self.dependencies.get("argp-standalone")
        if argp is not None and argp.package_folder:
            tc.extra_cflags.append("-I{}".format(os.path.join(argp.package_folder, "include")))
            tc.extra_cxxflags.append("-I{}".format(os.path.join(argp.package_folder, "include")))
            tc.extra_ldflags.append("-L{} -largp".format(os.path.join(argp.package_folder, "lib")))
        # src/common 的 Makefile.am 未带 GSL_CFLAGS/ITPP_CFLAGS（上游依赖系统级
        # include），把全部依赖 include 目录同时注入 CFLAGS/CXXFLAGS 保证
        # gsl/itpp 头在 C++ 编译（clang++，用 CXXFLAGS）中可寻。
        for dep_name, dep in self.dependencies.items():
            if dep.package_folder and os.path.isdir(os.path.join(dep.package_folder, "include")):
                inc = os.path.join(dep.package_folder, "include")
                if inc not in tc.extra_cflags:
                    tc.extra_cflags.append("-I{}".format(inc))
                if inc not in tc.extra_cxxflags:
                    tc.extra_cxxflags.append("-I{}".format(inc))
            if dep_name.ref.name == "glib" and dep.package_folder:
                for sub in ("lib/glib-2.0/include",):
                    s = os.path.join(dep.package_folder, sub)
                    if os.path.isdir(s):
                        if s not in tc.extra_cflags:
                            tc.extra_cflags.append("-I{}".format(s))
                        if s not in tc.extra_cxxflags:
                            tc.extra_cxxflags.append("-I{}".format(s))
        # PKG_CONFIG_PATH: PkgConfigDeps folder + every conan package pkgconfig dir.
        pkgs = [self.generators_folder]
        for dep_name, dep in self.dependencies.items():
            if dep.package_folder:
                for sub in ("lib/pkgconfig", "share/pkgconfig"):
                    d = os.path.join(dep.package_folder, sub)
                    if os.path.isdir(d):
                        pkgs.append(d)
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(":".join(pkgs)))
        env = tc.environment()
        if self.settings.os == "OHOS":
            tools_dir = self._prepend_glib_tools(env)
            # configure.ac 用 AC_PATH_PROGS 探测 glib-compile-resources，
            # 系统 /data/service/hnp/bin 版是坏二进制（ffi 符号缺失）。
            # 显式传变量绕过 PATH 探测，强制用 wrapper。
            if tools_dir:
                tc.configure_args.append(
                    "glib_compile_resources={}".format(
                        os.path.join(tools_dir, "glib-compile-resources")))
            # AX_PROG_LUA 从 PATH 探测 lua 解释器（>=5.1）。conan lua 包的可执行
            # 文件在其 bin/ 下，运行需 LD_LIBRARY_PATH 指向包内 lib。
            if lua is not None and lua.package_folder:
                env.prepend_path("PATH", os.path.join(lua.package_folder, "bin"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(lua.package_folder, "lib"))
        tc.generate(env=env)
        VirtualBuildEnv(self).generate()

    def _derive_pc_shims(self):
        """PkgConfigDeps 不生成 glib 子模块 .pc（gthread/gio-unix/gmodule-export）
        与 libconfig++/samplerate 别名；包内自带 .pc 的 prefix=/ 是坏的，手工派生
        指向真实 conan 包目录的 shim（存 generators_folder，R49 私有前缀）。"""
        gen = self.generators_folder
        glib = self.dependencies.get("glib")
        glib_folder = glib.package_folder if glib and glib.package_folder else None
        if glib_folder:
            glib_pc = os.path.join(gen, "glib-2.0.pc")
            prefix = "${pcfiledir}/../.."
            if os.path.exists(glib_pc):
                m = re.search(r"^prefix=(.+)$", load(self, glib_pc), re.M)
                if m:
                    prefix = m.group(1).strip()
            inc_glib = os.path.join(glib_folder, "include", "glib-2.0")
            inc_glib_lib = os.path.join(glib_folder, "lib", "glib-2.0", "include")
            # gthread-2.0.pc
            self._write_pc(gen, "gthread-2.0.pc",
                           "GThread", "Thread support for GLib", "2.84.0",
                           libs="-L${libdir} -lgthread-2.0",
                           requires="glib-2.0",
                           extra="Cflags: -I${includedir} -I${includedir1} -I${includedir2}",
                           inc1=inc_glib, inc2=inc_glib_lib, prefix=prefix)
            # gio-unix-2.0.pc (headers only)
            self._write_pc(gen, "gio-unix-2.0.pc",
                           "GIO unix specific APIs", "unix headers for glib I/O", "2.84.0",
                           libs="", requires="gobject-2.0, gio-2.0",
                           extra="Cflags: -I${includedir}/gio-unix-2.0",
                           inc1=os.path.join(glib_folder, "include"), inc2="", prefix=prefix)
            # gmodule-export-2.0.pc / gmodule-no-export-2.0.pc
            for name, req in (("gmodule-export-2.0", "gmodule-no-export-2.0, glib-2.0"),
                              ("gmodule-no-export-2.0", "glib-2.0")):
                self._write_pc(gen, name + ".pc",
                               "GModule", "Dynamic module loader for GLib", "2.84.0",
                               libs="-Wl,--export-dynamic", requires=req,
                               extra="Cflags: -I${includedir}",
                               inc1=os.path.join(glib_folder, "include"), inc2="", prefix=prefix)
        # libconfig++.pc — alias of libconfig C++ binding
        libconfig = self.dependencies.get("libconfig")
        if libconfig and libconfig.package_folder:
            self._write_pc(gen, "libconfig++.pc",
                           "libconfig++", "C++ Configuration File Library", "1.7.3",
                           libs="-L${libdir} -lconfig++", requires="",
                           extra="Cflags: -I${includedir}",
                           inc1=os.path.join(libconfig.package_folder, "include"), inc2="",
                           prefix=os.path.join(libconfig.package_folder, "").rstrip("/"))
        # samplerate.pc — alias of libsamplerate (configure.ac checks 'samplerate')
        lrs = self.dependencies.get("libsamplerate")
        if lrs and lrs.package_folder:
            self._write_pc(gen, "samplerate.pc",
                           "samplerate", "Conan package: libsamplerate", "0.2.2",
                           libs='-L"${libdir}" -lsamplerate', requires="",
                           extra='Cflags: -I"${includedir}"',
                           inc1=os.path.join(lrs.package_folder, "include"), inc2="",
                           prefix=lrs.package_folder)

    def _write_pc(self, gen, fname, name, desc, version, libs, requires, extra,
                  inc1, inc2, prefix):
        lines = [
            "prefix={}".format(prefix),
            "libdir=${prefix}/lib",
            "includedir={}".format(inc1),
        ]
        if inc2:
            lines.append("includedir1={}".format(inc2))
            lines.append("includedir2={}".format(inc2))
        lines += [
            "",
            "Name: {}".format(name),
            "Description: {}".format(desc),
            "Version: {}".format(version),
        ]
        if requires:
            lines.append("Requires: {}".format(requires))
        if libs:
            lines.append("Libs: {}".format(libs))
        if extra:
            lines.append(extra)
        save(self, os.path.join(gen, fname), "\n".join(lines) + "\n")

    def _fix_la_files(self):
        r"""E236: libtool .la 依赖元数据在 conan 重定位后带损坏路径（libdir='//lib'、
        dependency_libs 里的 ${libdir}/libxxx.a、/libxxx.a、//lib/libxxx.la 等），
        复制到构建私有目录 _la_fix 并改写为真实存在的绝对路径。

        v3 重写（修复 CI #50377 line 38 引号未闭合）：
        - 逐行、严格在引号内改写 libdir/dependency_libs，绝不跨行、绝不吞掉引号
          （旧版 `\s+//lib/[^\s]*` 的 [^\s]* 会连同行尾 ' 一并删除，导致依赖
          .la 语法损坏 → libtool/sh "unexpected EOF while looking for matching
          ''"，libdir 解析失败退化为 /libpcre2-posix.a 链接错误）。
        - dependency_libs 逐 token 改写：基名为 lib*.a/.so/.la 且前缀损坏的引用
          统一替换为真实路径；.la 兄弟引用指向 _la_fix 内修正版（链式 .la 也
          读修正版），.a/.so 指向依赖包真实 lib 目录；纯损坏前缀垃圾丢弃。
        - 不再就地回写依赖缓存原文件：那会让本地缓存被先修正，与 CI 干净缓存
          行为不一致（本地通过、CI 失败的根源之一）。每次构建都从原始状态出发，
          保证本地与 PR CI 一致。
        """
        if self.settings.os != "OHOS":
            return ""
        la_dir = os.path.join(self.build_folder, "_la_fix")
        os.makedirs(la_dir, exist_ok=True)
        # basename -> 真实绝对路径：.a/.so 指向依赖包 lib 目录；.la 用 la_dir 修正版
        lib_file_to_path = {}
        for dep_name, dep in self.dependencies.items():
            if dep.package_folder is None:
                continue
            dep_lib = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(dep_lib):
                for f in os.listdir(dep_lib):
                    lib_file_to_path.setdefault(f, os.path.join(dep_lib, f))

        def _rewrite_line(line, dep_lib):
            # 严格行级：仅当整行形如  key='value' 时在引号内改写，永不吞引号/跨行
            m = re.match(r"^([A-Za-z_]+)='(.*)'\s*$", line)
            if not m:
                return line
            key, val = m.group(1), m.group(2)
            if key == "libdir":
                if not val or val in ("//lib", "/lib") or not os.path.isdir(val):
                    return "libdir='{}'\n".format(dep_lib)
                return line
            if key == "dependency_libs":
                out = []
                for tok in val.split():
                    if tok.startswith("${libdir}") or tok.startswith("/"):
                        base = tok.replace("${libdir}", "").lstrip("/").rsplit("/", 1)[-1]
                        if re.match(r"^lib[^\s']*\.(?:a|so|la)$", base):
                            if base.endswith(".la"):
                                fixed = os.path.join(la_dir, base)
                                if os.path.exists(fixed):
                                    out.append(fixed)
                                    continue
                            real = lib_file_to_path.get(base)
                            if real:
                                out.append(real)
                                continue
                        # 纯损坏前缀（${libdir}、/lib、//lib、/lib/ 等无库名）→ 丢弃
                        if re.match(r"^(?:\$\{libdir\}|/+)lib/?$", tok):
                            continue
                    out.append(tok)
                return "dependency_libs='{}'\n".format(" ".join(out))
            return line

        for dep_name, dep in self.dependencies.items():
            if dep.package_folder is None:
                continue
            dep_lib = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(dep_lib):
                continue
            for f in sorted(os.listdir(dep_lib)):
                if not f.endswith(".la"):
                    continue
                src = os.path.join(dep_lib, f)
                text = load(self, src)
                fixed = "".join(_rewrite_line(l, dep_lib) for l in text.splitlines(keepends=True))
                save(self, os.path.join(la_dir, f), fixed)
        self.output.info("Fixed dependency .la files into {} (quote-safe, no cache write)".format(la_dir))
        return la_dir

    def _prepend_glib_tools(self, env):
        """glib-compile-resources/glib-genmarshal 等工具从 conan glib 包取，
        wrapper 补 LD_LIBRARY_PATH 后前置 PATH（configure AC_CHECK_PROG 查找）。

        返回 tools_dir（供调用方显式传 glib_compile_resources 变量绕过系统
        坏二进制 /data/service/hnp/bin/glib-compile-resources，其 ffi 符号缺失）。

        E511（CI #51312）：部分 CI worker 的 HMDFS 拒绝执行 conan 缓存内未签名
        的 ELF（exec 报 "Operation not permitted"，本地可复现与否取决于签名
        校验状态，属环境差异）。参照知识库 E318/E486 及 acme-client 配方：
        把工具复制到构建目录，llvm-objcopy 移除旧 .codesign 后 binary-sign-tool
        自签再执行。签名失败（无签名工具等）降级为原路径，保持旧行为。"""
        glib = self.dependencies.get("glib")
        if glib is None or glib.package_folder is None:
            self.output.warning("glib dependency not available; glib tools skipped")
            return None
        glib_bin = os.path.join(glib.package_folder, "bin")
        glib_lib = os.path.join(glib.package_folder, "lib")
        # glib 工具运行需要 libffi/glib 等全部依赖库，LD_LIBRARY_PATH 收集所有
        # 依赖包的 lib 目录（不只 glib），否则 relocation 报 ffi 符号缺失。
        all_libs = []
        for _dep_name, dep in self.dependencies.items():
            if dep.package_folder and os.path.isdir(os.path.join(dep.package_folder, "lib")):
                lib = os.path.join(dep.package_folder, "lib")
                if lib not in all_libs:
                    all_libs.append(lib)
        if glib_lib not in all_libs:
            all_libs.append(glib_lib)
        ld_library_path = ":".join(all_libs)
        tools_dir = os.path.join(self.build_folder, "_glib_tools")
        os.makedirs(tools_dir, exist_ok=True)
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        can_sign = os.path.isfile(objcopy) and os.path.isfile(signer)
        for tool in ("glib-compile-resources", "glib-compile-schemas", "gdbus"):
            real = os.path.join(glib_bin, tool)
            if not os.path.isfile(real):
                continue
            # E511: 缓存内 ELF 可能被 HMDFS 拒绝执行（未签名）→ 复制 + 自签。
            # 签名成功用副本；失败则回退原二进制（本地已能执行的环境不受影响）。
            if can_sign:
                copied = os.path.join(tools_dir, tool + ".unsigned")
                try:
                    shutil.copy2(real, copied)
                    self.run("{} --remove-section .codesign {} 2>/dev/null || true".format(objcopy, copied))
                    signed = copied + ".signed"
                    self.run("{} sign -inFile {} -outFile {} -selfSign 1".format(signer, copied, signed))
                    os.replace(signed, copied)
                    os.chmod(copied, 0o755)
                    real = copied
                except Exception as e:
                    self.output.warning("glib tool self-sign failed for {}: {} (fallback to unsigned)".format(tool, e))
                    real = os.path.join(glib_bin, tool)
            wrapper = os.path.join(tools_dir, tool)
            script = (
                "#!/bin/sh\n"
                "export LD_LIBRARY_PATH=\"{ld}\"${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\n"
                "exec \"{real}\" \"$@\"\n"
            ).format(ld=ld_library_path, real=real)
            fd = os.open(wrapper, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(script)
            except Exception:
                os.close(fd)
                raise
        env.prepend_path("PATH", tools_dir)
        return tools_dir

    # ------------------------------------------------------------------ #
    #  build()                                                            #
    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)
        # CI worker 的 /data/service/hnp/bin 只有 autoconf 系列而无 automake/aclocal
        # （E248 平台事实，CI #50264 实测 autoreconf: aclocal failed exit 2）→
        # 不能跑 autoreconf（其第一步 aclocal 即失败）。改用「仅 autoconf」重新生成
        # configure（autoconf 不依赖 automake/aclocal，CI 可用）：
        #   * tarball 自带 aclocal.m4 已含 AX_PATH_GSL 宏（aclocal.m4:27），autoconf
        #     展开后生成含 HAVE_GSL_20 检测的 configure（实测 configure:17140），
        #     从而走 GSL>=2.0 新 API（否则 gsl_multifit_fdfsolver 无 .J 成员报错）
        #   * config.guess/config.sub 为 configure 运行时脚本，补丁直接生效
        #   * gresource 规则由 0041 补丁直接修正 data/ui/Makefile.in，无需 automake
        self._regen_configure_autoconf_only()
        # 补丁使 Makefile.am/config.guess/config.sub mtime 新于 Makefile.in 时，
        # make 会尝试用缺失的 automake/aclocal 重新生成（Error 127）→ E248 mtime 对齐。
        self._align_generated_mtimes()
        self._patch_configure_hmdfs()
        autotools = Autotools(self)
        autotools.configure()
        # -j1 串行在 CI 超时窗口内编不完（GTK 栈全量 >5min），并行加速。
        jobs = os.cpu_count() or 4
        autotools.make(args=["-j{}".format(min(jobs, 8))])

    def _regen_configure_autoconf_only(self):
        """仅用 autoconf 重新生成 configure（不用 autoreconf）。
        autoreconf 第一步就跑 aclocal（automake 的一部分），而鸿蒙 PC 设备
        只提供 autoconf 系列（/data/service/hnp/bin 无 automake/aclocal，见
        E248，CI #50264 实测失败）→ 必须绕开。autoconf 只重生成 configure，
        不生成 Makefile.in（后者由 tarball 自带 + 0041 补丁直接修正）。
        """
        configure = os.path.join(self.source_folder, "configure")
        configure_ac = os.path.join(self.source_folder, "configure.ac")
        if os.path.exists(configure) and os.path.exists(configure_ac):
            self.run("autoconf -f", cwd=self.source_folder)
            self.output.info("Regenerated configure via autoconf-only (no automake/aclocal needed)")

    def _align_generated_mtimes(self):
        """E248 fix-mtime-after-patch：补丁使 acinclude.m4/config.guess/config.sub/
        Makefile.am 的 mtime 新于 aclocal.m4/Makefile.in 时，GNU make 按
        am__aclocal_m4_deps / 'Makefile.in: Makefile.am $(am__configure_deps)'
        判定生成物过期，调用 build-aux/missing aclocal/automake 重新生成；而鸿蒙
        PC 设备仅提供 autoconf 系列（无 automake/aclocal，CI #50264 实测
        'aclocal-1.15: command not found' Error 127），重生成即崩溃。
        处置（零新增依赖，发行包构建不要求完整 autotool 链）：
          1) 所有 Makefile.in mtime 对齐到当前时间（最新，覆盖其全部依赖）；
          2) 被补丁触碰的 autotools 输入（acinclude.m4/config.guess/config.sub/
             Makefile.am）mtime 恢复为 tarball 基准（= configure.ac 的 mtime），
             掐断 aclocal.m4/configure 的重生成触发条件。
        """
        import time
        cfg_ac = os.path.join(self.source_folder, "configure.ac")
        base_ns = os.stat(cfg_ac).st_mtime_ns if os.path.exists(cfg_ac) else time.time_ns()
        now_ns = time.time_ns()
        aligned = 0
        for root, _dirs, files in os.walk(self.source_folder):
            for f in files:
                path = os.path.join(root, f)
                if f == "Makefile.in":
                    os.utime(path, ns=(now_ns, now_ns))
                    aligned += 1
                elif f in ("acinclude.m4", "config.guess", "config.sub", "Makefile.am"):
                    os.utime(path, ns=(base_ns, base_ns))
                    aligned += 1
        self.output.info("Aligned {} generated/autotools-input mtimes to prevent aclocal/automake regen (E248)".format(aligned))

    def _patch_configure_hmdfs(self):
        if self.settings.os != "OHOS":
            return
        import tempfile
        os.environ["PWD"] = self.build_folder
        fixed_tmp = os.path.join(tempfile.gettempdir(), "aghermann-ac-tmp")
        os.makedirs(fixed_tmp, exist_ok=True)
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.exists(cfg):
            text = load(self, cfg)
            if "ac_tmp=$tmp" in text:
                text = text.replace("ac_tmp=$tmp", "ac_tmp={}".format(fixed_tmp))
            old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
            if old_trap in text:
                text = text.replace(old_trap, "exit $exit_status")
            old_acpwd = 'ac_pwd=`pwd` && test -n "$ac_pwd" &&'
            new_acpwd = 'ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\ntest -n "$ac_pwd" &&'
            if old_acpwd in text:
                text = text.replace(old_acpwd, new_acpwd)
            text = text.replace('(umask 077 && mktemp -d "./confXXXXXX")',
                                '(umask 022 && mktemp -d "./confXXXXXX")')
            text = text.replace('(umask 077 && mkdir "$tmp")',
                                '(umask 022 && mkdir "$tmp")')
            save(self, cfg, text)
            os.chmod(cfg, 0o755)
            self.output.info("Patched configure for HMDFS (ac_tmp/ac_pwd/umask)")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # aghermann is an application: GUI (aghermann/edfhed-gtk) + CLI tools
        # (edfcat/edfhed/agh-profile-gen) + private libs under lib/aghermann/.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["sigproc", "sigfile", "metrics"]
        self.cpp_info.libdirs = ["lib/aghermann"]
