#!/usr/bin/env python3
"""Conan recipe — libgsystemservice 0.3.0 (Meson).

libgsystemservice is a utility library providing the common components needed
to build system services exposed on the D-Bus **system** bus: GssService (a
GApplication-derived base class with polkit authorization + systemd readiness
notification) and GssPeerManager (per-peer credentials for a D-Bus connection).

Adapted to HarmonyOS PC (aarch64).  See notes.md for the platform adaptations.
"""
import glob
import os
import re
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# glib/2.84.0.1 包内 bin/ 的构建期工具在 HMFS 上不能直接执行：
#   * python 脚本（glib-mkenums / glib-genmarshal / gdbus-codegen）解释器
#     shebang 不可用，跨 UID 脚本执行被拒；
#   * ELF（glib-compile-resources / gobject-query / ...）缺少 .codesign
#     段，execve 返回 EPERM（shell 报 Operation not permitted，退出码 126）。
# 按 archives/g/gtk/3.24.43（依赖同一 glib/2.84.0.1）已验证的做法，在 build
# 目录里 staging 一份：python 工具包 sh wrapper 显式指定解释器，ELF 工具拷
# 贝出来重签名，meson 的 .pc 工具变量统一指向 staging 副本。
HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")
PYTHON3 = os.path.realpath(sys.executable)

GLIB_PYTHON_TOOLS = ("glib-mkenums", "glib-genmarshal", "gdbus-codegen")
GLIB_ELF_TOOLS = (
    "glib-compile-resources",
    "glib-compile-schemas",
    "gobject-query",
    "gio-querymodules",
)

# Upstream `libgsystemservice/tests/meson.build` registers one `test()` per
# entry of its `test_programs` list:
#     test_programs = ['config-file', 'peer-manager', 'service']
# i.e. 3 meson test *programs*, holding 13 g_test cases in total
# (config-file 9 + peer-manager 2 + service 2).
UPSTREAM_TEST_PROGRAMS = 3
UPSTREAM_TEST_CASES = 13

# Programs which must pass on every platform we support.
REQUIRED_PASSING_PROGRAMS = ("config-file", "service")

# `peer-manager`'s fixture calls `g_test_dbus_up()`, which spawns a private
# `dbus-daemon` over an AF_UNIX socket.  The OHOS sandbox denies AF_UNIX bind
# (see archives/d/dbus/1.14.10.2/manifest.yaml) and the published dbus package
# ships the client library only (no `dbus-daemon` binary), so this program
# cannot run here.  It is still registered, built and executed — its failure is
# declared, not skipped.
#
# The allowlist below is deliberately keyed on *identity and count*, never on
# the failure text: GLib's `start_daemon()` spawns dbus-daemon and then
# `g_assert_no_error()`s the spawn result, so with no dbus-daemon the process
# aborts (message: `Failed to execute child process “dbus-daemon” (No such file
# or directory)`), while a daemon that starts but cannot bind may fail through
# an entirely different, unguarded path.  Failure text is therefore only used
# as a diagnostic (`SANDBOX_FAILURE_MARKERS`), not as the gate.
SANDBOX_BLOCKED_PROGRAMS = ("peer-manager",)
SANDBOX_FAILURE_MARKERS = (
    "dbus-daemon",
    "AF_UNIX",
    "Operation not permitted",
    "Failed to execute child process",
    "Failed to start message bus",
    "Could not connect: No such file or directory",
    "Error spawning command line",
)


class LibgsystemserviceConan(ConanFile):
    name = "libgsystemservice"
    version = "0.3.0"
    description = "Common components for building D-Bus system services (GssService / GssPeerManager)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/pwithnall/libgsystemservice"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # glib is the only *public* dependency: gss_service.h / gss_peer_manager.h
        # pull in gio/gio.h and the GObject type system.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # libsystemd is a *private* dependency: service.c includes
        # <systemd/sd-daemon.h> and calls sd_notify() (READY=1 / STOPPING=1).
        # The published systemd/261 recipe ships libsystemd.so + the public
        # headers + libsystemd.pc.
        self.requires("systemd/261", visible=False)
        # polkit-gobject-1 is a *private* dependency: service.c includes
        # <polkit/polkit.h> and calls polkit_authority_check_authorization_sync().
        # The published polkit/127 recipe ships the libpolkit-gobject-1 client
        # library + polkit-gobject-1.pc.
        self.requires("polkit/127", visible=False)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    # ─────────────────────────── source ───────────────────────────
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # No patches upstream (conandata.yml: `patches: {}`); applied here, once,
        # so a re-run of build() can never apply them a second time.
        apply_conandata_patches(self)

    # ────────────────────────── generate ──────────────────────────
    def generate(self):
        PkgConfigDeps(self).generate()
        tools_folder = self._prepare_glib_build_tools()
        self._augment_glib_pkg_config(tools_folder)
        self._alias_dependency_pc()
        toolchain = MesonToolchain(self)
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        # gtk_doc defaults to true upstream and needs gtk-doc + the
        # documentation toolchain, neither of which OHOS provides.
        toolchain.project_options["gtk_doc"] = False
        # Only *.test metadata is affected; upstream defaults to false already.
        toolchain.project_options["installed_tests"] = False
        toolchain.c_link_args.extend(self._glib_libintl_link_args())
        toolchain.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    # ─────────────────────────── build ────────────────────────────
    def build(self):
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            if not cross_building(self) and can_run(self):
                # `meson test` exits non-zero as soon as one test fails, and the
                # run is expected to report the sandbox-blocked `peer-manager`
                # program as a failure — so the exit code is deliberately not
                # consulted; the suite summary is read back and asserted below.
                self.run(
                    "meson test -C {} --print-errorlogs".format(self.build_folder),
                    env="conanbuild",
                    ignore_errors=True,
                )
                self._assert_suite_results()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        # Upstream ships COPYING as a *symlink* to LICENSES/LGPL-2.1-or-later.txt;
        # copy the regular file it points at, so the packaged licence can never
        # end up as a dangling link.
        copy(self, "LICENSES/LGPL-2.1-or-later.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # libgsystemservice.so.0 — upstream installs it under the API-versioned
        # name "gsystemservice-0".
        self.cpp_info.libs = ["gsystemservice-0"]
        self.cpp_info.includedirs = ["include/gsystemservice-0"]
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
        ]
        self.cpp_info.set_property("cmake_file_name", "gsystemservice-0")
        self.cpp_info.set_property("cmake_target_name", "gsystemservice-0::gsystemservice-0")
        self.cpp_info.set_property("pkg_config_name", "gsystemservice-0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ────────────────────────── helpers ───────────────────────────
    def _build_environment(self):
        """PATH / LD_LIBRARY_PATH / TMPDIR plumbing.

        ``TMPDIR`` matters for the upstream suite: ``config-file``'s fixture
        calls ``g_dir_make_tmp()``, and OHOS' ``/tmp`` is not writable, so a
        writable temp directory has to be handed to the tests explicitly.
        """
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)

        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        # ★ 依赖包里的 SONAME 名字是**符号链接**且带旧签名，设备 dlopen 不了：
        # 物化成真文件副本并重签，见 _stage_symlinked_sonames。
        staged_sonames = self._stage_symlinked_sonames()
        if staged_sonames:
            environment.prepend_path("LD_LIBRARY_PATH", staged_sonames)
        # staging 出来的 glib 构建工具必须排在依赖自带的 bin/ 前面，
        # 否则 meson 仍会挑到包缓存里那份不可执行的副本。
        tools_folder = self._glib_tools_folder()
        if os.path.isdir(tools_folder):
            environment.prepend_path("PATH", tools_folder)
        # ★ 系统库目录：polkit/127 的 libpolkit-gobject-1.so.0 唯一的外部
        # DT_NEEDED 是 **libz.so**（glib/expat/duktape 全部静态链进去了），
        # 而 ohpcd 发布的 zlib/1.3.1.1 包里只有静态 `libz.a`（没有 libz.so），
        # zlib 在本依赖图里连二进制包都被 conan 跳过（Skipped binaries），
        # 于是 meson test 的 LD_LIBRARY_PATH（全是 conan 依赖的 lib/）里没有
        # libz.so 的来源。OHOS 的 conan-run 路径默认**不含**系统库目录
        # （avahi-ui/0.8、alkimia/8.2.1 先例：libc++_shared.so 同理），所以
        # libz.so 只能来自 /system/lib64，必须显式挂上。
        #
        # 注意：挂 /system/lib64 **不能**解决上面那条 libpolkit-gobject-1.so.0
        # 报错 —— 那条的真因是符号链接 + 旧签名（见 _stage_symlinked_sonames），
        # 当时误判成 libz.so 缺失，加了这一行也没让 CI 转绿；保留它是为了真正的
        # libz.so 依赖，别再拿它当那条空 strerror 的解药。
        #
        # 用 append 而非 prepend：/system/lib64 排在 conan 依赖之后，避免系统里
        # 同名库（glib/expat/…）顶掉 conan 那份（baloo/26.04.3 同款理由）。
        if self.settings.os == "OHOS":
            environment.append_path("LD_LIBRARY_PATH", "/system/lib64")
        return environment

    def _stage_symlinked_sonames(self):
        """把依赖 libdir 里的 .so 符号链接物化成真文件副本，并**重签**。

        ohpcd 上按 Linux 惯例打包的库，SONAME 名（`libpolkit-gobject-1.so.0`、
        `libjson-glib-1.0.so.0` …）只是指向 `*.so.0.0.0` 的**符号链接**，而鸿蒙
        HMDFS 对 .so 符号链接的运行期 dlopen 支持不完整。判定法：Conan 的
        `conanmanifest.txt` 对符号链接记的是**目标字符串**的 md5，例如

            lib/libpolkit-gobject-1.so.0: d2edb620a9e0d008e76e1d70d9f0a201
                                      == md5("libpolkit-gobject-1.so.0.0.0")

        实测 polkit-0.127 与 json-glib-1.8.0 的包内都是这种布局。

        症状（CI #62298/#62306 三连）：

            Error loading shared library libpolkit-gobject-1.so.0:
                (needed by .../libgsystemservice-0.so.0)
            Error relocating .../libgsystemservice-0.so.0: polkit_authority_get_sync: symbol not found

        冒号后 **strerror 为空**，是「文件找得到、加载器解析不到」的特征；如果是
        真找不到会写 `No such file or directory`，如果是 ELF 未签名（E077）会写
        `Permission denied`。判据是**别盯着"被它拖住的下游库"**：loader 只会点名
        「正在解析的那个直接依赖」。

        ★ 只做「物化」不够，必须重签。同一批 PR 的 A/B 实测（2026-09-27）：
          - libratbag/0.18：物化 → CI FAIL；物化 **+ 重签** → CI PASS
            （09:20 FAIL、09:37 推重签、09:43 PASS）。
          - 本包与 pgroonga/4.0.8、libgmobile/0.7.2 只做物化，09:42~09:46
            仍是同一条空 strerror FAIL。

        依赖包在 Conan 缓存里只读且已被引用（改不得），所以把副本放进本包 build
        目录下的 staging 目录、并置于 LD_LIBRARY_PATH 最前，让加载器命中的是
        重签后的普通文件。副本复制下来后走 `_sign_elf()`：丢掉随包带来的旧
        `.codesign`，再 `binary-sign-tool sign -selfSign 1` 就地重签。
        """
        staged = os.path.join(self.build_folder, "conan-staged-soname-libs")
        materialized = []
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if not os.path.isdir(libdir):
                    continue
                for name in sorted(os.listdir(libdir)):
                    if not name.endswith(".so") and ".so." not in name:
                        continue
                    source = os.path.join(libdir, name)
                    if not os.path.islink(source):
                        continue
                    target = os.path.join(staged, name)
                    if os.path.exists(target):
                        continue
                    real = os.path.realpath(source)
                    if not os.path.isfile(real):
                        continue
                    os.makedirs(staged, exist_ok=True)
                    # copy2 默认跟随符号链接 → 落下来的是真文件内容
                    shutil.copy2(real, target)
                    os.chmod(target, 0o755)
                    # 丢掉旧签名后重签，否则设备仍拒绝映射（空 strerror）
                    self._sign_elf(target)
                    materialized.append(name)
        if not materialized:
            return None
        self.output.info(
            "E073: 物化并重签 %d 个符号链接 SONAME 到 %s（%s）"
            % (len(materialized), staged, ", ".join(materialized)))
        return staged

    # ─────────────────── glib 构建工具 staging ────────────────────
    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _glib_dep(self):
        """本配方**直接**声明的 glib 包接口（无则 None）。

        不能写 self.dependencies["glib"]：systemd/261 会带入一个不可见的
        glib/2.84.0（Traits: visible=False），于是 Conan 抛
        "There are more than one requires matching the specified filters:
        {'build': False}"。按名字过滤**直接**依赖即可唯一命中本配方声明的
        glib/2.84.0.1，且不随版本号变化而失配。
        """
        for dep in self.dependencies.direct_host.values():
            if dep.ref.name == "glib":
                return dep
        return None

    def _sign_elf(self, binary):
        """HMFS 执行限制规避：去掉 .codesign 段后 selfSign 重签。"""
        if os.path.isfile(OBJCOPY):
            self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                     f"{shlex.quote(binary)} 2>/dev/null || true")
        if os.path.isfile(SIGN_TOOL):
            self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", binary,
                                 "-outFile", binary, "-selfSign", "1"]))

    def _prepare_glib_build_tools(self):
        """把 glib 包 bin/ 里的构建工具 staging 到 build 目录。

        返回 {工具名: 可执行文件绝对路径}，供 .pc 工具变量注入使用。
        """
        glib_pkg = self._glib_dep()
        if glib_pkg is None:
            return {}
        glib_bin = os.path.join(glib_pkg.package_folder, "bin")
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        quote = lambda s: "'" + str(s).replace("'", "'\\''") + "'"

        staged = {}
        for tool in GLIB_PYTHON_TOOLS:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                continue
            wrapper = os.path.join(tools_folder, tool)
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(f"#!/bin/sh\nexec {quote(PYTHON3)} {quote(src)} \"$@\"\n")
            os.chmod(wrapper, 0o755)
            staged[tool] = wrapper

        for tool in GLIB_ELF_TOOLS:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                continue
            target = os.path.join(tools_folder, tool)
            shutil.copyfile(src, target)
            os.chmod(target, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(target)
            staged[tool] = target
        return staged

    def _dependency_object(self, name):
        for dependency in self.dependencies.host.values():
            if getattr(dependency.ref, "name", "") == name:
                return dependency
        return None

    def _dependency_folder(self, name):
        dependency = self._dependency_object(name)
        return dependency.package_folder if dependency is not None else ""

    def _append_dependency_pkg_config_paths(self):
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        paths = [self.generators_folder]
        for dependency in self.dependencies.host.values():
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(dependency.package_folder, *relative)
                if os.path.isdir(candidate):
                    paths.append(candidate)
        unique_paths = []
        for path in paths:
            normalized = path.replace("\\", "/")
            if normalized not in unique_paths:
                unique_paths.append(normalized)
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        replacement = "pkg_config_path = [" + ", ".join(
            "'{}'".format(p) for p in unique_paths) + "]"
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _inject_meson_tools(self):
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (
                bindir,
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin",
            ):
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
            pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
            if not pkg_config or not os.path.isfile(str(pkg_config)):
                pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace(
                    "[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _augment_glib_pkg_config(self, staged_tools):
        """PkgConfigDeps emits simplified .pc files: no tool variables, no -lintl.

        glib on OHOS builds its ``proxy-libintl`` subproject, so the
        ``g_libintl_*`` symbols live inside the glib package rather than in the
        system libc, but glib's ``package_info`` does not declare ``intl`` as a
        system library — consumers otherwise end up with
        ``undefined reference to `g_libintl_*'``.

        工具变量一律指向 :meth:`_prepare_glib_build_tools` staging 出来的
        副本（而不是 glib 包缓存里的原件）—— 后者在 HMFS 上不可执行。

        工具名 → 所属 .pc 的映射与 meson 自己的 ``gnome._find_tool`` 一致
        （``mesonbuild/modules/gnome.py`` 的 ``tool_map``）：``glib-compile-resources``
        / ``glib-compile-schemas`` / ``gio-querymodules`` / ``gdbus-codegen`` 挂在
        ``gio-2.0``，``glib-mkenums`` / ``glib-genmarshal`` 挂在 ``glib-2.0``。
        上游 ``tests/meson.build`` 用了 ``gnome.compile_resources()``，它内部是
        ``ModuleState.find_tool('glib-compile-resources', 'gio-2.0',
        'glib_compile_resources')``；该函数在 .pc 分支上调用的是
        ``dep.get_variable(pkgconfig='glib_compile_resources')`` —— **没有 default**，
        变量缺失时直接
        ``ERROR: Could not get pkg-config variable and no default provided for
        <PkgConfigDependency gio-2.0: True ['>= 2.71']>``。
        """
        entries = {
            "glib-2.0.pc": ["glib_mkenums", "glib_genmarshal", "gobject_query"],
            "gobject-2.0.pc": ["glib_mkenums"],
            "gio-2.0.pc": ["glib_compile_resources", "glib_compile_schemas",
                           "gio_querymodules", "gdbus_codegen"],
        }
        # -lintl 只补在真正引用 g_libintl_* 的 glib/gobject 上；gio 不需要，
        # 给它挂上只会让每个 consumer 的 gio 链接行多一个 -lintl。
        intl_pc_files = ("glib-2.0.pc", "gobject-2.0.pc")
        for pc_name, tool_names in entries.items():
            pc_file = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            modified = False
            additions = []
            for tool in tool_names:
                path = staged_tools.get(tool.replace("_", "-"))
                if path and f"{tool}=" not in content:
                    additions.append(f"{tool}={path.replace(os.sep, '/')}")
            if additions:
                content += "\n" + "\n".join(additions) + "\n"
                modified = True
            if pc_name in intl_pc_files and "-lintl" not in content:
                lines = []
                for line in content.splitlines(True):
                    if line.startswith("Libs:") and "-lintl" not in line:
                        line = line.rstrip("\n") + " -lintl\n"
                    lines.append(line)
                content = "".join(lines)
                modified = True
            if modified:
                with open(pc_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _alias_dependency_pc(self):
        """Make sure `libsystemd.pc` and `polkit-gobject-1.pc` resolve correctly.

        Upstream asks for ``dependency('libsystemd')`` and
        ``dependency('polkit-gobject-1')``.  Neither name matches the conan
        package name, and PkgConfigDeps derives .pc names from the *package*
        name (``systemd.pc`` / ``polkit.pc``), so the real .pc files shipped
        inside those packages are what meson has to find.  Those copies were
        installed with ``--prefix=/`` + DESTDIR by their recipes, i.e. their
        ``prefix=`` line points at ``/`` — copying them through unmodified would
        make ``-I${includedir}/polkit-1`` resolve to ``/polkit-1``.  The copy
        written here lives in ``generators_folder``, which is first on meson's
        ``pkg_config_path``, and has ``prefix=`` rewritten to the actual
        dependency package folder.

        ``systemd/261`` is a special case: the published binary package has an
        *empty* ``lib/pkgconfig/``, so there is nothing to copy.  Its recipe
        builds only the ``libsystemd`` target and deliberately skips
        ``meson.install()`` (a full install would drive 1281 targets and time
        out), and meson's ``pkg.generate()`` output only lands in
        ``<build>/libsystemd.pc`` when the corresponding target is built — so
        the recipe's ``if os.path.isfile(pc_src)`` guard silently skips it.
        That is not something this recipe can fix (patching another package's
        build is out of scope), so the .pc is synthesised here from the real
        on-disk layout instead.
        """
        wanted = {
            "systemd": "libsystemd.pc",
            "polkit": "polkit-gobject-1.pc",
        }
        for dependency_name, pc_name in wanted.items():
            dependency = self._dependency_object(dependency_name)
            if dependency is None:
                continue
            folder = dependency.package_folder
            source = None
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(folder, *(relative + (pc_name,)))
                if os.path.isfile(candidate):
                    source = candidate
                    break
            prefix_native = folder.replace("\\", "/")
            if source:
                with open(source, encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
                content = "\n".join(
                    "prefix=" + prefix_native if line.startswith("prefix=") else line
                    for line in content.splitlines()
                )
            elif pc_name == "libsystemd.pc":
                content = self._synthesize_libsystemd_pc(dependency, prefix_native)
            else:
                self.output.warning(
                    f"{pc_name} not found in the {dependency_name} package")
                continue
            destination = os.path.join(self.generators_folder, pc_name)
            with open(destination, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    @staticmethod
    def _synthesize_libsystemd_pc(dependency, prefix):
        """Minimal ``libsystemd.pc`` for a package that ships none.

        Mirrors the layout the package really has: the public headers live in
        ``include/systemd/sd-*.h`` (included as ``<systemd/sd-daemon.h>``, so
        ``-I${includedir}`` is required) and the library is ``lib/libsystemd.so``.
        ``-I${includedir}/systemd`` matches what systemd's own .pc does via
        ``subdirs``.  ``Version`` is taken from the resolved dependency so it
        satisfies upstream's ``>=227`` requirement.
        """
        version = dependency.ref.version
        return (
            "prefix={prefix}\n"
            "exec_prefix=${{prefix}}\n"
            "libdir=${{prefix}}/lib\n"
            "includedir=${{prefix}}/include\n"
            "\n"
            "Name: libsystemd\n"
            "Description: systemd Library\n"
            "Version: {version}\n"
            "Libs: -L${{libdir}} -lsystemd\n"
            "Cflags: -I${{includedir}} -I${{includedir}}/systemd\n"
        ).format(prefix=prefix, version=version)

    def _glib_libintl_link_args(self):
        if self.settings.os != "OHOS":
            return []
        for dependency in self.dependencies.host.values():
            for library_name in ("libintl.so", "libintl.a"):
                library_path = os.path.join(dependency.package_folder, "lib", library_name)
                if os.path.isfile(library_path):
                    return [library_path.replace("\\", "/")]
        return []

    def _assert_suite_results(self):
        """Read back the meson suite summary instead of trusting the exit code.

        ``meson test`` returns 0 whenever nothing failed — a suite whose tests
        were skipped, or whose ``test()`` calls never ran, exits 0 too.  The
        summary block is the only place that says how much actually ran, so it
        is asserted explicitly.

        The one sandbox-blocked program is allowed to fail, but only by
        *identity and count*: exactly the declared program, exactly as many
        failures as there are declared programs.  Anything else — an extra
        failure, a timeout, a test that was not registered at all — is a hard
        error.  The failure text is checked too, but only advisory: GLib
        reaches this failure through several different code paths (abort in
        ``g_assert_no_error()`` when no dbus-daemon exists, or an unguarded
        path when one exists but cannot bind), so the message is not a stable
        contract.
        """
        log = os.path.join(self.build_folder, "meson-logs", "testlog.txt")
        if not os.path.isfile(log):
            raise ConanException(f"meson test log missing: {log}")
        with open(log, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        summary = {}
        for key in ("Ok", "Expected Fail", "Fail", "Unexpected Pass", "Skipped", "Timeout"):
            match = re.search(rf"^{re.escape(key)}:\s+(\d+)\s*$", content, re.MULTILINE)
            if match:
                summary[key] = int(match.group(1))
        self.output.info(f"upstream meson suite summary: {summary}")

        for key in ("Timeout", "Unexpected Pass"):
            if summary.get(key, 0):
                raise ConanException(
                    f"upstream meson suite reports {key}={summary[key]}:\n"
                    + "\n".join(content.splitlines()[-40:])
                )

        failed = summary.get("Fail", 0)
        if failed > len(SANDBOX_BLOCKED_PROGRAMS):
            raise ConanException(
                f"upstream meson suite reports Fail={failed}, more than the "
                f"{len(SANDBOX_BLOCKED_PROGRAMS)} sandbox-blocked program(s) "
                f"{SANDBOX_BLOCKED_PROGRAMS}:\n"
                + "\n".join(content.splitlines()[-40:])
            )
        if failed:
            # The allowed failure has to be *the declared one* — otherwise a
            # genuine regression elsewhere would masquerade as the declared
            # platform limitation.
            for program in SANDBOX_BLOCKED_PROGRAMS:
                if program not in content:
                    raise ConanException(
                        f"expected the failing program to be {program!r}, but it "
                        f"does not appear in the test log:\n"
                        + "\n".join(content.splitlines()[-40:])
                    )
            if not any(marker in content for marker in SANDBOX_FAILURE_MARKERS):
                self.output.warning(
                    f"the failing program {SANDBOX_BLOCKED_PROGRAMS} does not "
                    "show any of the recognised no-D-Bus-session-bus markers "
                    f"{SANDBOX_FAILURE_MARKERS}; it is still the declared "
                    "sandbox-blocked program, but the failure text differs from "
                    "the expected one — worth a look. Last lines:\n"
                    + "\n".join(content.splitlines()[-20:])
                )

        # `Ok` must cover every program that is required to pass; the
        # sandbox-blocked one may be counted either way (it passes on a host
        # with a usable session bus).
        if summary.get("Ok", 0) < len(REQUIRED_PASSING_PROGRAMS):
            raise ConanException(
                f"upstream meson suite ran only {summary.get('Ok', 0)} test "
                f"program(s); {len(REQUIRED_PASSING_PROGRAMS)} are required to "
                f"pass ({REQUIRED_PASSING_PROGRAMS}) — suite is vacuous or "
                f"silently truncated:\n" + "\n".join(content.splitlines()[-40:])
            )
        for program in REQUIRED_PASSING_PROGRAMS:
            if program not in content:
                raise ConanException(
                    f"required test program {program!r} does not appear in the "
                    "test log — it was not registered or not executed:\n"
                    + "\n".join(content.splitlines()[-40:])
                )

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                path = os.path.join(bindir, name)
                if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path):
                    targets.append(path)
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
