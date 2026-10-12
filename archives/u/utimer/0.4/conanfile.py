import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, get, replace_in_file, unzip


class UtimerConan(ConanFile):
    name = "utimer"
    version = "0.4"
    license = "GPL-3.0-or-later"
    description = "Command-line timer, countdown and stopwatch"
    homepage = "https://launchpad.net/utimer"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt", "globals.c"

    def export_sources(self):
        for name in ("CMakeLists.txt", "globals.c"):
            copy(self, name, self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("glib/2.88.3")
        # Direct gettext calls are not an implementation detail of GLib.
        self.requires("proxy-libintl/0.5")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Supported targets: Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        archive = self.conf.get("user.utimer:source_archive", default=None)
        if archive:
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        if os.path.realpath(self.export_sources_folder) != os.path.realpath(self.source_folder):
            for name in ("CMakeLists.txt", "globals.c"):
                copy(self, name, self.export_sources_folder, self.source_folder)
        header = os.path.join(self.source_folder, "src", "utimer.h")
        replace_in_file(self, header, "#include <glib.h>",
                        "#include <glib.h>\n#include <glib-object.h>\n#include <locale.h>\n#include <libintl.h>")
        for old, new in (
            ("GMainLoop         *loop;", "extern GMainLoop *loop;"),
            ("gboolean          paused;", "extern gboolean paused;"),
            ("struct termios    savedttystate;", "extern struct termios savedttystate;"),
            ("Config            ut_config;", "extern Config ut_config;"),
        ):
            replace_in_file(self, header, old, new)
        source = os.path.join(self.source_folder, "src", "utimer.c")
        replace_in_file(self, source, "static gboolean        *stopwatch = FALSE,",
                        "static gboolean         stopwatch = FALSE,")
        replace_in_file(self, source, "*show_limits = FALSE", "show_limits = FALSE")
        replace_in_file(self, source, "*show_version = FALSE", "show_version = FALSE")
        replace_in_file(self, os.path.join(self.source_folder, "src", "log.h"),
                        "#endif /* LOG_H */", "void setup_log_handler(void);\n\n#endif /* LOG_H */")
        # A timer without an attached print source must not remove a random
        # GLib source ID. The unchanged upstream duration test exposes this.
        replace_in_file(self, os.path.join(self.source_folder, "src", "timer.c"),
                        "t->gtimer      = timer;", "t->gtimer      = timer;\n  t->timer_print_source_id = 0;")
        # A background fgetc holds stdin's FILE lock while waiting for input;
        # descriptor-level read does not obstruct process exit/stdio cleanup.
        # EOF stops only the watcher, not the finite timer's success callback.
        replace_in_file(self, os.path.join(self.source_folder, "src", "utils.c"),
                        "c = fgetc (stdin);",
                        "unsigned char key;\n    ssize_t n;\n    do { n = read(STDIN_FILENO, &key, 1); } while (n < 0 && errno == EINTR);\n    if (n <= 0)\n      return 0;\n    c = key;")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self.run('"./utimer-upstream-tests" --verbose -m slow',
                     cwd=self.build_folder, env="conanrun")

    def package(self):
        CMake(self).install()
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
