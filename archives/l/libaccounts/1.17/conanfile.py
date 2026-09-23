from conan import ConanFile
from conan.tools.gnu import AutotoolsToolchain, Autotools, PkgConfigDeps
from conan.tools.files import copy, get, rmdir, replace_in_file, apply_conandata_patches, save
from conan.tools.layout import basic_layout
import os
import re

required_conan_version = ">=2.0"

class LibaccountsConan(ConanFile):
    name = "libaccounts"
    version = "1.17"
    description = "GLib-based client library for the accounts database"
    license = "LGPL-2.1-or-later"
    url = "https://gitlab.com/accounts-sso/libaccounts-glib"
    homepage = "https://gitlab.com/accounts-sso/libaccounts-glib"
    topics = ("accounts", "sso", "glib", "accounts-sso")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def requirements(self):
        self.requires("glib2/2.88.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("sqlite3/3.53.4", transitive_headers=True, transitive_libs=True)
        self.test_requires("check/0.15.2")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def export_sources(self):
        export = self.conf.get("user.build_patch:export_sources", default=True)
        if export:
            copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-introspection")
        tc.configure_args.append("--disable-gtk-doc")
        tc.configure_args.append("--disable-man")
        tc.configure_args.append("--disable-python")
        tc.configure_args.append("--enable-tests")
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-linux")
        # Suppress deprecated-declarations errors from glib 2.88
        # (libaccounts-glib 1.17 uses glib 2.26-era APIs that are deprecated in 2.88)
        tc.extra_cflags.append("-Wno-error=deprecated-declarations")
        tc.extra_cflags.append("-Wno-error=deprecated")
        pkg = PkgConfigDeps(self)
        pkg.generate()
        # Create .pc shims for gio-2.0, gio-unix-2.0, gobject-2.0
        glib2_prefix = self.dependencies["glib2"].package_folder
        self._create_pc_shim("gio-2.0", glib2_prefix)
        self._create_pc_shim("gio-unix-2.0", glib2_prefix, include_gio_unix=True)
        self._create_pc_shim("gobject-2.0", glib2_prefix)
        tc.generate()

    def _create_pc_shim(self, name, prefix, include_gio_unix=False):
        gen_folder = self.generators_folder
        extra_inc = ""
        if include_gio_unix:
            extra_inc = f' -I{prefix}/include/gio-unix-2.0'
        # gio-unix-2.0 symbols live inside libgio-2.0 (conan glib2 ships no
        # separate libgio-unix-2.0), so always link against -lgio-2.0.
        link_lib = "gio-2.0" if name == "gio-unix-2.0" else name
        content = (
            f'prefix={prefix}\n'
            f'libdir=${{prefix}}/lib\n'
            f'includedir=${{prefix}}/include/glib-2.0\n'
            f'includedir1=${{prefix}}/lib/glib-2.0/include\n\n'
            f'Name: {name}\n'
            f'Description: Conan shim for {name} (from glib2)\n'
            f'Version: 2.88.0.1\n'
            f'Libs: -L${{libdir}} -l{link_lib} -lglib-2.0\n'
            f'Cflags: -I${{includedir}} -I${{includedir1}}{extra_inc}\n'
            f'Requires: glib-2.0\n'
        )
        save(self, os.path.join(gen_folder, f"{name}.pc"), content)

    def _patch_sources(self):
        src = self.source_folder

        # Remove docs and pygobject from SUBDIRS
        replace_in_file(self, os.path.join(src, "Makefile.am"),
                        "SUBDIRS = libaccounts-glib docs tools",
                        "SUBDIRS = libaccounts-glib tools")
        replace_in_file(self, os.path.join(src, "Makefile.am"),
                        "SUBDIRS += pygobject",
                        "#SUBDIRS += pygobject")

        # Fix configure.ac: remove docs and pygobject from AC_CONFIG_FILES
        with open(os.path.join(src, "configure.ac"), "r") as f:
            lines = f.readlines()
        new_lines = [l for l in lines if not any(d in l for d in ["docs/Makefile", "docs/reference/Makefile", "docs/reference/version.xml", "pygobject/Makefile"])]
        with open(os.path.join(src, "configure.ac"), "w") as f:
            f.writelines(new_lines)

        # Disable gobject-introspection
        replace_in_file(self, os.path.join(src, "configure.ac"),
                        "GOBJECT_INTROSPECTION_CHECK([1.30.0])",
                        "AM_CONDITIONAL([HAVE_INTROSPECTION], [false])")

        # Disable gtk-doc
        replace_in_file(self, os.path.join(src, "configure.ac"),
                        "GTK_DOC_CHECK([1.14], [--flavour no-tmpl])",
                        "AM_CONDITIONAL([ENABLE_GTK_DOC], [false])")

        # Fix multiline LIBACCOUNTS_REQUIRED variable
        old_var = 'LIBACCOUNTS_REQUIRED="glib-2.0 >= 2.26\n     gio-2.0 >= 2.30\n     gio-unix-2.0\n     gobject-2.0 >= 2.35.1\n     libxml-2.0\n     sqlite3 >= 3.7.0"'
        new_var = 'LIBACCOUNTS_REQUIRED="glib-2.0 >= 2.26 gio-2.0 >= 2.30 gio-unix-2.0 gobject-2.0 >= 2.35.1 libxml-2.0 sqlite3 >= 3.7.0"'
        try:
            replace_in_file(self, os.path.join(src, "configure.ac"), old_var, new_var)
        except Exception:
            pass

        # Add AM_PROG_AR after AC_PROG_CC
        replace_in_file(self, os.path.join(src, "configure.ac"),
                        "AC_PROG_CC\nAC_PROG_CC_STDC",
                        "AC_PROG_CC\nAM_PROG_AR\nAC_PROG_CC_STDC")

        # Disable python support
        python_start = '# Python support'
        python_end = 'AM_CONDITIONAL([ENABLE_PYTHON], [test "x$have_python" = "xyes"])'
        with open(os.path.join(src, "configure.ac"), "r") as f:
            content = f.read()
        start_idx = content.find(python_start)
        end_idx = content.find(python_end)
        if start_idx >= 0 and end_idx >= 0:
            end_idx += len(python_end)
            content = content[:start_idx] + "# Python support disabled for OHOS\nAM_CONDITIONAL([ENABLE_PYTHON], [false])" + content[end_idx:]
            with open(os.path.join(src, "configure.ac"), "w") as f:
                f.write(content)

        # Remove -Werror
        try:
            replace_in_file(self, os.path.join(src, "configure.ac"), "-Wall -Werror", "-Wall")
        except Exception:
            pass
        # Also remove -Werror from Makefile.am files (all subdirs)
        for subdir in ["libaccounts-glib", "tests", "tools"]:
            makefile_am = os.path.join(src, subdir, "Makefile.am")
            if os.path.exists(makefile_am):
                with open(makefile_am, "r") as f:
                    am_content = f.read()
                am_content = am_content.replace("-Wall -Werror", "-Wall -Wno-error=deprecated-declarations -Wno-error=deprecated")
                with open(makefile_am, "w") as f:
                    f.write(am_content)

        # Also patch Makefile.am.in or Makefile.in if they exist (before autoreconf)
        for subdir in ["libaccounts-glib", "tests", "tools"]:
            for tmpl in ["Makefile.in", "Makefile.am.in"]:
                tmpl_path = os.path.join(src, subdir, tmpl)
                if os.path.exists(tmpl_path):
                    with open(tmpl_path, "r") as f:
                        tmpl_content = f.read()
                    if "-Wall -Werror" in tmpl_content:
                        tmpl_content = tmpl_content.replace("-Wall -Werror", "-Wall -Wno-error=deprecated-declarations -Wno-error=deprecated")
                        with open(tmpl_path, "w") as f:
                            f.write(tmpl_content)

        # After autoreconf, also patch generated Makefile.in files
        # This is done in build() after autoreconf

        # Create empty gtk-doc.make
        save(self, os.path.join(src, "gtk-doc.make"), "")

    def build(self):
        apply_conandata_patches(self)
        self._patch_sources()
        self.run("autoreconf -fi", cwd=self.source_folder)
        self.run("chmod +x configure config.guess config.sub install-sh missing depcomp 2>/dev/null; true", cwd=self.source_folder)

        # Patch generated Makefile.in files to remove -Werror (after autoreconf)
        for subdir in ["libaccounts-glib", "tests", "tools"]:
            makefile_in = os.path.join(self.source_folder, subdir, "Makefile.in")
            if os.path.exists(makefile_in):
                with open(makefile_in, "r") as f:
                    mi_content = f.read()
                if "-Wall -Werror" in mi_content:
                    mi_content = mi_content.replace("-Wall -Werror", "-Wall -Wno-error=deprecated-declarations -Wno-error=deprecated")
                    with open(makefile_in, "w") as f:
                        f.write(mi_content)

        # Fix E011: HMDFS umask 077 permission issue in config.status
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r") as f:
            configure_content = f.read()
        configure_content = configure_content.replace("umask 077", "umask 022")
        with open(configure_path, "w") as f:
            f.write(configure_content)

        # Run configure in the build folder (out-of-tree build)
        build_dir = self.build_folder
        os.makedirs(build_dir, exist_ok=True)
        src = self.source_folder

        self.run(
            f"cd {build_dir} && {src}/configure"
            f" --prefix= --disable-introspection --disable-gtk-doc --disable-man"
            f" --disable-python --enable-tests"
            f" --build=aarch64-unknown-linux-gnu --host=aarch64-linux"
            f" CFLAGS='-Wno-error=deprecated-declarations -Wno-error=deprecated'"
            f" CXXFLAGS='-Wno-error=deprecated-declarations'"
            f" lt_cv_deplibs_check_method=pass_all"
            f" --no-create",
            env="conanbuild"
        )

        # Patch config.status to skip .la dependency resolution
        config_status = os.path.join(build_dir, "config.status")
        if os.path.exists(config_status):
            with open(config_status, "r") as f:
                cs = f.read()
            cs = cs.replace("umask 077", "umask 022")
            with open(config_status, "w") as f:
                f.write(cs)

        self.run(f"cd {build_dir} && ./config.status", env="conanbuild")

        # Patch the generated libtool: set link_all_deplibs=yes so that
        # dependency .la files are not re-resolved at link time (their
        # libdir entries can point to broken '//lib' prefixes on CI
        # workers). This is an official libtool knob -- keep the script
        # syntax intact (no function-definition rewriting).
        for subdir in ["", "libaccounts-glib"]:
            libtool_path = os.path.join(build_dir, subdir, "libtool") if subdir else os.path.join(build_dir, "libtool")
            if os.path.exists(libtool_path):
                with open(libtool_path, "r") as f:
                    lt = f.read()
                lt = lt.replace("link_all_deplibs=unknown", "link_all_deplibs=yes")
                lt = lt.replace("link_all_deplibs=no", "link_all_deplibs=yes")
                with open(libtool_path, "w") as f:
                    f.write(lt)

        # Fix dependency .la files. On CI workers, shared dependency builds
        # (glib2/pcre2/...) ship .la files whose libdir is a broken '//lib'
        # prefix and whose dependency_libs embed absolute .la references
        # (e.g. '//lib/libpcre2-8.la') that libtool tries to re-resolve and
        # fails ("is not a valid libtool archive"). Rewrite each dependency
        # .la: (1) libdir -> the real package lib folder; (2) every .la
        # reference inside dependency_libs -> the equivalent -l<name> linker
        # flag (resolved via -L, never re-read recursively by libtool).
        def _la_ref_to_link_flag(match):
            ref = match.group(0)
            base = os.path.basename(ref)
            stem = base[:-3] if base.endswith(".la") else base
            if stem.startswith("lib") and len(stem) > 3:
                return f"-l{stem[3:]}"
            return f"-l{stem}"

        def _fix_dependency_libs_line(match):
            line = match.group(0)
            return re.sub(r"[^\s']*\.la", _la_ref_to_link_flag, line)

        for require, dep in self.dependencies.items():
            la_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(la_dir):
                continue
            for la in os.listdir(la_dir):
                if not la.endswith(".la"):
                    continue
                la_path = os.path.join(la_dir, la)
                with open(la_path, "r") as f:
                    la_content = f.read()
                new_content = re.sub(
                    r"^libdir='[^']*'$",
                    f"libdir='{la_dir}'",
                    la_content,
                    flags=re.M,
                )
                new_content = re.sub(
                    r"^dependency_libs='.*'$",
                    _fix_dependency_libs_line,
                    new_content,
                    flags=re.M,
                )
                if new_content != la_content:
                    with open(la_path, "w") as f:
                        f.write(new_content)

        # Run make with explicit CFLAGS to suppress deprecation errors.
        # Prepend glib2's bin to PATH so gdbus-codegen comes from the conan
        # glib2 package (shebang '#!/usr/bin/env python3' works on OHOS)
        # instead of the system copy at /data/service/hnp/bin whose shebang
        # points to the missing /usr/bin/python3.
        glib2_bin = os.path.join(self.dependencies["glib2"].package_folder, "bin")
        self.run(f'PATH="{glib2_bin}:$PATH" make -j1 CFLAGS=\'-Wall -Wno-error=deprecated-declarations -Wno-error=deprecated\'', cwd=build_dir, env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["accounts-glib"]
        self.cpp_info.requires = ["glib2::glib2", "libxml2::libxml2", "sqlite3::sqlite3"]
        self.cpp_info.includedirs = ["include", "include/libaccounts-glib"]
        self.cpp_info.set_property("pkg_config_name", "libaccounts-glib")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
