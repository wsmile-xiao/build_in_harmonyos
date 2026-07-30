#!/usr/bin/env python3
"""Conan recipe for ike-scan 1.9.5."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy, get, save
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class IkeScanConan(ConanFile):
    name = "ike-scan"
    version = "1.9.5"
    description = "Command-line tool for discovering and fingerprinting IKE hosts"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/royhills/ike-scan"
    url = "https://github.com/royhills/ike-scan"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _data_dir(self):
        return os.path.join("..", "share", self.name).replace("\\", "/")

    def _write_config_h(self):
        data_dir = self._data_dir().replace('"', r'\"')
        config = f"""
#define STDC_HEADERS 1
#define HAVE_INTTYPES_H 1
#define HAVE_STDINT_H 1
#define HAVE_UNISTD_H 1
#define HAVE_NETDB_H 1
#define HAVE_GETOPT_H 1
#define HAVE_NETINET_IN_H 1
#define HAVE_NETINET_TCP_H 1
#define HAVE_SYS_TIME_H 1
#define HAVE_SYS_SOCKET_H 1
#define HAVE_ARPA_INET_H 1
#define HAVE_SIGNAL_H 1
#define HAVE_REGEX_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_FCNTL_H 1
#define HAVE_MALLOC 1
#define HAVE_GETHOSTBYNAME 1
#define HAVE_GETTIMEOFDAY 1
#define HAVE_INET_NTOA 1
#define HAVE_MEMSET 1
#define HAVE_SELECT 1
#define HAVE_SOCKET 1
#define HAVE_STRERROR 1
#define TIME_WITH_SYS_TIME 1
#define ATTRIBUTE_UNUSED __attribute__((__unused__))
#define IKE_INT64 long int
#define IKE_UINT64 unsigned long int
#define IKE_INT64_FORMAT "%ld"
#define IKE_UINT64_FORMAT "%lu"
#define NET_SIZE_T socklen_t
#define IKEDATADIR "{data_dir}"
#define PACKAGE "ike-scan"
#define PACKAGE_NAME "ike-scan"
#define PACKAGE_VERSION "1.9.5"
#define PACKAGE_STRING "ike-scan 1.9.5"
#define PACKAGE_BUGREPORT "https://github.com/royhills/ike-scan"
#define VERSION "1.9.5"
""".lstrip()
        save(self, os.path.join(self.source_folder, "config.h"), config)

    def _compile(self, output, sources):
        cc = "${CC:-clang}"
        srcs = " ".join(f'"{os.path.join(self.source_folder, source)}"' for source in sources)
        build_type = str(self.settings.build_type)
        optflags = {
            "Debug": "-O0 -g",
            "Release": "-O2",
            "RelWithDebInfo": "-O2 -g",
            "MinSizeRel": "-Os",
        }.get(build_type, "-O2")
        cflags = f'${{CFLAGS:-}} {optflags} -fPIE -Wall -Wshadow -Wwrite-strings -DHAVE_CONFIG_H=1 -I"{self.source_folder}"'
        ldflags = "${LDFLAGS:-} -pie -Wl,-z,relro,-z,now"
        self.run(f'{cc} {cflags} {srcs} -o "{output}" {ldflags}', cwd=self.source_folder, env="conanbuild")

    def build(self):
        self._write_config_h()
        os.makedirs(self.build_folder, exist_ok=True)

        common_sources = [
            "error.c",
            "wrappers.c",
            "utils.c",
            "mt19937ar.c",
            "md5.c",
            "sha1.c",
            "strlcat.c",
            "strlcpy.c",
        ]
        self._compile(os.path.join(self.build_folder, "ike-scan"), ["ike-scan.c", "isakmp.c"] + common_sources)
        self._compile(os.path.join(self.build_folder, "psk-crack"), ["psk-crack.c"] + common_sources)

        if can_run(self):
            self._compile(os.path.join(self.build_folder, "check-sizes"), ["check-sizes.c", "error.c", "strlcat.c"])
            self._compile(
                os.path.join(self.build_folder, "check-hash"),
                ["check-hash.c", "error.c", "utils.c", "wrappers.c", "mt19937ar.c", "md5.c", "sha1.c", "strlcat.c", "strlcpy.c"],
            )
            self.run(f'"{os.path.join(self.build_folder, "check-sizes")}"', env="conanbuild")
            self.run(f'"{os.path.join(self.build_folder, "check-hash")}"', env="conanbuild")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        data_dir = os.path.join(self.package_folder, "share", self.name)
        copy(self, "ike-scan", self.build_folder, bin_dir)
        copy(self, "psk-crack", self.build_folder, bin_dir)
        for filename in ("ike-backoff-patterns", "ike-vendor-ids", "psk-crack-dictionary"):
            copy(self, filename, self.source_folder, data_dir)
        copy(self, "*.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        for filename in ("ike-scan", "psk-crack"):
            path = os.path.join(bin_dir, filename)
            real_path = path + ".bin"
            if os.path.exists(path):
                os.replace(path, real_path)
                save(self, path, self._launcher(filename))
                os.chmod(path, 0o755)
                os.chmod(real_path, 0o755)

    def _launcher(self, filename):
        return """#!/usr/bin/env sh
set -eu
bindir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$bindir"
exec "$bindir/{0}.bin" "$@"
""".format(filename)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
