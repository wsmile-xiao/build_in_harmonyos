#!/usr/bin/env python3
"""Conan recipe for xapian-core 1.4.22."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import load_toolchain_args
from conan.tools.files import collect_libs, get, load, replace_in_file, save
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XapianCoreConan(ConanFile):
    name = "xapian-core"
    version = "1.4.22"
    description = "Search engine library with probabilistic information retrieval APIs"
    license = "GPL-2.0-or-later"
    homepage = "https://xapian.org/"
    url = "https://xapian.org/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-documentation")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        self._patch_sources()
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            os.chmod(configure, 0o755)
        autotools = Autotools(self)
        configure_args = self._load_configure_args()
        if self.settings.os == "OHOS":
            replace_in_file(self, configure, "umask 077 && mktemp -d", "umask 022 && mktemp -d")
            replace_in_file(self, configure, 'umask 077 && mkdir "$tmp"', 'umask 022 && mkdir "$tmp"')
            config_shell = shutil.which("bash") or "/system/bin/sh"
            cc = shutil.which("clang") or os.environ.get("CC", "clang")
            cxx = shutil.which("clang++") or os.environ.get("CXX", "clang++")
            cc_cmd = f"{config_shell} {cc}"
            cxx_cmd = f"{config_shell} {cxx}"
            ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
            ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib") or "ranlib"
            nm = shutil.which("llvm-nm") or shutil.which("nm") or "nm"
            ld = shutil.which("ld.lld") or shutil.which("ld") or "ld"
            self.run(
                f'CC="{cc_cmd}" CXX="{cxx_cmd}" AR="{ar}" RANLIB="{ranlib}" NM="{nm}" '
                f'LD="{ld}" CONFIG_SHELL="{config_shell}" '
                f'"{config_shell}" "{configure}" {configure_args}'
            )
        else:
            config_shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "sh"
            self.run(f'CONFIG_SHELL="{config_shell}" "{config_shell}" "{configure}" {configure_args}')
        if self.settings.os == "OHOS":
            self._fix_empty_version_header()
        autotools.make()

    def _load_configure_args(self):
        return load_toolchain_args(self.generators_folder).get("configure_args")

    def _patch_sources(self):
        config_guess = os.path.join(self.source_folder, "config.guess")
        replace_in_file(
            self,
            config_guess,
            "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n    *:NetBSD:*:*)",
            """case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in
    *:HarmonyOS:*:*)
\tcase "$UNAME_MACHINE" in
\t    aarch64|arm64) MACHINE=aarch64 ;;
\t    armv7*|armv8*) MACHINE=arm ;;
\t    x86_64|amd64)  MACHINE=x86_64 ;;
\t    i?86)          MACHINE=i686 ;;
\t    *)             MACHINE="$UNAME_MACHINE" ;;
\tesac
\tGUESS=${MACHINE}-unknown-linux-ohos
\t;;
    *:NetBSD:*:*)""",
            strict=True,
        )

        config_sub = os.path.join(self.source_folder, "config.sub")
        replace_in_file(
            self,
            config_sub,
            """\t\t\tandroid-linux)
\t\t\t\tbasic_machine=$field1-unknown
\t\t\t\tbasic_os=linux-android
\t\t\t\t;;
\t\t\t*)""",
            """\t\t\tandroid-linux)
\t\t\t\tbasic_machine=$field1-unknown
\t\t\t\tbasic_os=linux-android
\t\t\t\t;;
\t\t\tohos-linux)
\t\t\t\tbasic_machine=$field1-unknown
\t\t\t\tbasic_os=linux-ohos
\t\t\t\t;;
\t\t\t*)""",
            strict=True,
        )
        replace_in_file(
            self,
            config_sub,
            "gnu* | android* | bsd* | mach* | minix* | genix* | ultrix* | irix* \\",
            "gnu* | android* | ohos* | bsd* | mach* | minix* | genix* | ultrix* | irix* \\",
            strict=True,
        )
        replace_in_file(
            self,
            config_sub,
            "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \\",
            "linux-gnu* | linux-dietlibc* | linux-android* | linux-ohos* | linux-newlib* \\",
            strict=True,
        )

        uuids = os.path.join(self.source_folder, "backends", "uuids.cc")
        replace_in_file(
            self,
            uuids,
            """    int fd = open("/proc/sys/kernel/random/uuid", O_RDONLY);
    if (rare(fd == -1)) {
\tthrow Xapian::DatabaseCreateError("Opening UUID generator failed", errno);
    }
    bool failed = (read(fd, buf, STRING_SIZE) != STRING_SIZE);
    close(fd);
    if (failed) {
\tthrow Xapian::DatabaseCreateError("Generating UUID failed");
    }
    parse(buf);""",
            """    int fd = open("/proc/sys/kernel/random/uuid", O_RDONLY);
    if (fd != -1) {
\tbool failed = (read(fd, buf, STRING_SIZE) != STRING_SIZE);
\tclose(fd);
\tif (failed) {
\t    throw Xapian::DatabaseCreateError("Generating UUID failed");
\t}
\tparse(buf);
\treturn;
    }

    fd = open("/dev/urandom", O_RDONLY);
    if (rare(fd == -1)) {
\tthrow Xapian::DatabaseCreateError("Opening UUID generator failed", errno);
    }
    bool failed = (read(fd, uuid_data, BINARY_SIZE) != BINARY_SIZE);
    close(fd);
    if (failed) {
\tthrow Xapian::DatabaseCreateError("Generating UUID failed");
    }

    // Mark as RFC 4122 variant, version 4 random UUID.
    uuid_data[6] = (uuid_data[6] & 0x0f) | 0x40;
    uuid_data[8] = (uuid_data[8] & 0x3f) | 0x80;""",
            strict=True,
        )

        api_backend = os.path.join(self.source_folder, "tests", "api_backend.cc")
        replace_in_file(
            self,
            api_backend,
            """\tstring path = get_named_writable_database_path("lockfileumask1");
\tpath += "/flintlock";

\tstruct stat statbuf;
\tTEST(stat(path.c_str(), &statbuf) == 0);
\tTEST_EQUAL(statbuf.st_mode & 0777, 0644);""",
            """\tstring path = get_named_writable_database_path("lockfileumask1");
\tstring probe_path = path;
\tpath += "/flintlock";
\tprobe_path += "/umaskprobe";
\tint fd = open(probe_path.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0666);
\tTEST(fd != -1);
\tTEST(close(fd) == 0);

\tstruct stat statbuf;
\tTEST(stat(probe_path.c_str(), &statbuf) == 0);
\tmode_t expected_mode = statbuf.st_mode & 0777;
\tTEST(unlink(probe_path.c_str()) == 0);
\tTEST(stat(path.c_str(), &statbuf) == 0);
\tTEST_EQUAL(statbuf.st_mode & 0777, expected_mode);""",
            strict=True,
        )

        for script in ("runsrv.in", "runtest.in"):
            replace_in_file(
                self,
                os.path.join(self.source_folder, "tests", script),
                "#!/bin/sh",
                "#!@SHELL@",
                strict=True,
            )

    def _fix_empty_version_header(self):
        version_h = os.path.join(self.build_folder, "include", "xapian", "version.h")
        visibility_define = self._visibility_define()
        if os.path.isfile(version_h) and os.path.getsize(version_h) > 0:
            if visibility_define:
                content = load(self, version_h)
                if "#define XAPIAN_ENABLE_VISIBILITY" not in content:
                    content = content.replace(
                        "#define XAPIAN_INCLUDED_VERSION_H\n",
                        f"#define XAPIAN_INCLUDED_VERSION_H\n\n{visibility_define}",
                        1,
                    )
                    save(self, version_h, content)
            return

        content = f"""\
#ifndef XAPIAN_INCLUDED_VERSION_H
#define XAPIAN_INCLUDED_VERSION_H

{visibility_define}\
#define XAPIAN_VERSION "{self.version}"
#define XAPIAN_MAJOR_VERSION 1
#define XAPIAN_MINOR_VERSION 4
#define XAPIAN_REVISION 22

#define XAPIAN_DOCID_BASE_TYPE int
#define XAPIAN_TERMCOUNT_BASE_TYPE int
#define XAPIAN_TERMPOS_BASE_TYPE int
#define XAPIAN_TOTALLENGTH_TYPE unsigned long
#define XAPIAN_REVISION_TYPE unsigned long

#define XAPIAN_HAS_CHERT_BACKEND 1
#define XAPIAN_HAS_GLASS_BACKEND 1
#define XAPIAN_HAS_INMEMORY_BACKEND 1
#define XAPIAN_HAS_REMOTE_BACKEND 1

#define XAPIAN_AT_LEAST(A,B,C) \\
 (XAPIAN_MAJOR_VERSION > (A) || \\
 (XAPIAN_MAJOR_VERSION == (A) && \\
 (XAPIAN_MINOR_VERSION > (B) || \\
 (XAPIAN_MINOR_VERSION == (B) && XAPIAN_REVISION >= (C)))))

#ifndef XAPIAN_MOVE_SEMANTICS
# if __cplusplus >= 201103L || defined XAPIAN_LIB_BUILD
# define XAPIAN_MOVE_SEMANTICS
# endif
#endif

#endif /* XAPIAN_INCLUDED_VERSION_H */
"""
        save(self, version_h, content)
        save(self, os.path.join(self.build_folder, "include", "xapian", "version.h.timestamp"), "")

    def _visibility_define(self):
        makefile = os.path.join(self.build_folder, "Makefile")
        if os.path.isfile(makefile) and "-fvisibility=hidden" in load(self, makefile):
            return "#define XAPIAN_ENABLE_VISIBILITY\n\n"
        return ""

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        config = os.path.join(self.package_folder, "bin", "xapian-config")
        if os.path.isfile(config):
            os.chmod(config, 0o755)

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["xapian"]
        self.cpp_info.set_property("cmake_file_name", "xapian")
        self.cpp_info.set_property("cmake_target_name", "xapian::xapian")
        self.cpp_info.set_property("pkg_config_name", "xapian-core")
        self.cpp_info.requires = ["zlib::zlib"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
