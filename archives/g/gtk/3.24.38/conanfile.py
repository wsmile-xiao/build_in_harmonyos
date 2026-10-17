import glob
import json
import os
import re
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class Gtk3Conan(ConanFile):
    name = "gtk"
    version = "3.24.38"
    description = "GTK+ 3 widget toolkit"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gtk.org"
    url = "https://gitlab.gnome.org/GNOME/gtk"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    _ohos_compiled_glib_tools = (
        "gio-querymodules",
        "glib-compile-resources",
        "glib-compile-schemas",
        "gobject-query",
    )
    _expected_upstream_tests = 237
    _ohos_runnable_upstream_tests = (
        "gtk+:bitmask",
        "gtk+:rbtree",
        "gtk+:typename",
        "gtk+:c++ keywords",
        "gtk+:rgba",
        "gtk+:test-simplify",
        "gtk+:test-settings",
    )

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
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("cairo-gobject/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires("pango/1.56.4", transitive_headers=True, transitive_libs=True)
        self.requires("harfbuzz/14.2.0", force=True, transitive_headers=True, transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6", transitive_headers=True, transitive_libs=True)
        self.requires("atk/2.38.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("fribidi/1.0.16", transitive_headers=True, transitive_libs=True)
        self.requires("libepoxy/1.5.10", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._create_pkg_config_aliases()
        self._redirect_cairo_pkg_config_to_gobject()
        self._patch_glib_pkg_config_tool_variables()
        self._patch_dependency_pkg_config_cflags()

        toolchain = MesonToolchain(self)
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        toolchain.project_options["x11_backend"] = False
        toolchain.project_options["wayland_backend"] = False
        toolchain.project_options["broadway_backend"] = True
        toolchain.project_options["win32_backend"] = False
        toolchain.project_options["quartz_backend"] = False
        toolchain.project_options["xinerama"] = "no"
        toolchain.project_options["cloudproviders"] = False
        toolchain.project_options["profiler"] = False
        toolchain.project_options["tracker3"] = False
        toolchain.project_options["print_backends"] = "file"
        toolchain.project_options["colord"] = "no"
        toolchain.project_options["gtk_doc"] = False
        toolchain.project_options["man"] = False
        toolchain.project_options["introspection"] = False
        toolchain.project_options["demos"] = False
        toolchain.project_options["examples"] = False
        toolchain.project_options["tests"] = True
        toolchain.project_options["installed_tests"] = False
        toolchain.project_options["builtin_immodules"] = "none"
        toolchain.generate()

        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            self._prepare_ohos_glib_tools()
            meson_program = shutil.which("meson")
            if not meson_program:
                raise ConanException("Meson executable is missing from PATH")
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            if self.settings.os == "OHOS":
                self._build_gettext_shim_object()
                self._patch_ninja_tool_invocations()
            meson.build()
            if self.settings.os == "OHOS":
                self._run_ohos_upstream_tests(meson_program)

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        shutil.rmtree(os.path.join(self.package_folder, "bin"), ignore_errors=True)
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()
            self._ensure_shared_library_aliases()

    def package_info(self):
        self.cpp_info.libs = ["gtk-3", "gdk-3", "gailutil-3"]
        self.cpp_info.includedirs = ["include/gtk-3.0", "include"]
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "cairo::cairo",
            "cairo-gobject::cairo-gobject",
            "pango::pango",
            "harfbuzz::harfbuzz",
            "gdk-pixbuf::gdk-pixbuf",
            "atk::atk",
            "fribidi::fribidi",
            "libepoxy::libepoxy",
            "zlib::zlib",
        ]
        self.cpp_info.set_property("cmake_file_name", "gtk3")
        self.cpp_info.set_property("cmake_target_name", "gtk3::gtk3")
        self.cpp_info.set_property("pkg_config_name", "gtk+-3.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

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
        host_tool_dir = self._ohos_host_tool_dir()
        if os.path.isdir(host_tool_dir):
            environment.prepend_path("PATH", host_tool_dir)
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        if self.settings.os == "OHOS":
            sdk_llvm_libs = sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
            )
            if sdk_llvm_libs:
                # lld is dynamically linked against the matching SDK libxml2.
                environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_libs[-1])
        return environment

    def _create_pkg_config_aliases(self):
        # PkgConfigDeps generates one file per Conan component. Some GNOME packages
        # install additional .pc entry points that GTK's Meson probes directly.
        aliases = {
            "gio-unix-2.0": ("2.84.0.1", "gio-2.0", ["-I${includedir}/gio-unix-2.0"], []),
            "pangocairo": ("1.56.4", "pango cairo", ["-I${includedir}/pango-1.0"], ["-lpangocairo-1.0"]),
        }
        for name, (version, requires, cflags, libs) in aliases.items():
            path = os.path.join(self.generators_folder, name + ".pc")
            if os.path.isfile(path):
                continue
            content = [
                "prefix=${pcfiledir}/../..",
                "includedir=${prefix}/include",
                "libdir=${prefix}/lib",
                f"Name: {name}",
                f"Description: generated forwarding pc for {name}",
                f"Version: {version}",
                f"Requires: {requires}",
            ]
            if libs:
                content.append("Libs: -L${libdir} " + " ".join(libs))
            if cflags:
                content.append("Cflags: " + " ".join(cflags))
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(content) + "\n")

    def _patch_glib_pkg_config_tool_variables(self):
        try:
            self.dependencies["glib"]
        except KeyError:
            return
        variables_by_pc = {
            "glib-2.0.pc": {
                "glib_genmarshal": "glib-genmarshal",
                "glib_mkenums": "glib-mkenums",
            },
            "gobject-2.0.pc": {
                "glib_mkenums": "glib-mkenums",
                "gobject_query": "gobject-query",
            },
            "gio-2.0.pc": {
                "gio_querymodules": "gio-querymodules",
                "gdbus_codegen": "gdbus-codegen",
                "glib_compile_resources": "glib-compile-resources",
                "glib_compile_schemas": "glib-compile-schemas",
            },
        }
        for filename, variables in variables_by_pc.items():
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().splitlines()
            for variable, tool in variables.items():
                assignment = f"{variable}={self._resolve_build_tool(tool)}"
                for index, line in enumerate(lines):
                    if line.startswith(variable + "="):
                        lines[index] = assignment
                        break
                else:
                    lines.append(assignment)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")

    def _patch_dependency_pkg_config_cflags(self):
        cflags_by_pc = {
            "fribidi.pc": ['-I"${includedir}/fribidi"'],
        }
        for filename, additions in cflags_by_pc.items():
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().splitlines()
            for index, line in enumerate(lines):
                if line.startswith("Cflags:"):
                    for addition in additions:
                        if addition not in line:
                            line += " " + addition
                    lines[index] = line
                    break
            else:
                lines.append("Cflags: " + " ".join(additions))
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")

    def _redirect_cairo_pkg_config_to_gobject(self):
        try:
            cairo_gobject = self.dependencies["cairo-gobject"]
        except KeyError:
            return
        path = os.path.join(self.generators_folder, "cairo.pc")
        if not os.path.isfile(path):
            return
        prefix = cairo_gobject.package_folder.replace("\\", "/")
        content = [
            f"prefix={prefix}",
            "libdir=${prefix}/lib",
            "includedir=${prefix}/include/cairo",
            "includedir1=${prefix}/include",
            "bindir=${prefix}/bin",
            "",
            "Name: cairo",
            "Description: cairo from gobject-enabled cairo-gobject package",
            "Version: 1.18.4",
            'Libs: -L"${libdir}" -lcairo -lm -lpthread',
            'Cflags: -I"${includedir}" -I"${includedir1}"',
            "Requires: pixman-1 fontconfig freetype2 libpng zlib",
        ]
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(content) + "\n")

    def _resolve_build_tool(self, tool):
        if self.settings.os == "OHOS" and tool in self._ohos_compiled_glib_tools:
            candidate = os.path.join(self._ohos_host_tool_dir(), tool)
            return candidate.replace("\\", "/")
        dependency_tools = {
            "gdbus-codegen",
            "gio-querymodules",
            "glib-compile-resources",
            "glib-compile-schemas",
            "glib-genmarshal",
            "glib-mkenums",
            "gobject-query",
        }
        if tool in dependency_tools:
            try:
                glib_package = self.dependencies["glib"].package_folder
            except KeyError:
                glib_package = None
            if glib_package:
                candidate = os.path.join(glib_package, "bin", tool)
                if os.path.isfile(candidate):
                    return candidate.replace("\\", "/")
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            if not directory:
                continue
            candidate = os.path.join(directory, tool)
            if os.path.isfile(candidate):
                return candidate.replace("\\", "/")
        return "${bindir}/" + tool

    def _ohos_host_tool_dir(self):
        return os.path.join(self.build_folder, "ohos-host-tools")

    def _prepare_ohos_glib_tools(self):
        try:
            glib_package = self.dependencies["glib"].package_folder
        except KeyError as error:
            raise ConanException("Required glib dependency is missing") from error
        tool_dir = self._ohos_host_tool_dir()
        os.makedirs(tool_dir, exist_ok=True)
        for tool in self._ohos_compiled_glib_tools:
            source = os.path.join(glib_package, "bin", tool)
            if not os.path.isfile(source):
                raise ConanException(f"Required glib host tool is missing: {tool}")
            destination = os.path.join(tool_dir, tool)
            shutil.copy2(source, destination)
            os.chmod(destination, 0o755)
            self._sign_ohos_elf(destination)

    def _patch_ninja_tool_invocations(self):
        # Meson records the configure-time absolute paths, while the build
        # environment may resolve the same tools from dependency packages.
        # Patch command lines by basename instead of re-resolving one path.
        ninja_file = os.path.join(self.build_folder, "build.ninja")
        if not os.path.isfile(ninja_file):
            return
        with open(ninja_file, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        # The pinned GLib package ships these host generators as Python scripts.
        python = shutil.which("python3") or "python3"
        tool_runners = {
            "glib-mkenums": python,
            "glib-genmarshal": python,
            "gdbus-codegen": python,
        }
        for index, line in enumerate(lines):
            if not line.startswith(" COMMAND = "):
                continue
            for tool, runner in tool_runners.items():
                pattern = r"(?<!\S)(/[^\s]*/{})(?=\s|$)".format(re.escape(tool))
                line = re.sub(pattern, lambda match: f"{runner} {match.group(1)}", line)
            lines[index] = line
        content = "\n".join(lines) + "\n"
        content = self._patch_ninja_cairo_gobject_order(content)
        content = self._patch_ninja_gettext_shim_link(content)
        with open(ninja_file, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _patch_ninja_cairo_gobject_order(self, content):
        try:
            cairo = self.dependencies["cairo"]
            cairo_gobject = self.dependencies["cairo-gobject"]
        except KeyError:
            return content
        cairo_prefix = cairo.package_folder.replace("\\", "/")
        cairo_gobject_prefix = cairo_gobject.package_folder.replace("\\", "/")
        cflags = f"-I{cairo_gobject_prefix}/include/cairo -I{cairo_gobject_prefix}/include"
        content = content.replace(f"-I{cairo_prefix}/include/cairo", f"{cflags} -I{cairo_prefix}/include/cairo")
        ldflags = f"-L{cairo_gobject_prefix}/lib"
        content = content.replace(f"-L{cairo_prefix}/lib", f"{ldflags} -L{cairo_prefix}/lib")
        return content

    def _gettext_shim_object(self):
        return os.path.join(self.build_folder, "gtk_ohos_gettext_shim.o")

    def _build_gettext_shim_object(self):
        try:
            glib = self.dependencies["glib"]
        except KeyError:
            return
        source = os.path.join(self.build_folder, "gtk_ohos_gettext_shim.c")
        obj = self._gettext_shim_object()
        content = r'''
#include <glib.h>

extern const gchar *glib_gettext(const gchar *str);

char *g_libintl_gettext(const char *msgid) { return (char *)glib_gettext(msgid); }
char *g_libintl_dgettext(const char *domainname, const char *msgid) { return (char *)g_dgettext(domainname, msgid); }
char *g_libintl_dcgettext(const char *domainname, const char *msgid, int category) { return (char *)g_dcgettext(domainname, msgid, category); }
char *g_libintl_dngettext(const char *domainname, const char *msgid, const char *msgid_plural, unsigned long n) { return (char *)g_dngettext(domainname, msgid, msgid_plural, n); }
char *g_libintl_textdomain(const char *domainname) { return (char *)domainname; }
char *g_libintl_bindtextdomain(const char *domainname, const char *dirname) { (void)domainname; return (char *)dirname; }
char *g_libintl_bind_textdomain_codeset(const char *domainname, const char *codeset) { (void)domainname; return (char *)codeset; }
'''.lstrip()
        with open(source, "w", encoding="utf-8") as handle:
            handle.write(content)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or shutil.which("clang") or "clang"
        glib_prefix = glib.package_folder
        includes = [
            os.path.join(glib_prefix, "include"),
            os.path.join(glib_prefix, "include", "glib-2.0"),
            os.path.join(glib_prefix, "lib", "glib-2.0", "include"),
        ]
        command = [cc, "-fPIC"]
        for include in includes:
            command.append("-I" + include)
        command.extend(["-c", source, "-o", obj])
        subprocess.run(command, check=True)

    def _patch_ninja_gettext_shim_link(self, content):
        obj = self._gettext_shim_object().replace("\\", "/")
        if not os.path.isfile(obj) or obj in content:
            return content
        return content.replace("-Wl,--end-group", f"{obj} -Wl,--end-group")

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
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or ""
        bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
        candidates = [bindir]
        ar = compilers.get("ar")
        ranlib = compilers.get("ranlib")
        for directory in candidates:
            if not ar:
                candidate = os.path.join(directory, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
            if not ranlib:
                candidate = os.path.join(directory, "llvm-ranlib")
                if os.path.isfile(candidate):
                    ranlib = candidate
        ar = ar or shutil.which("llvm-ar")
        ranlib = ranlib or shutil.which("llvm-ranlib")
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "[binaries]" not in content:
            return
        insert = []
        if ar and "\nar =" not in content:
            insert.append(f"ar = '{ar}'")
        if ranlib and "\nranlib =" not in content:
            insert.append(f"ranlib = '{ranlib}'")
        if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
            insert.append(f"pkg-config = '{pkg_config}'")
        if insert:
            content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
            with open(native_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        targets = set()
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.update(glob.glob(pattern, recursive=True))
        for target in sorted(targets):
            if not os.path.islink(target):
                self._sign_ohos_elf(target)

    def _sign_ohos_test_targets(self, tests, meson_program):
        introspection = subprocess.run(
            [meson_program, "introspect", self.build_folder, "--targets"],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        project_targets = json.loads(introspection.stdout)
        candidates = set()
        for target in project_targets:
            if target.get("type") not in ("executable", "shared library", "shared module"):
                continue
            filenames = target.get("filename", [])
            if isinstance(filenames, str):
                filenames = [filenames]
            candidates.update(filenames)
        for test in tests:
            candidates.update(test.get("cmd", []))
        candidates.add(os.path.join(self.build_folder, "gdk", "broadway", "broadwayd"))

        build_root = os.path.realpath(self.build_folder)
        targets = set()
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            if not os.path.isabs(candidate):
                candidate = os.path.join(build_root, candidate)
            candidate = os.path.realpath(candidate)
            try:
                if os.path.commonpath((build_root, candidate)) != build_root:
                    continue
            except ValueError:
                continue
            if os.path.isfile(candidate) and self._is_elf(candidate):
                targets.add(candidate)
        if not targets:
            raise ConanException("No Meson project/test ELF files found in GTK build tree")
        for target in sorted(targets):
            self._sign_ohos_elf(target)
        self.output.info(f"Signed {len(targets)} Meson project/test ELF files")

    def _run_ohos_upstream_tests(self, meson_program):
        introspection = subprocess.run(
            [meson_program, "introspect", self.build_folder, "--tests"],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        tests = json.loads(introspection.stdout)
        if len(tests) != self._expected_upstream_tests:
            raise ConanException(
                "Unexpected GTK upstream test count: "
                f"{len(tests)} != {self._expected_upstream_tests}"
            )
        registered = {test.get("name") for test in tests}
        required = {
            selector.split(":", 1)[1]
            for selector in self._ohos_runnable_upstream_tests
        }
        missing = sorted(required - registered)
        if missing:
            raise ConanException(
                "Missing required OHOS upstream tests: " + ", ".join(missing)
            )
        self._sign_ohos_test_targets(tests, meson_program)
        self._ensure_build_tree_shared_library_aliases()

        broadwayd = os.path.join(self.build_folder, "gdk", "broadway", "broadwayd")
        if not os.path.isfile(broadwayd):
            raise ConanException(f"Missing Broadway test server: {broadwayd}")

        runtime_dir = os.path.join(self.build_folder, "tmp", "broadway-runtime")
        os.makedirs(runtime_dir, exist_ok=True)
        environment = os.environ.copy()
        environment.pop("DISPLAY", None)
        environment.update(
            {
                "BROADWAY_DISPLAY": ":5",
                "GDK_BACKEND": "broadway",
                "NO_AT_BRIDGE": "1",
                "XDG_RUNTIME_DIR": runtime_dir,
            }
        )
        server_log = os.path.join(self.build_folder, "broadwayd-test.log")
        with open(server_log, "w", encoding="utf-8") as log:
            server = subprocess.Popen(
                [broadwayd, ":5"],
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                time.sleep(1)
                if server.poll() is not None:
                    raise ConanException(
                        f"Broadway test server exited with {server.returncode}; "
                        f"see {server_log}"
                    )
                subprocess.run(
                    [
                        meson_program,
                        "test",
                        "-C",
                        self.build_folder,
                        "--no-rebuild",
                        "--print-errorlogs",
                        "--num-processes",
                        "1",
                    ] + list(self._ohos_runnable_upstream_tests),
                    check=True,
                    env=environment,
                    timeout=300,
                )
                self.output.info(
                    f"Validated {len(tests)} upstream registrations and passed "
                    f"{len(self._ohos_runnable_upstream_tests)} OHOS-safe tests"
                )
            finally:
                if server.poll() is None:
                    server.terminate()
                    try:
                        server.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait(timeout=10)

    def _sign_ohos_elf(self, target):
        objcopy = shutil.which("llvm-objcopy")
        readelf = shutil.which("llvm-readelf")
        signer = shutil.which("binary-sign-tool")
        if not all((objcopy, readelf, signer)):
            raise ConanException("Required OHOS signing tools are missing from PATH")
        os.chmod(target, 0o755)
        if self._has_codesign_section(target, readelf):
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", target],
                check=True,
                timeout=30,
            )
        output = target + ".gtk-signed"
        subprocess.run(
            [signer, "sign", "-inFile", target, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {target}")
        os.chmod(output, (os.stat(target).st_mode & 0o777) | 0o055)
        os.replace(output, target)

    def _ensure_shared_library_aliases(self):
        self._ensure_shared_library_aliases_in(os.path.join(self.package_folder, "lib"))

    def _ensure_build_tree_shared_library_aliases(self):
        self._ensure_shared_library_aliases_in(self.build_folder, recursive=True)

    def _ensure_shared_library_aliases_in(self, root, recursive=False):
        if not os.path.isdir(root):
            return
        pattern = os.path.join(root, "**", "lib*.so.*") if recursive else os.path.join(root, "lib*.so.*")
        for versioned in glob.glob(pattern, recursive=recursive):
            if not os.path.isfile(versioned) or not self._is_elf(versioned):
                continue
            basename = os.path.basename(versioned)
            stem, version = basename.split(".so.", 1)
            aliases = [stem + ".so"]
            major = version.split(".", 1)[0]
            if major:
                aliases.append(stem + ".so." + major)
            for alias_name in aliases:
                alias = os.path.join(os.path.dirname(versioned), alias_name)
                if os.path.exists(alias):
                    continue
                shutil.copy2(versioned, alias)

    def _has_codesign_section(self, path, readelf):
        completed = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return any(".codesign" in line.split() for line in completed.stdout.splitlines())
