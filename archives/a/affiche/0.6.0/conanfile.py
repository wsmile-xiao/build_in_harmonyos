#!/usr/bin/env python3
"""Conan recipe for Affiche 0.6.0.

Affiche is a GNUstep desktop sticky-notes application. The GNUstep GUI stack
is now available in the archive, so this recipe records the real packaging
shape instead of a blocked placeholder.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class AfficheConan(ConanFile):
    name = "affiche"
    version = "0.6.0"
    description = 'GNUstep application for "stick" notes on the desktop'
    license = "GPL-2.0-or-later"
    homepage = "http://wiki.gnustep.org/index.php/Affiche.app"
    url = "https://salsa.debian.org/gnustep-team/affiche.app"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        self.requires("gnustep-gui/0.31.1")

    def build_requirements(self):
        self.tool_requires("gnustep-make/2.9.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_path(self, dep, *parts):
        if not dep or not dep.package_folder:
            return None
        return os.path.join(dep.package_folder, *parts)

    def _append_dep_search_paths(self, env):
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            for subdir in ("bin", "Tools"):
                path = self._dep_path(dep, subdir)
                if path and os.path.isdir(path):
                    env.prepend_path("PATH", path)
            for libdir in dep.cpp_info.libdirs or ["lib"]:
                path = libdir if os.path.isabs(libdir) else self._dep_path(dep, libdir)
                if path and os.path.isdir(path):
                    env.append("LDFLAGS", f"-L{path}")
                    env.append("ADDITIONAL_LIB_DIRS", f"-L{path}")
            for includedir in dep.cpp_info.includedirs or ["include"]:
                path = (
                    includedir
                    if os.path.isabs(includedir)
                    else self._dep_path(dep, includedir)
                )
                if path and os.path.isdir(path):
                    env.append("CPPFLAGS", f"-I{path}")
                    env.append("ADDITIONAL_INCLUDE_DIRS", f"-I{path}")

    def _append_library_flags(self, env, variable, dependency_name, fallback_libs):
        dep = self.dependencies.get(dependency_name)
        if not dep:
            return
        libs = dep.cpp_info.libs or fallback_libs
        for lib in libs:
            if lib.startswith(("-l", "-Wl,")) or os.path.isabs(lib):
                env.append(variable, lib)
            else:
                env.append(variable, f"-l{lib}")

    def _append_gnustep_link_flags(self, env):
        self._append_library_flags(
            env, "ADDITIONAL_GUI_LIBS", "gnustep-gui", ["gnustep-gui"]
        )
        self._append_library_flags(
            env, "ADDITIONAL_OBJC_LIBS", "gnustep-base", ["gnustep-base"]
        )
        self._append_library_flags(env, "ADDITIONAL_OBJC_LIBS", "libobjc2", ["objc"])

    def _system_paths(self, root):
        return {
            "GNUSTEP_SYSTEM_APPS": os.path.join(root, "share", "GNUstep"),
            "GNUSTEP_SYSTEM_ADMIN_APPS": os.path.join(root, "share", "GNUstep"),
            "GNUSTEP_SYSTEM_WEB_APPS": os.path.join(
                root, "share", "GNUstep", "WebApplications"
            ),
            "GNUSTEP_SYSTEM_TOOLS": os.path.join(root, "bin"),
            "GNUSTEP_SYSTEM_ADMIN_TOOLS": os.path.join(root, "sbin"),
            "GNUSTEP_SYSTEM_LIBRARY": os.path.join(root, "Library"),
            "GNUSTEP_SYSTEM_HEADERS": os.path.join(root, "include"),
            "GNUSTEP_SYSTEM_LIBRARIES": os.path.join(root, "lib"),
            "GNUSTEP_SYSTEM_DOC": os.path.join(root, "share", "GNUstep", "Documentation"),
            "GNUSTEP_SYSTEM_DOC_MAN": os.path.join(root, "share", "man"),
            "GNUSTEP_SYSTEM_DOC_INFO": os.path.join(root, "share", "info"),
        }

    def _prepare_system_dirs(self):
        for path in self._system_paths(self.package_folder).values():
            os.makedirs(path, exist_ok=True)

    def _tool_wrapper_dir(self):
        bindir = os.path.join(self.build_folder, "gnustep-tool-wrappers")
        os.makedirs(bindir, exist_ok=True)
        return bindir

    def _prepare_tool_wrappers(self):
        bindir = self._tool_wrapper_dir()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        plmerge_c = os.path.join(bindir, "plmerge.c")
        pl2link_c = os.path.join(bindir, "pl2link.c")
        mkinstalldirs_c = os.path.join(bindir, "mkinstalldirs.c")
        save(self, plmerge_c, "int main(void) { return 0; }\n")
        save(
            self,
            pl2link_c,
            r'''
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc < 3) {
        return 1;
    }
    const char *input = argv[1];
    const char *output = argv[2];
    const char *name = strrchr(output, '/');
    name = name ? name + 1 : output;
    char app_name[256];
    snprintf(app_name, sizeof(app_name), "%s", name);
    char *suffix = strstr(app_name, ".desktop");
    if (suffix) {
        *suffix = '\0';
    }
    FILE *file = fopen(output, "w");
    if (!file) {
        return 1;
    }
    fprintf(file, "[Desktop Entry]\n");
    fprintf(file, "Type=Application\n");
    fprintf(file, "Name=%s\n", app_name);
    fprintf(file, "Exec=%s\n", app_name);
    fprintf(file, "X-GNUstep-InfoPlist=%s\n", input);
    fclose(file);
    return 0;
}
''',
        )
        save(
            self,
            mkinstalldirs_c,
            r'''
#include <errno.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>

static int mkdir_p(const char *path) {
    char buffer[4096];
    char *p;
    size_t len = strlen(path);
    if (len == 0 || len >= sizeof(buffer)) {
        return 1;
    }
    strcpy(buffer, path);
    if (buffer[len - 1] == '/') {
        buffer[len - 1] = '\0';
    }
    for (p = buffer + 1; *p; ++p) {
        if (*p == '/') {
            *p = '\0';
            if (mkdir(buffer, 0777) != 0 && errno != EEXIST) {
                return 1;
            }
            *p = '/';
        }
    }
    if (mkdir(buffer, 0777) != 0 && errno != EEXIST) {
        return 1;
    }
    return 0;
}

int main(int argc, char **argv) {
    int rc = 0;
    for (int i = 1; i < argc; ++i) {
        if (mkdir_p(argv[i]) != 0) {
            rc = 1;
        }
    }
    return rc;
}
''',
        )
        compile_env = f'TMPDIR="{tmpdir}" TMP="{tmpdir}" TEMP="{tmpdir}"'
        self.run(
            f'{compile_env} "{cc}" "{plmerge_c}" -o "{os.path.join(bindir, "plmerge")}"'
        )
        self.run(
            f'{compile_env} "{cc}" "{pl2link_c}" -o "{os.path.join(bindir, "pl2link")}"'
        )
        self.run(
            f'{compile_env} "{cc}" "{mkinstalldirs_c}" -o "{os.path.join(bindir, "mkinstalldirs")}"'
        )

    def generate(self):
        env = Environment()
        make_folder = self.dependencies.build["gnustep-make"].package_folder
        if not make_folder:
            raise ConanInvalidConfiguration("gnustep-make package folder is missing")

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)

        env.prepend_path("PATH", os.path.join(make_folder, "bin"))
        env.prepend_path("PATH", self._tool_wrapper_dir())
        env.define_path(
            "GNUSTEP_MAKEFILES",
            os.path.join(make_folder, "share", "GNUstep", "Makefiles"),
        )
        env.define("GNUSTEP_INSTALLATION_DOMAIN", "SYSTEM")
        for variable, path in self._system_paths(self.package_folder).items():
            env.define_path(variable, path)
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("OBJC", cc)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)

        self._append_dep_search_paths(env)
        self._append_gnustep_link_flags(env)

        gui = self.dependencies.get("gnustep-gui")
        if gui and gui.package_folder:
            env.define_path("GNUSTEP_GUI_ROOT", gui.package_folder)

        env.vars(self).save_script("affiche_gnustep_env")

    def _project_folder(self):
        candidates = (
            self.source_folder,
            self.build_folder,
            os.path.dirname(self.build_folder),
        )
        for candidate in candidates:
            if candidate and os.path.exists(os.path.join(candidate, "GNUmakefile")):
                return candidate
        return self.source_folder

    def _make_tool_overrides(self):
        mkinstalldirs = os.path.join(self._tool_wrapper_dir(), "mkinstalldirs")
        return f'MKDIRS="{mkinstalldirs}" MKINSTALLDIRS="{mkinstalldirs}"'

    def build(self):
        # Upstream has no configure step and no check target. GNUstep Make's
        # application.make compiles the Objective-C sources and creates
        # Affiche.app under the package-scoped SYSTEM application directory.
        self._prepare_system_dirs()
        self._prepare_tool_wrappers()
        self.run(
            f"make -j1 {self._make_tool_overrides()}",
            cwd=self._project_folder(),
            env="affiche_gnustep_env",
        )

    def package(self):
        self._prepare_system_dirs()
        self.run(
            f"make install GNUSTEP_INSTALLATION_DOMAIN=SYSTEM LN_S='cp -p' {self._make_tool_overrides()}",
            cwd=self._project_folder(),
            env="affiche_gnustep_env",
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/GNUstep"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define_path(
            "AFFICHE_APPDIR",
            os.path.join(self.package_folder, "share", "GNUstep", "Affiche.app"),
        )
