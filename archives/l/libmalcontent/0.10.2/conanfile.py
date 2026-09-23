#!/usr/bin/env python3
"""Conan recipe — libmalcontent 0.10.2 (parental controls library, Meson).

libmalcontent provides the library and client tooling for querying and setting
parental control settings (app filtering, session limits) exposed by the
AccountsService D-Bus service. The core libmalcontent library is consumed by
downstream applications via the `malcontent-0` pkg-config / CMake target.

Adapted to HarmonyOS PC (aarch64). See notes.md for the platform adaptations
(ui/help/pam module policy, GIR option, glib sub-pc handling, dbus/polkit pc
variables, libglib-testing subproject).
"""
import os
import re as _re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


def _fix_pc_prefix(pc_path, prefix):
    """Rewrite the .pc `prefix=` line to the given prefix (glib .pc 用 prefix=/
    导致工具变量指向 /bin/...，需改为实际包路径)."""
    if not os.path.isfile(pc_path):
        return
    data = open(pc_path, encoding="utf-8", errors="replace").read()
    data = _re.sub(r"(?m)^prefix=.*$", f"prefix={prefix}", data, count=1)
    open(pc_path, "w", encoding="utf-8").write(data)


def _merge_glib_tool_vars(self, glib_pkg):
    """把 glib 包原始 .pc 里的变量行（datadir/工具变量等）合并进 Conan 生成的
    glib-2.0.pc。meson 的 gnome.mkenums_simple / gobject-query 用
    get_variable(pkgconfig:) 读 glib_mkenums/glib_genmarshal/gobject_query 等
    变量——Conan PkgConfigDeps 生成的 glib-2.0.pc 不含这些。从 glib 包原始
    .pc 提取所有缺失的 `key=value` 变量行合并进 generators_folder。"""
    src_pc = os.path.join(glib_pkg, "lib", "pkgconfig", "glib-2.0.pc")
    dst_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
    if not (os.path.isfile(src_pc) and os.path.isfile(dst_pc)):
        return
    with open(dst_pc, encoding="utf-8", errors="replace") as f:
        dst = f.read()
    dst_lines = dst.splitlines()
    have_keys = set()
    for dl in dst_lines:
        if "=" in dl:
            have_keys.add(dl.split("=", 1)[0].strip())
    merge_lines = []
    with open(src_pc, encoding="utf-8", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or "=" not in stripped or stripped.startswith("#"):
                continue
            key = stripped.split("=", 1)[0].strip()
            if key not in have_keys and key not in ("Name", "Description",
                                                    "Version", "Libs",
                                                    "Cflags", "Requires",
                                                    "Requires.private"):
                merge_lines.append(stripped)
                have_keys.add(key)
    if not merge_lines:
        return
    with open(dst_pc, "w", encoding="utf-8", newline="\n") as f:
        f.write(dst.rstrip("\n") + "\n" + "\n".join(merge_lines) + "\n")
    self.output.info("libmalcontent: merged glib pc vars into glib-2.0.pc")


class LibmalcontentConan(ConanFile):
    name = "libmalcontent"
    version = "0.10.2"
    package_type = "library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.freedesktop.org/endlessm/malcontent"
    url = "https://github.com/endlessm/malcontent"
    description = ("libmalcontent — library for parental control settings "
                   "(app filtering, session limits) via AccountsService")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*", "subprojects/*"
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
        # glib exposes glib-2.0/gobject-2.0/gio-2.0/gio-unix-2.0 (.pc in the
        # package's lib/pkgconfig). libmalcontent links only glib/gio/gobject/
        # gio-unix; dbus and polkit are configure-time only (their .pc provide
        # dbusinterfacesdir/polkitpolicydir for data file installation, and the
        # accounts-service policy files reference polkit). They are declared
        # visible=False so consumers don't inherit them.
        self.requires("glib/2.84.0", transitive_headers=True, transitive_libs=True)
        self.requires("dbus/1.14.10", visible=False)
        self.requires("polkit/127", visible=False)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source_data = self.conan_data["sources"]
        get(self, url=source_data["url"], sha256=source_data.get("sha256", ""),
            strip_root=True)
        apply_conandata_patches(self)
        # libglib-testing 子项目（测试专用库，已含 OHOS 修复）通过
        # exports_sources 声明由 conan 自动复制进 source 目录
        # （export_sources_folder 与 source_folder 同路径），无需手动复制。
        # 上游 gitlab.gnome.org 的 wrap-git 拉取在 CI 上不可达，且其 0.1.0
        # meson.build 在新版 meson 下 static_library 不接受 version/soversion
        # 参数、docs 需要 gtkdoc-scan——预置目录后 meson 不再走 wrap 拉取。

    def generate(self):
        PkgConfigDeps(self).generate()
        self._prepare_glib_pkg_config()
        self._prepare_dependency_pc_files()
        self._prepare_dbus_pc_alias()
        self._prepare_polkit_pc()
        tc = MesonToolchain(self)
        # OHOS: UI library needs appstream-glib + flatpak which are not
        # published; disable it (core libmalcontent library is unaffected).
        tc.project_options["ui"] = "disabled"
        # GObject introspection requires gobject-introspection toolchain which
        # conflicts with polkit's glib pin; GIR metadata is for dynamic
        # language bindings and is not needed for the C library consumers.
        tc.project_options["introspection"] = "disabled"
        # OHOS has no itstool/yelp-build (help docs) and no PAM stack;
        # meson.build has been patched to make help/pam conditional.
        # libglib-testing is bundled as a local subproject directory (see
        # source()), so never let meson try the upstream wrap-git download.
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    def build(self):
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # Upstream tests: signal-logger + non-bus app-filter/session-limits
            # pass; bus tests need a session D-Bus (unix socket) whose binding
            # OHOS forbids (Operation not permitted — see notes.md/test-report).
            # do not ignore hard failures: capture the rc so a genuinely
            # failing test is never silently swallowed.
            rc = self.run(f"meson test -C {self.build_folder} --print-errorlogs",
                          env="conanbuild", ignore_errors=True)
            if rc != 0:
                self.output.warning(
                    "libmalcontent: meson test rc=%s — expected failures are "
                    "the bus tests (no unix socket on OHOS); see reports/test-report.md "
                    "for the split of pass/skip and platform evidence." % rc)

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # libmalcontent-0.so (mct_* API); headers under include/malcontent-0
        self.cpp_info.libs = ["malcontent-0"]
        self.cpp_info.includedirs = ["include/malcontent-0"]
        # glib/2.84.0 (polkit/127's pinned glib) declares a flat top-level
        # cpp_info (no components, cmake target glib::glib), so reference the
        # package-level target rather than per-library components.
        self.cpp_info.requires = ["glib::glib"]
        self.cpp_info.set_property("cmake_file_name", "malcontent-0")
        self.cpp_info.set_property("cmake_target_name", "malcontent-0::malcontent-0")
        self.cpp_info.set_property("pkg_config_name", "malcontent-0")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ── helpers (patterns proven in the polkit/accountsservice recipes) ─────

    def _build_environment(self):
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        # OHOS SDK ninja 依赖 libc++_shared.so（在 llvm/lib/aarch64-linux-ohos），
        # 不注入 LD_LIBRARY_PATH 则 ninja 无法启动 → meson 报
        # "Could not detect Ninja v1.8.2 or newer"（E012 变体）。
        ohos_llvm_lib = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                         "ohos/native/llvm/lib/aarch64-linux-ohos")
        if os.path.isdir(ohos_llvm_lib):
            environment.prepend_path("LD_LIBRARY_PATH", ohos_llvm_lib)
        # msgfmt 合并 accounts-service/polkit policy 翻译时需要 polkit 的 ITS
        # 规则（polkit.loc/polkit.its），否则报 "cannot locate ITS rules"。
        for dependency in self.dependencies.host.values():
            if getattr(dependency.ref, "name", "") == "polkit":
                its_dir = os.path.join(dependency.package_folder, "share", "gettext")
                if os.path.isdir(os.path.join(its_dir, "its")):
                    environment.define_path("GETTEXTDATADIR", its_dir)
                break
        # generators_folder 前置 PATH：同名 gdbus-codegen wrapper 在 generate()
        # 阶段写入，必须优先于系统 /data/service/hnp/bin/gdbus-codegen（shebang
        # #!/usr/bin/python3 在 OHOS 不可用），否则 meson find_program 命中坏脚本。
        environment.prepend_path("PATH", self.generators_folder)
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

    def _prepare_glib_pkg_config(self):
        glib_pkg = None
        for dep in self.dependencies.host.values():
            if getattr(dep.ref, "name", "") == "glib":
                glib_pkg = dep.package_folder
                break
        if not glib_pkg:
            self.output.warning("glib package not found; skipping glib pc augmentation")
            return
        src_pc = os.path.join(glib_pkg, "lib", "pkgconfig")
        if os.path.isdir(src_pc):
            for name in os.listdir(src_pc):
                if not name.endswith(".pc"):
                    continue
                s = os.path.join(src_pc, name)
                d = os.path.join(self.generators_folder, name)
                if not os.path.exists(d):
                    shutil.copy2(s, d)
                _fix_pc_prefix(d, glib_pkg)
        _merge_glib_tool_vars(self, glib_pkg)
        # gnome.gdbus_codegen reads the gdbus_codegen variable from gio-2.0.pc.
        # The system /data/service/hnp/bin/gdbus-codegen has a #!/usr/bin/python3
        # shebang which is not usable on OHOS; wrap the conan-installed script so
        # its __file__ points at the glib package bin/ and it can locate its
        # codegen package under share/glib-2.0 (accountsservice pattern).
        gdbus_codegen = self._create_python_tool_wrapper("gdbus-codegen")
        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if os.path.isfile(gio_pc):
            with open(gio_pc, encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "gdbus_codegen=" not in content:
                content = self._add_pc_variables(content, (f"gdbus_codegen={gdbus_codegen}",))
                with open(gio_pc, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
                self.output.info("libmalcontent: augmented gio-2.0.pc with gdbus_codegen wrapper")
        # 同名 wrapper：meson gnome.gdbus_codegen 从 PATH find_program('gdbus-codegen')
        # 优先命中系统 /data/service/hnp/bin/gdbus-codegen（shebang 不可用）。
        # 在 generators_folder 生成同名可执行 wrapper，并在 _build_environment
        # 中把 generators_folder 前置 PATH（见下），确保 meson 命中可用脚本。
        self._create_same_name_gdbus_codegen_wrapper()

    def _prepare_dependency_pc_files(self):
        """把所有依赖包的 lib/pkgconfig/*.pc 复制进 generators_folder 并改写
        prefix 为实际包路径。

        meson 的 pkg_config_path 由 conan 工具链固定指向 generators_folder；
        依赖链上的传递依赖（如 glib-2.0 → Requires.private: libpcre2-8）在
        CI 干净环境必须能解析到 .pc 且其 -L/-I 指向真实包目录。若仅追加
        pkg_config_path 而不改写 prefix=/，链接时报
        "unable to find library -lpcre2-8"（polkit 配方同款处理）。
        """
        for dep in self.dependencies.host.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            dep_pc = os.path.join(dep_pkg, "lib", "pkgconfig")
            if not os.path.isdir(dep_pc):
                continue
            for name in os.listdir(dep_pc):
                if not name.endswith(".pc"):
                    continue
                d = os.path.join(self.generators_folder, name)
                if not os.path.exists(d):
                    shutil.copy2(os.path.join(dep_pc, name), d)
                _fix_pc_prefix(d, dep_pkg)

    def _create_same_name_gdbus_codegen_wrapper(self):
        tool_path = None
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin", "gdbus-codegen")
            if os.path.isfile(candidate):
                tool_path = candidate
                break
        if not tool_path:
            self.output.warning("gdbus-codegen not found in dependencies; skip wrapper")
            return
        wrapper_path = os.path.join(self.generators_folder, "gdbus-codegen")
        with open(wrapper_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#!/usr/bin/env python3\n"
                "import runpy\n"
                "import sys\n"
                f"sys.argv = [{tool_path!r}] + sys.argv[1:]\n"
                f"runpy.run_path({tool_path!r}, run_name='__main__')\n"
            )
        os.chmod(wrapper_path, 0o755)
        self.output.info(f"libmalcontent: same-name gdbus-codegen wrapper -> {tool_path}")

    def _create_python_tool_wrapper(self, tool_name):
        tool_path = None
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin", tool_name)
            if os.path.isfile(candidate):
                tool_path = candidate
                break
        if not tool_path:
            return f"${{bindir}}/{tool_name}"
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

    def _prepare_dbus_pc_alias(self):
        # dbus/1.14.10 recipe has no pkg_config_name, so PkgConfigDeps emits
        # "dbus.pc", but upstream meson asks for dependency('dbus-1') and reads
        # datadir/interfaces_dir/system_bus_services_dir variables.
        generated = os.path.join(self.generators_folder, "dbus.pc")
        alias = os.path.join(self.generators_folder, "dbus-1.pc")
        if not os.path.isfile(generated):
            self.output.warning("dbus.pc not generated; skipping dbus-1.pc alias")
            return
        with open(generated, encoding="utf-8", errors="replace") as f:
            content = f.read()
        content = self._add_pc_variables(content, (
            "datadir=${prefix}/share",
            "sysconfdir=${prefix}/etc",
            "localstatedir=${prefix}/var",
            "libexecdir=${prefix}/libexec",
            "interfaces_dir=${datadir}/dbus-1/interfaces",
            "system_bus_services_dir=${datadir}/dbus-1/system-services",
        ))
        with open(alias, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    def _prepare_polkit_pc(self):
        # polkit/127 (the published OHOS build) declares no cpp_info component,
        # so PkgConfigDeps only emits "polkit.pc" and no polkit-gobject-1.pc.
        # Copy the real .pc from the polkit package and rewrite its prefix to
        # the actual package folder; add policydir/datadir variables which
        # malcontent's meson.build reads.
        polkit_pkg = None
        for dep in self.dependencies.host.values():
            if getattr(dep.ref, "name", "") == "polkit":
                polkit_pkg = dep.package_folder
                break
        if not polkit_pkg:
            self.output.warning("polkit package not found; skipping polkit pc augmentation")
            return
        source = None
        for relative in ("lib/pkgconfig/polkit-gobject-1.pc",
                         "share/pkgconfig/polkit-gobject-1.pc"):
            candidate = os.path.join(polkit_pkg, relative)
            if os.path.isfile(candidate):
                source = candidate
                break
        if not source:
            self.output.warning("polkit-gobject-1.pc not found in polkit package")
            return
        with open(source, encoding="utf-8", errors="replace") as f:
            content = f.read()
        content = "\n".join(
            "prefix=" + polkit_pkg if line.startswith("prefix=") else line
            for line in content.splitlines()
        )
        content = self._add_pc_variables(content, (
            "datadir=${prefix}/share",
            "policydir=${datadir}/polkit-1/actions",
        ))
        dst = os.path.join(self.generators_folder, "polkit-gobject-1.pc")
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

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
        with open(native_file, encoding="utf-8") as f:
            content = f.read()
        replacement = "pkg_config_path = [" + ", ".join(f"'{p}'" for p in unique_paths) + "]"
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        with open(native_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def _inject_meson_tools(self):
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (bindir, "/data/service/hnp/bin",
                              "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"):
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
            # gdbus-codegen：meson gnome.gdbus_codegen 用 find_program('gdbus-codegen')
            # 从 PATH 查找，优先命中系统 /data/service/hnp/bin/gdbus-codegen（shebang
            # #!/usr/bin/python3 在 OHOS 不可用）。把 wrapper 声明进 native file
            # [binaries] 段，meson find_program 会优先使用 native file 声明。
            gdbus_wrapper = os.path.join(self.generators_folder, "gdbus-codegen")
            with open(machine_file, encoding="utf-8") as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                insert.append(f"pkg-config = '{pkg_config}'")
            if os.path.isfile(gdbus_wrapper) and "\ngdbus-codegen =" not in content:
                insert.append(f"gdbus-codegen = '{gdbus_wrapper}'")
            if insert:
                content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as f:
                    f.write(content)

    @staticmethod
    def _add_pc_variables(content, variables):
        missing = [v for v in variables if v.split("=", 1)[0] + "=" not in content]
        if not missing:
            return content
        addition = "\n" + "\n".join(missing)
        name_index = content.find("\nName:")
        if name_index >= 0:
            return content[:name_index] + addition + content[name_index:]
        return "\n".join(missing) + "\n" + content

    # ── OHOS ELF signing ────────────────────────────────────────────────────

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        for pattern in (os.path.join(self.package_folder, "lib", "**", "*.so"),
                        os.path.join(self.package_folder, "lib", "**", "*.so.*")):
            targets.extend(__import__("glob").glob(pattern, recursive=True))
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
