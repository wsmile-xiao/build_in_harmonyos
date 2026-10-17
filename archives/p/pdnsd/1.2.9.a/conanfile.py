import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PdnsdConan(ConanFile):
    name = "pdnsd"
    version = "1.2.9.a"
    description = "Proxy DNS server with persistent caching"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/kwarunek/pdnsd"
    url = ""
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pdnsd is supported for Linux/OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        if str(self.settings.os) == "OHOS":
            return
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--with-target=Linux",
                "--with-thread-lib=NPTL",
                "--with-default-id=root",
                "--with-cachedir=/var/cache/pdnsd",
                "--sysconfdir=/etc",
            ]
        )
        tc.generate()

    def _build_type_flags(self):
        return {
            "Debug": ["-O0", "-g"],
            "Release": ["-O2", "-DNDEBUG"],
            "RelWithDebInfo": ["-O2", "-g", "-DNDEBUG"],
            "MinSizeRel": ["-Os", "-DNDEBUG"],
        }.get(str(self.settings.build_type), ["-O2", "-DNDEBUG"])

    def _ohos_target(self):
        return {
            "armv8": "aarch64-linux-ohos",
            "x86_64": "x86_64-linux-ohos",
        }.get(str(self.settings.arch), "aarch64-linux-ohos")

    def _ohos_config_h(self):
        return r'''#ifndef _CONFIG_H_
#define _CONFIG_H_
#define TARGET TARGET_LINUX
#define ENABLE_IPV4 1
#define DEFAULT_IPV4 1
#define M_PRESET UDP_ONLY
#define SRC_ADDR_DISC 1
#define R_DEFAULT 1
#define CACHE_DBM DBM_NATIVE
#define CACHEDIR "/var/cache/pdnsd"
#define TEMPDIR "/tmp"
#define DEBUG 1
#define VERBOSITY 0
#define HASH_SZ 10
#define CPP_C99_VARIADIC_MACROS 1
#define TCP_TIMEOUT 30
#define PAR_QUERIES 2
#define TARGET_LINUX 0
#define TARGET_BSD 1
#define TARGET_CYGWIN 2
#define THREADLIB_NPTL 1
#define _REENTRANT 1
#define _THREAD_SAFE 1
#define charp (char *)
#define ucharp (unsigned char *)
#define VERSION "1.2.9a-par"
#define CONFDIR "/etc"
#define HAVE_ALLOCA 1
#define HAVE_ALLOCA_H 1
#define HAVE_ASPRINTF 1
#define HAVE_FCNTL_H 1
#define HAVE_GETLINE 1
#define HAVE_GETPWNAM_R 1
#define HAVE_GETTIMEOFDAY 1
#define HAVE_INET_NTOP 1
#define HAVE_INET_PTON 1
#define HAVE_INTTYPES_H 1
#define HAVE_LIBPTHREAD 1
#define HAVE_MALLOC_H 1
#define HAVE_MEMORY_H 1
#define HAVE_MEMPCPY 1
#define HAVE_MKFIFO 1
#define HAVE_NANOSLEEP 1
#define HAVE_NETINET_IN_H 1
#define HAVE_NET_IF_H 1
#define HAVE_POLL 1
#define HAVE_SELECT 1
#define HAVE_SNPRINTF 1
#define HAVE_SOCKET 1
#define HAVE_SOCKLEN_T 1
#define HAVE_STDINT_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STPCPY 1
#define HAVE_STPNCPY 1
#define HAVE_STRDUP 1
#define HAVE_STRERROR 1
#define HAVE_STRINGS_H 1
#define HAVE_STRING_H 1
#define HAVE_STRLCPY 1
#define HAVE_STRNDUP 1
#define HAVE_STRUCT_IFREQ 1
#define HAVE_STRUCT_IN6_ADDR 1
#define HAVE_STRUCT_IN_PKTINFO 1
#define HAVE_SYSLOG_H 1
#define HAVE_SYS_IOCTL_H 1
#define HAVE_SYS_POLL_H 1
#define HAVE_SYS_SOCKET_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TIME_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_SYS_WAIT_H 1
#define HAVE_UNAME 1
#define HAVE_UNISTD_H 1
#define HAVE_VASPRINTF 1
#define HAVE_VPRINTF 1
#define HAVE_VSNPRINTF 1
#define PACKAGE_BUGREPORT ""
#define PACKAGE_NAME ""
#define PACKAGE_STRING ""
#define PACKAGE_TARNAME ""
#define PACKAGE_VERSION ""
#define RETSIGTYPE void
#define STDC_HEADERS 1
#define TIME_WITH_SYS_TIME 1
#endif
'''

    def _compiler_executable(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("c") if compilers else None

    def _ohos_common_flags(self, config_dir):
        cc = self._compiler_executable() or "clang"
        flags = [
            f"--target={self._ohos_target()}",
            "-D__MUSL__",
            "-include",
            "net/if.h",
            f"-I{config_dir}",
            f"-I{self.source_folder}",
            f"-I{os.path.join(self.source_folder, 'src')}",
            "-D_REENTRANT",
            "-D_THREAD_SAFE",
        ]
        native_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(cc))))
        sysroot = os.path.join(native_dir, "sysroot")
        if os.path.isdir(sysroot):
            flags.insert(1, f"--sysroot={sysroot}")
        flags.extend(self._build_type_flags())
        return cc, flags

    def _ohos_link_flags(self, cc):
        flags = [f"--target={self._ohos_target()}"]
        native_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(cc))))
        sysroot = os.path.join(native_dir, "sysroot")
        if os.path.isdir(sysroot):
            flags.append(f"--sysroot={sysroot}")
        flags.extend(self._build_type_flags())
        return flags

    def _run_cmd(self, cmd):
        self.output.info(" ".join(cmd))
        subprocess.run(cmd, check=True)

    def _build_ohos_direct(self):
        os.makedirs(self.build_folder, exist_ok=True)
        config_dir = os.path.join(self.build_folder, "generated")
        obj_dir = os.path.join(self.build_folder, "obj")
        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(obj_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)
        with open(os.path.join(config_dir, "config.h"), "w", newline="\n") as config:
            config.write(self._ohos_config_h())

        cc, common = self._ohos_common_flags(config_dir)
        src_dir = os.path.join(self.source_folder, "src")
        main_sources = [
            "conf-parser.c", "conff.c", "consts.c", "debug.c", "dns.c",
            "dns_answer.c", "dns_query.c", "error.c", "helpers.c", "icmp.c",
            "list.c", "main.c", "netdev.c", "rr_types.c", "status.c",
            "servers.c", "thread.c", "cache.c", "hash.c",
        ]
        objects = []
        for source in main_sources:
            obj = os.path.join(obj_dir, f"{source}.o")
            self._run_cmd([cc, *common, "-c", os.path.join(src_dir, source), "-o", obj])
            objects.append(obj)
        link_flags = self._ohos_link_flags(cc)
        self._run_cmd([cc, *link_flags, *objects, "-lpthread", "-o", os.path.join(bin_dir, "pdnsd")])

        ctl_obj = os.path.join(obj_dir, "pdnsd-ctl.o")
        rr_client_obj = os.path.join(obj_dir, "rr_types-client.o")
        self._run_cmd(
            [
                cc, *common, f"-I{os.path.join(src_dir, 'pdnsd-ctl')}",
                "-c", os.path.join(src_dir, "pdnsd-ctl", "pdnsd-ctl.c"), "-o", ctl_obj,
            ]
        )
        self._run_cmd([cc, *common, "-DCLIENT_ONLY", "-c", os.path.join(src_dir, "rr_types.c"), "-o", rr_client_obj])
        self._run_cmd([cc, *link_flags, ctl_obj, rr_client_obj, "-lpthread", "-o", os.path.join(bin_dir, "pdnsd-ctl")])
        self.output.info("OHOS direct clang build completed")

    def _patch_sources(self):
        icmp_c = os.path.join(self.source_folder, "src", "icmp.c")
        replace_in_file(
            self,
            icmp_c,
            "# include <netinet/ip.h>\n# include <linux/types.h>\n# include <linux/icmp.h>",
            "# include <net/if.h>\n# include <netinet/ip.h>\n# include <linux/types.h>\n# include <linux/icmp.h>",
        )

    def build(self):
        self._patch_sources()
        if str(self.settings.os) == "OHOS":
            self._build_ohos_direct()
            return

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

        # Upstream ships four diagnostic programs under src/test. make check
        # builds them; when the build context can execute target binaries, run
        # all four with deterministic local inputs and fail on any non-zero exit.
        autotools.make(args=["check"])
        if can_run(self):
            test_dir = os.path.join(self.build_folder, "src", "test")
            tests = [
                ("if_up", "lo"),
                ("is_local_addr", "127.0.0.1"),
                ("tping", "127.0.0.1"),
                ("random",),
            ]
            for test in tests:
                cmd = " ".join(os.path.join(test_dir, test[0]) if i == 0 else arg for i, arg in enumerate(test))
                self.run(cmd)
            self.output.info("Upstream diagnostic tests passed: 4/4")
        else:
            self.output.info("Upstream diagnostic tests built; execution skipped for cross build context")

    def package(self):
        if str(self.settings.os) == "OHOS":
            copy(self, "pdnsd", os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
            copy(self, "pdnsd-ctl", os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
            copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
            copy(self, "COPYING.BSD", self.source_folder, os.path.join(self.package_folder, "licenses"))
            copy(self, "README.rst", self.source_folder, os.path.join(self.package_folder, "share", "doc", "pdnsd"))
            copy(self, "README.par", self.source_folder, os.path.join(self.package_folder, "share", "doc", "pdnsd"))
            copy(self, "pdnsd-ctl.8", os.path.join(self.source_folder, "doc"), os.path.join(self.package_folder, "share", "man", "man8"))
            return

        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.BSD", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.rst", self.source_folder, os.path.join(self.package_folder, "share", "doc", "pdnsd"))
        copy(self, "README.par", self.source_folder, os.path.join(self.package_folder, "share", "doc", "pdnsd"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
