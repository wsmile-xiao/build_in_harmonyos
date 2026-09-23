#!/usr/bin/env python3
"""Conan recipe — gupnp-av 0.14.5 (Meson).

GUPnP A/V is a small utility library for dealing with UPnP A/V profiles
(DIDL-Lite parsing/writing, MediaServer search criteria, protocol info).
Pure C, LGPL-2.1+, built with Meson, depends only on glib-2.0/gobject-2.0
(>= 2.58) and libxml-2.0. It does NOT depend on gupnp/gssdp themselves.
Adapted to HarmonyOS PC (aarch64). See notes.md for the platform notes.
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GupnpAvConan(ConanFile):
    name = "gupnp-av"
    version = "0.14.5"
    description = "Utility library for UPnP A/V profiles (DIDL-Lite, search criteria, protocol info)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gupnp-av"
    url = "https://gitlab.gnome.org/GNOME/gupnp-av"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
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
        # gupnp-av 0.14.5 上游 meson.build 实测只依赖 gobject-2.0/glib-2.0
        # (>= 2.58) + libxml-2.0；不依赖 gupnp/gssdp（名字带 gupnp 仅生态
        # 归属）。glib2/2.88.0 的 PkgConfigDeps 已直接产出 glib-2.0.pc/
        # gobject-2.0.pc/gio-2.0.pc（Version 2.88.0），无需转发 hack。
        self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        toolchain = MesonToolchain(self)
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        # introspection 默认 true 会拉 g-ir-scanner（本机不可用）；关掉后
        # meson.build 的 vala 子目录（依赖 introspection）与 gtk_doc 一并跳过。
        toolchain.project_options["introspection"] = False
        toolchain.project_options["vapi"] = False
        toolchain.project_options["gtk_doc"] = False
        # tests/ 与 tests/gtest/ 由 meson.build 无条件 subdir('tests') 构建，
        # 上游测试目标自动可用，无需 tests 开关（gupnp-av 无此 option）。
        toolchain.c_link_args.extend(self._glib_libintl_link_args())
        toolchain.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()
        # 【E120/E132 同款：CI worker lld 动态链接 libxml2.so.16】
        # meson configure 阶段的编译器/链接器探测（clang -Wl,--version 拉起
        # lld）跑在 conanbuild 环境里——buildenv_info 前置 SDK llvm/lib 后
        # 探测可正常加载 lld。真机 SSH 环境自带该路径，CI worker
        # （AppSpawn 沙箱）缺失（先例：archives/p/pycairo/1.29.0）。
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
            self.output.info(
                "gupnp-av: prepend SDK llvm/lib to LD_LIBRARY_PATH: %s" % sdk_llvm_lib)

    def _sdk_llvm_libdir(self):
        """返回 OHOS SDK 的 llvm/lib 目录（lld 的 libxml2.so.16 所在），
        找不到则返回 None。路径带 SDK 版本号，用 glob 探测（pycairo 同款）。"""
        import glob as _glob
        dirs = sorted(_glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"))
        for d in reversed(dirs):
            if os.path.isdir(d):
                return d
        return None

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            if not cross_building(self) and can_run(self):
                meson.test()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # meson install 不产 .la；防御性清理（仓内惯例）。
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["gupnp-av-1.0"]
        self.cpp_info.includedirs = ["include/gupnp-av-1.0", "include"]
        # glib2/2.88.0 与 libxml2/2.15.3.1 均为平铺包（无 components），
        # 引用整体包名而非组件名。
        self.cpp_info.requires = ["glib2::glib2", "libxml2::libxml2"]
        self.cpp_info.set_property("cmake_file_name", "gupnp-av-1.0")
        self.cpp_info.set_property("cmake_target_name", "gupnp-av-1.0::gupnp-av-1.0")
        self.cpp_info.set_property("pkg_config_name", "gupnp-av-1.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # DIDL-Lite 校验用的 XSD 装在 <pkg>/share/gupnp-av/；库内 DATADIR
        # 宏是编译期 prefix（/share/gupnp-av），消费者运行时必须用
        # GUPNP_AV_DATADIR 指到包内实际路径（上游 tests/gtest/meson.build
        # 同款机制），否则 libxml2 找不到 schema 直接 abort。
        xsd_dir = os.path.join(self.package_folder, "share", "gupnp-av")
        if os.path.isdir(xsd_dir):
            self.runenv_info.define_path("GUPNP_AV_DATADIR", xsd_dir)

    # ------------------------------------------------------------------
    # helpers (pattern follows archives/a/atk/2.38.0.1.1 — same glib2
    # + meson + OHOS toolchain family)
    # ------------------------------------------------------------------

    def _build_environment(self):
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        # 【OHOS 必需】meson 的 ninja 探测用 python subprocess 跑裸名
        # `ninja`（OHOS python subprocess 裸名命令 PATH 解析不可靠 →
        # FileNotFoundError），且默认 LD_LIBRARY_PATH 下 ninja 可能加载
        # libc++_shared.so 失败（rc=127 被 meson 静默跳过 → "Could not
        # detect Ninja"）。meson tooldetect.detect_ninja 优先读 NINJA
        # 环境变量传绝对路径，同时把 /system/lib64 前置进
        # LD_LIBRARY_PATH 保证 ninja/工具链子进程可加载 libc++_shared。
        # （archives/g/glib/2.84.0 同款 NINJA 注入。）
        ninja = os.environ.get("NINJA") or shutil.which("ninja")
        if ninja and os.path.isfile(ninja):
            environment.define_path("NINJA", ninja)
        ldlp = os.environ.get("LD_LIBRARY_PATH", "")
        if ldlp:
            environment.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        else:
            environment.define_path("LD_LIBRARY_PATH", "/system/lib64")
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def _append_dependency_pkg_config_paths(self):
        # conan MesonToolchain 生成的 native file 的 pkg_config_path 只有
        # generators 目录；glib2/libxml2 包内 pkgconfig 目录需显式追加，
        # 否则 meson dependency() 探测不到。
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
        replacement = "pkg_config_path = [" + ", ".join("'{}'".format(p) for p in unique_paths) + "]"
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _make_clang_wrapper(self, cc):
        """生成 clang wrapper 脚本：export LD_LIBRARY_PATH=<SDK llvm/lib> 后
        exec 真编译器。lld 动态依赖 libxml2.so.16（在 SDK llvm/lib），CI
        worker 的探测/链接子进程环境里没有该路径。wrapper 从进程层面兜底，
        不依赖 conanbuild env 是否被 meson 探测继承。"""
        if not cc or not os.path.isfile(cc):
            return None
        sdk_lib = self._sdk_llvm_libdir()
        if not sdk_lib:
            return None  # 无 SDK 目录（非 OHOS 环境）则不需要 wrapper
        bindir = os.path.join(self.generators_folder, "clang-wrappers")
        os.makedirs(bindir, exist_ok=True)
        wrappers = {}
        for suffix in ("", "++"):
            wrapper = os.path.join(bindir, f"clang{suffix}")
            with open(wrapper, "w", encoding="utf-8") as f:
                f.write(
                    "#!/data/service/hnp/bin/bash\n"
                    f'export LD_LIBRARY_PATH="{sdk_lib}:$LD_LIBRARY_PATH"\n'
                    f'exec "{cc}{suffix}" "$@"\n'
                )
            os.chmod(wrapper, 0o755)
            wrappers[suffix] = wrapper
        return wrappers[""]

    def _inject_meson_tools(self):
        # 【OHOS 必需】MesonToolchain 不写 ar/ranlib 进 native file；clang
        # 工具链在 /data/service/hnp/bin，PATH 上无裸名 llvm-ar 时 meson
        # configure 直接失败。注入全路径 + pkg-config。
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            # 【CI worker 兼容（E120 变体，hard 版）】meson 的编译器/链接器
            # 探测（clang -Wl,--version 拉起 lld）在探测子进程里执行，
            # conanbuild.sh 与 build() 内 Environment 都覆盖不到（CI 三台
            # worker CI-031/037/011 实证）。根治：把 native file 里的
            # c/cpp 编译器替换为 wrapper 脚本——wrapper 自己 export
            # LD_LIBRARY_PATH=<SDK llvm/lib> 后 exec 真 clang，探测/编译/
            # 链接全部经过 wrapper，环境必然生效（真机 SSH 环境也兼容：
            # 前置只是多一条搜索路径）。
            cc_wrapper = self._make_clang_wrapper(cc) if cc else None
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (bindir, "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"):
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
            if cc_wrapper:
                # 替换 c/cpp 编译器为 wrapper（meson 探测与构建统一走它）
                content = re.sub(r"^c\s*=.*$", f"c = '{cc_wrapper}'", content, flags=re.M)
                content = re.sub(r"^cpp\s*=.*$", f"cpp = '{cc_wrapper}++'", content, flags=re.M)
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _augment_glib_pkg_config(self):
        # glib2 包的 glib-2.0.pc 里 glib_genmarshal=${bindir}/glib-genmarshal
        # 指向 OHOS ELF（构建机不可执行）；meson gnome.genmarshal 探测到该
        # 路径时会尝试运行。包内 glib-genmarshal 实为 python3 脚本，直接
        # 用绝对路径替换变量即可在构建机运行（atk 2.38.0.1.1 同款处理）。
        glib_genmarshal = self._resolve_host_tool("glib-genmarshal")
        variables = {
            "glib-2.0": [
                f"glib_genmarshal={glib_genmarshal}",
            ],
        }
        for pc_name, entries in variables.items():
            pc_file = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.isfile(pc_file):
                self.output.warning(f"Could not augment missing {pc_name}.pc")
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            inserted = []
            for entry in entries:
                key = entry.split("=", 1)[0] + "="
                if key not in content:
                    inserted.append(entry)
            if not inserted:
                continue
            name_index = content.find("\nName:")
            addition = "\n" + "\n".join(inserted)
            if name_index >= 0:
                content = content[:name_index] + addition + content[name_index:]
            else:
                content = "\n".join(inserted) + "\n" + content
            with open(pc_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _resolve_host_tool(self, tool_name):
        # 优先直接可用路径（包内 python 脚本），否则回落 ${bindir}/NAME。
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin", tool_name)
            if os.path.isfile(candidate):
                return candidate.replace("\\", "/")
        return f"${{bindir}}/{tool_name}"

    def _glib_libintl_link_args(self):
        # OHOS 无 libc gettext/intl；glib2 的 .pc 带 -lintl，静态链接需把
        # 包内 libintl.a 显式传给链接器（atk 2.38.0.1.1 同款）。
        if self.settings.os != "OHOS":
            return []
        for dependency in self.dependencies.host.values():
            for library_name in ("libintl.a", "libintl.so"):
                library_path = os.path.join(dependency.package_folder, "lib", library_name)
                if os.path.isfile(library_path):
                    return [library_path.replace("\\", "/")]
        return []
