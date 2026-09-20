#!/usr/bin/env python3
"""Conan recipe — libcloudproviders 0.4.0 (Meson, GNOME Cloud Providers DBus API).

libcloudproviders — GNOME 云盘供应商 DBus 接口库。提供
CloudProvidersCollector（客户端，枚举供应商/账户）与
CloudProvidersProviderExporter / CloudProvidersAccountExporter（服务端，
向 session bus 导出供应商与账户对象）。上游消费者如 nautilus/nautilus-sendto
通过该库集成 Nextcloud/Google Drive 等云盘账户。

适配要点（HarmonyOS PC / aarch64）：
- meson 构建，依赖 glib-2.0 / gio-2.0 / gio-unix-2.0（>=2.64）
- glib 配方无独立 gio-unix-2.0 组件，从 glib 包内复制 gio-unix-2.0.pc
  并重写 prefix（accountsservice dbus-1.pc 同款模式）
- 关闭可选特性 introspection（GIR）与 vapigen（Vala 绑定）：
  vapigen 引用 introspection 产物（libcloudproviders_gir[0]），两者必须同关；
  核心 C 库 libcloudproviders.so + 头文件 + pkg-config 完整保留
- gnome.mkenums_simple / gdbus_codegen 依赖的 glib 工具通过 python wrapper
  注入 .pc 变量（glib_mkenums/glib_genmarshal/gobject_query/gdbus_codegen）
- OHOS ELF 需签名（llvm-objcopy 去 .codesign + binary-sign-tool 自签名）
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibcloudprovidersConan(ConanFile):
    name = "libcloudproviders"
    version = "0.4.0"
    description = "Cloud providers DBus API library (GNOME)"
    license = "LGPL-3.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libcloudproviders"
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
        # glib exposes glib-2.0/gobject-2.0/gio-2.0 components; gio-unix-2.0
        # .pc lives inside the glib package (no separate conan component), a
        # local alias is created in generate().
        self.requires("glib/2.88.3.1", transitive_headers=True, transitive_libs=True)
        # glib 的 pkg-config 展开内联 -lintl（proxy-libintl 组件被
        # PkgConfigDeps 内联但不可见），链接时需要其 libdir（generate()
        # 注入 -L）。proxy-libintl 为 glib 链接依赖，声明为直接依赖并在
        # package_info() 的 cpp_info.requires 引用以满足 lint。
        self.requires("proxy-libintl/0.5", options={"shared": False})

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source_data = self.conan_data["sources"]
        get(self, url=source_data["url"], sha256=source_data["sha256"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        self._create_gio_unix_pc_alias()
        toolchain = MesonToolchain(self)
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        # 可选特性裁剪：introspection（GIR）与 vapigen（Vala）同关（见文件头说明）。
        # documentation 默认 false 无需显式设置。
        toolchain.project_options["introspection"] = False
        toolchain.project_options["vapigen"] = False
        toolchain.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    def build(self):
        # patches applied once in source(); do NOT re-apply here.
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # 上游测试（testcloudprovidersserver/client）为 DBus session bus
            # 演示/集成程序，未注册 meson test()，且依赖 session bus 运行；
            # OHOS 无 dbus-daemon，无法作为 CI 自动化测试运行。
            # 功能覆盖由 test_package 的自研断言承担。

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # libcloudproviders.so (link name "cloudproviders") + headers under
        # include/cloudproviders/ (meson install_headers subdir 'cloudproviders').
        self.cpp_info.libs = ["cloudproviders"]
        self.cpp_info.includedirs = ["include/cloudproviders"]
        self.cpp_info.requires = [
            "glib::glib",
            "glib::gio",
            # proxy-libintl 是 glib 的链接依赖（.pc 内联 -lintl），声明以
            # 满足 conan package_info lint（直接依赖须被 cpp_info.requires 引用）。
            # proxy-libintl 无 components，使用 pkg::pkg 形式引用默认组件。
            "proxy-libintl::proxy-libintl",
        ]
        self.cpp_info.set_property("pkg_config_name", "cloudproviders")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ── helpers (patterns proven in accountsservice/libei recipes) ─────────

    def _build_environment(self):
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
        return environment

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

    def _inject_meson_tools(self):
        import shutil

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
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
        # gnome.mkenums_simple needs glib_mkenums / glib_genmarshal /
        # gobject_query pkg-config variables which PkgConfigDeps does not emit;
        # gnome.gdbus_codegen reads gdbus_codegen from gio-2.0.pc (accountsservice
        # pattern). Wrap the conan-installed python scripts so __file__ resolves
        # under the package bin/ (locates codegen data under share/glib-2.0).
        import sys

        glib_mkenums = self._create_python_tool_wrapper("glib-mkenums")
        glib_genmarshal = self._create_python_tool_wrapper("glib-genmarshal")
        gdbus_codegen = self._create_python_tool_wrapper("gdbus-codegen")
        variables = {
            "glib-2.0": [
                f"glib_mkenums={glib_mkenums}",
                f"glib_genmarshal={glib_genmarshal}",
                "gobject_query=${bindir}/gobject-query",
            ],
            "gobject-2.0": [
                f"glib_mkenums={glib_mkenums}",
            ],
            "gio-2.0": [
                f"gdbus_codegen={gdbus_codegen}",
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
            if inserted:
                addition = "\n" + "\n".join(inserted)
                name_index = content.find("\nName:")
                if name_index >= 0:
                    content = content[:name_index] + addition + content[name_index:]
                else:
                    content = "\n".join(inserted) + "\n" + content
            libs_line = next((line for line in content.splitlines() if line.startswith("Libs:")), None)
            if libs_line is not None and "-lintl" not in libs_line.split():
                content = content.replace(libs_line, libs_line + " -lintl", 1)
            # PkgConfigDeps 内联 proxy-libintl 为裸 -lintl 但不附加其 -L；
            # 补上 proxy-libintl 包的 libdir，否则链接报 unable to find -lintl。
            if libs_line is not None and "-lintl" in libs_line:
                intl_libdir = self._proxy_libintl_libdir()
                if intl_libdir and f'-L"{intl_libdir}"' not in libs_line and intl_libdir not in libs_line:
                    content = content.replace(libs_line, libs_line + f' -L"{intl_libdir}"', 1)
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _proxy_libintl_libdir(self):
        for dependency in self.dependencies.host.values():
            if getattr(dependency.ref, "name", "") == "proxy-libintl":
                libdirs = list(dependency.cpp_info.libdirs) or ["lib"]
                for libdir in libdirs:
                    if not os.path.isabs(libdir):
                        libdir = os.path.join(dependency.package_folder, libdir)
                    if os.path.isdir(libdir):
                        return libdir.replace("\\", "/")
        return ""

    def _create_gio_unix_pc_alias(self):
        # upstream meson asks for dependency('gio-unix-2.0') but the glib conan
        # recipe declares no gio-unix-2.0 component, so PkgConfigDeps emits no
        # gio-unix-2.0.pc. Copy the real .pc from the glib package and rewrite
        # its bare "prefix=/" to the actual package folder.
        target = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        if os.path.isfile(target):
            return
        glib_folder = None
        for dependency in self.dependencies.host.values():
            if getattr(dependency.ref, "name", "") == "glib":
                glib_folder = dependency.package_folder
                break
        if not glib_folder:
            self.output.warning("glib dependency not found; skipping gio-unix-2.0.pc alias")
            return
        source = None
        for relative in ("lib/pkgconfig/gio-unix-2.0.pc", "share/pkgconfig/gio-unix-2.0.pc"):
            candidate = os.path.join(glib_folder, relative)
            if os.path.isfile(candidate):
                source = candidate
                break
        if not source:
            self.output.warning("gio-unix-2.0.pc not found in glib package; skipping alias")
            return
        with open(source, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        prefix = glib_folder.replace("\\", "/")
        content = "\n".join(
            "prefix=" + prefix if line.startswith("prefix=") else line
            for line in content.splitlines()
        )
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _create_python_tool_wrapper(self, tool_name):
        tool_path = None
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin", tool_name)
            if os.path.isfile(candidate):
                tool_path = candidate
                break
        if not tool_path:
            return f"${{bindir}}/{tool_name}"
        import sys

        wrapper_path = os.path.join(self.generators_folder, f"{tool_name}-python")
        with open(wrapper_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                f"#!{sys.executable}\n"
                "import runpy\n"
                "import sys\n"
                f"sys.argv = [{tool_path!r}] + sys.argv[1:]\n"
                f"runpy.run_path({tool_path!r}, run_name='__main__')\n"
            )
        os.chmod(wrapper_path, 0o755)
        return wrapper_path.replace("\\", "/")

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        import glob

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
        for subdir in ("bin", "libexec"):
            binary_dir = os.path.join(self.package_folder, subdir)
            if os.path.isdir(binary_dir):
                for name in os.listdir(binary_dir):
                    path = os.path.join(binary_dir, name)
                    if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path):
                        targets.append(path)
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
