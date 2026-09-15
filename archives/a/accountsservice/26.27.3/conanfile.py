#!/usr/bin/env python3
"""Conan recipe — accountsservice 26.27.3 (libaccountsservice + accounts-daemon, Meson).

AccountsService provides the org.freedesktop.Accounts D-Bus user-account
service: the libaccountsservice client library (act_* API — consumed by
ayatana-indicator-a11y) plus the accounts-daemon binary.

Adapted to HarmonyOS PC (aarch64). See notes.md for the platform adaptations
(version pin, dbus-1.pc alias, polkit .pc variables, logind stub).
"""
import glob
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class AccountsserviceConan(ConanFile):
    name = "accountsservice"
    version = "26.27.3"
    description = "AccountsService — D-Bus user account service (libaccountsservice + accounts-daemon)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.freedesktop.org/wiki/Software/AccountsService/"
    url = "https://gitlab.freedesktop.org/accountsservice/accountsservice"
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
        # glib exposes glib-2.0/gobject-2.0/gio-2.0/gio-unix-2.0 (.pc in the
        # package's lib/pkgconfig; gio-unix-2.0 is shipped inside the package).
        # libaccountsservice links only glib/gio/gio-unix (+ the logind stub),
        # so glib is the only dependency propagated to consumers.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # json-c is linked only by the accounts-daemon executable (not by the
        # library); keep it a private dependency (avoids the Conan "direct
        # dependency not used by cpp_info.requires" check).
        self.requires("json-c/0.18", visible=False)
        # dbus is configure-time only (install dirs via dbus-1.pc variables);
        # no library/executable links libdbus-1.
        self.requires("dbus/1.14.10", visible=False)
        # polkit-gobject-1 is hard-REQUIRED at meson configure (meson.build:161)
        # and linked only by the daemon; polkit/127 (the published OHOS build)
        # provides the libpolkit-gobject-1 client library.
        self.requires("polkit/127", visible=False)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        # tar_format in conandata.yml is only for validation; get() does not
        # accept it, so pass url/sha256 explicitly (dbus/polkit pattern).
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"], sha256=source_data.get("sha256", ""), strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        self._create_dbus_pc_alias()
        self._augment_polkit_pc()
        self._prepare_systemd_stub()
        toolchain = MesonToolchain(self)
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        # systemd units are optional; OHOS has no systemd
        toolchain.project_options["systemdsystemunitdir"] = "no"
        # OHOS libc has no _PATH_WTMPX / WTMPX_FILENAME; pin the wtmp path
        toolchain.project_options["wtmpfile"] = "/var/log/wtmp"
        toolchain.project_options["introspection"] = False
        toolchain.project_options["vapi"] = False
        toolchain.project_options["tests"] = False
        toolchain.project_options["docbook"] = False
        toolchain.project_options["gtk_doc"] = False
        toolchain.project_options["create_homed"] = False
        toolchain.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    def build(self):
        # patches are applied once in source(); do NOT re-apply here (a second
        # apply_conandata_patches would fail on a clean conan create).
        self._compile_systemd_stub()
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # upstream tests disabled (-Dtests=false) — functional coverage in test_package

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # libaccountsservice.so (act_* API); headers under include/accountsservice-1.0
        self.cpp_info.libs = ["accountsservice"]
        self.cpp_info.includedirs = ["include/accountsservice-1.0"]
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
        ]
        self.cpp_info.set_property("cmake_file_name", "accountsservice")
        self.cpp_info.set_property("cmake_target_name", "accountsservice::accountsservice")
        self.cpp_info.set_property("pkg_config_name", "accountsservice")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ── helpers (patterns proven in the polkit/atk 124 recipes) ─────────────

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
        # local logind stub prefix (libsystemd.pc)
        stub_pc = os.path.join(self.build_folder, "prefix", "lib", "pkgconfig")
        if os.path.isdir(stub_pc):
            paths.append(stub_pc)
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
        # gnome.mkenums needs glib_mkenums / glib_genmarshal / gobject_query
        # pkg-config variables which PkgConfigDeps does not emit (polkit pattern).
        glib_mkenums = self._create_python_tool_wrapper("glib-mkenums")
        glib_genmarshal = self._create_python_tool_wrapper("glib-genmarshal")
        # gnome.gdbus_codegen reads the gdbus_codegen variable from gio-2.0.pc
        # (meson find_tool falls back to it when gdbus-codegen is not on PATH);
        # wrap it so the conan-installed script's __file__ points at bin/ and it
        # can locate its codegen package under share/glib-2.0.
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
            # gi18n.h maps gettext() to g_libintl_* (glib proxy-libintl); the
            # generated .pc does not list -lintl so the shared lib would keep
            # undefined g_libintl_* symbols (ayatana-common pattern).
            libs_line = next((line for line in content.splitlines() if line.startswith("Libs:")), None)
            if libs_line is not None and "-lintl" not in libs_line.split():
                content = content.replace(libs_line, libs_line + " -lintl", 1)
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _create_dbus_pc_alias(self):
        # dbus/1.14.10 recipe has no pkg_config_name, so PkgConfigDeps emits
        # "dbus.pc", but upstream meson asks for dependency('dbus-1') and reads
        # datadir/interfaces_dir/system_bus_services_dir variables. Alias it and
        # add the upstream dbus-1.pc variables meson needs.
        generated = os.path.join(self.generators_folder, "dbus.pc")
        alias = os.path.join(self.generators_folder, "dbus-1.pc")
        if not os.path.isfile(generated):
            self.output.warning("dbus.pc not generated by PkgConfigDeps; skipping dbus-1.pc alias")
            return
        with open(generated, encoding="utf-8") as handle:
            content = handle.read()
        content = self._add_pc_variables(content, (
            "datadir=${prefix}/share",
            "sysconfdir=${prefix}/etc",
            "localstatedir=${prefix}/var",
            "libexecdir=${prefix}/libexec",
            "interfaces_dir=${datadir}/dbus-1/interfaces",
            "system_bus_services_dir=${datadir}/dbus-1/system-services",
        ))
        with open(alias, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _augment_polkit_pc(self):
        # upstream reads policydir (and datadir) from polkit-gobject-1.pc;
        # PkgConfigDeps-generated .pc lacks them.
        pc = os.path.join(self.generators_folder, "polkit-gobject-1.pc")
        if os.path.isfile(pc):
            with open(pc, encoding="utf-8") as handle:
                content = handle.read()
        else:
            # polkit/127 (the published OHOS build) declares no cpp_info
            # component, so PkgConfigDeps only emits "polkit.pc" and no
            # polkit-gobject-1.pc. Fall back to the real .pc installed inside
            # the polkit package and rewrite its bare "prefix=/" (installed
            # with --prefix=/ + DESTDIR) to the actual package folder — the
            # equivalent of what PkgConfigDeps would generate for a declared
            # component. Meson's pkg_config_path starts with generators_folder,
            # so this copy wins over the raw package .pc.
            source = self._polkit_gobject_pc()
            if not source:
                self.output.warning("polkit-gobject-1.pc not generated and not found in polkit package; skipping augmentation")
                return
            with open(source, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            polkit_prefix = self._polkit_package_folder().replace("\\", "/")
            content = "\n".join(
                "prefix=" + polkit_prefix if line.startswith("prefix=") else line
                for line in content.splitlines()
            )
        content = self._add_pc_variables(content, (
            "datadir=${prefix}/share",
            "policydir=${datadir}/polkit-1/actions",
        ))
        with open(pc, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _polkit_package_folder(self):
        for dependency in self.dependencies.host.values():
            if getattr(dependency.ref, "name", "") == "polkit":
                return dependency.package_folder
        return ""

    def _polkit_gobject_pc(self):
        folder = self._polkit_package_folder()
        if not folder:
            return None
        for relative in ("lib/pkgconfig/polkit-gobject-1.pc", "share/pkgconfig/polkit-gobject-1.pc"):
            candidate = os.path.join(folder, relative)
            if os.path.isfile(candidate):
                return candidate
        return None

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

    # ── logind (libsystemd) stub ────────────────────────────────────────────
    # OHOS has no systemd/logind. Upstream meson.build:242 unconditionally
    # requires dependency('libsystemd') (>= 186) and act-user-manager.c links
    # sd-login symbols for session tracking. We generate a minimal static stub
    # so libaccountsservice links and degrades gracefully ("no sessions" /
    # -ENOTSUP). Session tracking is a documented runtime limitation.

    def _prepare_systemd_stub(self):
        prefix = os.path.join(self.build_folder, "prefix")
        include_dir = os.path.join(prefix, "include", "systemd")
        lib_dir = os.path.join(prefix, "lib")
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")
        for directory in (include_dir, lib_dir, pc_dir):
            os.makedirs(directory, exist_ok=True)
        pc_file = os.path.join(pc_dir, "libsystemd.pc")
        with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                f"prefix={prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: systemd\n"
                "Description: OHOS stub libsystemd (logind session tracking stub, not functional)\n"
                "Version: 250\n"
                "Libs: -L${libdir} -lsystemd\n"
                "Cflags: -I${includedir}\n"
            )
        header = os.path.join(include_dir, "sd-login.h")
        with open(header, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#ifndef OHOS_SD_LOGIN_H\n"
                "#define OHOS_SD_LOGIN_H\n"
                "\n"
                "#include <sys/types.h>\n"
                "#include <stdint.h>\n"
                "\n"
                "#ifdef __cplusplus\n"
                "extern \"C\" {\n"
                "#endif\n"
                "\n"
                "typedef struct sd_login_monitor sd_login_monitor;\n"
                "\n"
                "int sd_login_monitor_new(const char *category, sd_login_monitor **ret);\n"
                "int sd_login_monitor_flush(sd_login_monitor *m);\n"
                "int sd_login_monitor_get_fd(sd_login_monitor *m);\n"
                "sd_login_monitor *sd_login_monitor_unref(sd_login_monitor *m);\n"
                "\n"
                "int sd_uid_get_sessions(uid_t uid, int leading, char ***sessions);\n"
                "int sd_get_sessions(char ***sessions);\n"
                "int sd_seat_can_multi_session(const char *seat);\n"
                "int sd_session_get_class(const char *session, char **ret);\n"
                "int sd_session_get_display(const char *session, char **ret);\n"
                "int sd_session_get_seat(const char *session, char **ret);\n"
                "int sd_session_get_state(const char *session, char **ret);\n"
                "int sd_session_get_type(const char *session, char **ret);\n"
                "int sd_session_get_uid(const char *session, uid_t *uid);\n"
                "\n"
                "#ifdef __cplusplus\n"
                "}\n"
                "#endif\n"
                "#endif\n"
            )
        stub_c = os.path.join(lib_dir, "sd-login-stub.c")
        with open(stub_c, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <errno.h>\n"
                "#include <stdlib.h>\n"
                "\n"
                "#include <systemd/sd-login.h>\n"
                "\n"
                "/* OHOS/PC stub for systemd/logind session tracking.\n"
                " * OHOS has no systemd/logind. act-user-manager.c uses sd-login to\n"
                " * track the user's graphical session; these stubs make\n"
                " * libaccountsservice link and degrade gracefully: \"no sessions\"\n"
                " * (0) / not-supported (-ENOTSUP). Runtime limitation, see notes.md. */\n"
                "\n"
                "int sd_uid_get_sessions(uid_t uid, int leading, char ***sessions) {\n"
                "    if (sessions) *sessions = NULL;\n"
                "    return 0;\n"
                "}\n"
                "\n"
                "int sd_get_sessions(char ***sessions) {\n"
                "    if (sessions) *sessions = NULL;\n"
                "    return 0;\n"
                "}\n"
                "\n"
                "int sd_login_monitor_new(const char *category, sd_login_monitor **ret) {\n"
                "    if (ret) *ret = NULL;\n"
                "    return -ENOTSUP;\n"
                "}\n"
                "\n"
                "int sd_login_monitor_flush(sd_login_monitor *m) { return -ENOTSUP; }\n"
                "int sd_login_monitor_get_fd(sd_login_monitor *m) { return -1; }\n"
                "sd_login_monitor *sd_login_monitor_unref(sd_login_monitor *m) { return NULL; }\n"
                "\n"
                "int sd_seat_can_multi_session(const char *seat) { return 0; }\n"
                "\n"
                "int sd_session_get_class(const char *session, char **ret) { if (ret) *ret = NULL; return -ENOTSUP; }\n"
                "int sd_session_get_display(const char *session, char **ret) { if (ret) *ret = NULL; return -ENOTSUP; }\n"
                "int sd_session_get_seat(const char *session, char **ret) { if (ret) *ret = NULL; return -ENOTSUP; }\n"
                "int sd_session_get_state(const char *session, char **ret) { if (ret) *ret = NULL; return -ENOTSUP; }\n"
                "int sd_session_get_type(const char *session, char **ret) { if (ret) *ret = NULL; return -ENOTSUP; }\n"
                "int sd_session_get_uid(const char *session, uid_t *uid) { return -ENOTSUP; }\n"
            )

    def _compile_systemd_stub(self):
        prefix = os.path.join(self.build_folder, "prefix")
        stub_c = os.path.join(prefix, "lib", "sd-login-stub.c")
        if not os.path.isfile(stub_c):
            return
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compilers.get("c") or shutil.which("clang") or "clang"
        obj = os.path.join(prefix, "lib", "sd-login-stub.o")
        archive = os.path.join(prefix, "lib", "libsystemd.a")
        include = os.path.join(prefix, "include")
        self.run(f'"{compiler}" -c "{stub_c}" -o "{obj}" -I"{include}"')
        archiver = None
        for candidate in (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-ar",
            "/data/service/hnp/bin/llvm-ar",
            "/data/service/hnp/bin/ar",
        ):
            if os.path.isfile(candidate):
                archiver = candidate
                break
        if not archiver:
            archiver = shutil.which("llvm-ar") or shutil.which("ar")
        if not archiver:
            raise ConanException("No archiver found to build the logind stub (llvm-ar/ar)")
        self.run(f'"{archiver}" rcs "{archive}" "{obj}"')

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
