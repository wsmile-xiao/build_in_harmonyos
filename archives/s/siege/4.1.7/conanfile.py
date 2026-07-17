#!/usr/bin/env python3
"""Conan recipe for siege 4.1.7."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain


class SiegeConan(ConanFile):
    name = "siege"
    version = "4.1.7"
    description = "HTTP/HTTPS regression testing and benchmarking utility"
    license = "GPL-3.0-or-later"
    homepage = "https://www.joedog.org/siege-home/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "conan"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # OpenSSL is not required for the package smoke test and is not declared as a Conan dependency here.
        tc.configure_args.append("--without-ssl")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            cookies_c = os.path.join(self.source_folder, "src", "cookies.c")
            cookies = load(self, cookies_c)
            cookies = cookies.replace("#include <string.h>\n", "#include <string.h>\n#include <stdint.h>\n", 1)
            cookies = cookies.replace("  size_t threadID;", "  uintptr_t threadID;")
            cookies = cookies.replace("  size_t  id    = pthread_self();", "  uintptr_t id  = (uintptr_t)pthread_self();")
            cookies = cookies.replace("  pthread_t id  = pthread_self();", "  uintptr_t id  = (uintptr_t)pthread_self();")
            cookies = cookies.replace("  size_t id = pthread_self();", "  uintptr_t id = (uintptr_t)pthread_self();")
            save(self, cookies_c, cookies)

            ftp_c = os.path.join(self.source_folder, "src", "ftp.c")
            ftp = load(self, ftp_c)
            ftp = ftp.replace("#include <setup.h>\n", "#include <setup.h>\n#include <stdint.h>\n", 1)
            ftp = ftp.replace("  size_t  id = pthread_self();", "  size_t  id = (size_t)(uintptr_t)pthread_self();")
            save(self, ftp_c, ftp)

            browser_c = os.path.join(self.source_folder, "src", "browser.c")
            browser = load(self, browser_c)
            browser = browser.replace(
                "#if defined(hpux) || defined(__hpux) || defined(WINDOWS)",
                "#if defined(hpux) || defined(__hpux) || defined(WINDOWS) || defined(__OHOS__)",
                1,
            )
            browser = browser.replace("pthread_once(&this->once, __signal_init);", "pthread_once(&once, __signal_init);")
            browser = browser.replace("sa.sa_handler = signal_handler;", "sa.sa_handler = __signal_handler;")
            browser = browser.replace("pthread_testcancel();", "((void)0);")
            save(self, browser_c, browser)

            crew_c = os.path.join(self.source_folder, "src", "crew.c")
            crew = load(self, crew_c)
            crew = crew.replace(
                "#if defined(hpux) || defined(__hpux)\n    pthread_kill(this->threads[x], SIGUSR1); \n#else\n    pthread_cancel(this->threads[x]); \n#endif",
                "#if defined(hpux) || defined(__hpux) || defined(__OHOS__)\n    pthread_kill(this->threads[x], SIGUSR1); \n#else\n    pthread_cancel(this->threads[x]); \n#endif",
                1,
            )
            save(self, crew_c, crew)

            sock_c = os.path.join(self.source_folder, "src", "sock.c")
            sock = load(self, sock_c)
            sock = sock.replace("pthread_setcanceltype(PTHREAD_CANCEL_DEFERRED, &type);", "type = PTHREAD_CANCEL_DEFERRED;")
            sock = sock.replace("pthread_setcanceltype(type,NULL);", "(void)type;")
            sock = sock.replace("pthread_setcanceltype(type,NULL); ", "(void)type;")
            sock = sock.replace("pthread_testcancel();", "((void)0);")
            save(self, sock_c, sock)

        guess_paths = [
            os.path.join(self.source_folder, "utils", "config.guess"),
            os.path.join(self.source_folder, "config", "config.guess"),
            os.path.join(self.source_folder, "config.guess"),
        ]
        for guess in guess_paths:
            if os.path.exists(guess):
                self.run(
                    r"""sed -i '/case "${UNAME_SYSTEM}" in/a HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl; ;;' """ + f"'{guess}'"
                )
                break

        configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure):
            self.run(f"sed -i 's/umask 077/umask 022/g' '{configure}'")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
