#!/usr/bin/env python3
"""Conan recipe for the Homebrew gcli 2.12.0 task."""
import os
import shlex
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class GcliConan(ConanFile):
    name = "gcli"
    version = "2.12.0"
    package_type = "application"

    description = "Portable command-line client for Git forges"
    license = "BSD-2-Clause"
    homepage = "https://sr.ht/~herrhotzenplotz/gcli"
    url = "https://git.sr.ht/~herrhotzenplotz/gcli"
    topics = ("github", "gitlab", "gitea", "bugzilla", "cli")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        res_src = os.path.join(self.recipe_folder, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.export_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("gcli supports Linux/OHOS builds only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        curl_src = os.path.join(self.source_folder, "_curl")
        if os.path.exists(curl_src):
            shutil.rmtree(curl_src)
        get(self, **self.conan_data["curl_source"], destination=curl_src, strip_root=True)
        export_dir = os.path.join(os.path.dirname(self.source_folder), "e")
        res_src = os.path.join(export_dir, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.source_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def generate(self):
        self._write_libcurl_pc()
        self._write_libcrypto_pc()

    def _default_prefix(self):
        return os.environ.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")

    def _resource_headers(self):
        return os.path.join(self.source_folder, "res", "headers")

    def _curl_prefix(self):
        return os.path.join(self.build_folder, "curl-prefix")

    def _dep_folder(self, name):
        return self.dependencies[name].package_folder

    def _machine(self):
        arch = str(self.settings.arch)
        machines = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "armv8.4": "aarch64",
            "x86_64": "x86_64",
            "x86": "i686",
            "armv7": "armv7a",
        }
        machine = machines.get(arch)
        if machine is None:
            raise ConanInvalidConfiguration(f"unsupported gcli architecture: {arch}")
        return machine

    def _build_triplet(self):
        return f"{self._machine()}-unknown-linux-gnu"

    def _host_triplet(self):
        if self.settings.os == "OHOS":
            return f"{self._machine()}-unknown-linux-ohos"
        return f"{self._machine()}-unknown-linux-gnu"

    def _write_pc(self, filename, prefix, name, description, version, libs, cflags="-I${includedir}"):
        os.makedirs(self.generators_folder, exist_ok=True)
        pc_path = os.path.join(self.generators_folder, filename)
        with open(pc_path, "w", encoding="utf-8") as pc:
            pc.write(
                f"prefix={prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n\n"
                f"Name: {name}\n"
                f"Description: {description}\n"
                f"Version: {version}\n"
                f"Libs: {libs}\n"
                f"Cflags: {cflags}\n"
            )

    def _write_libcurl_pc(self):
        openssl = self._dep_folder("openssl")
        zlib = self._dep_folder("zlib")
        self._write_pc(
            "libcurl.pc",
            self._curl_prefix(),
            "libcurl",
            "Private static libcurl built inside the gcli recipe",
            "8.15.0",
            " ".join([
                "-L${libdir}",
                "-lcurl",
                f"-L{openssl}/lib",
                "-lssl",
                "-lcrypto",
                f"-L{zlib}/lib",
                "-lz",
                "-ldl",
                "-pthread",
            ]),
            f"-I${{includedir}} -I{openssl}/include -I{zlib}/include",
        )

    def _write_libcrypto_pc(self):
        openssl = self._dep_folder("openssl")
        self._write_pc(
            "libcrypto.pc",
            openssl,
            "libcrypto",
            "OpenSSL crypto library from Conan openssl/3.5.6",
            "3.5.6",
            "-L${libdir} -lcrypto -ldl -pthread",
        )

    def _pkg_config_path(self):
        sysroot = self._default_prefix()
        paths = [
            self.generators_folder,
            os.path.join(sysroot, "lib", "pkgconfig"),
            os.path.join(sysroot, "share", "pkgconfig"),
        ]
        existing = os.environ.get("PKG_CONFIG_PATH")
        if existing:
            paths.append(existing)
        return os.pathsep.join(paths)

    def _append_env(self, name, value):
        existing = os.environ.get(name, "")
        return f"{existing} {value}".strip()

    def _env_prefix(self):
        sysroot = self._default_prefix()
        curl_prefix = self._curl_prefix()
        openssl = self._dep_folder("openssl")
        zlib = self._dep_folder("zlib")
        resource_headers = self._resource_headers()
        assignments = {
            "PKG_CONFIG_PATH": self._pkg_config_path(),
            "CPPFLAGS": self._append_env(
                "CPPFLAGS",
                " ".join([
                    f"-I{curl_prefix}/include",
                    f"-I{openssl}/include",
                    f"-I{zlib}/include",
                    f"-I{resource_headers}",
                    f"-I{sysroot}/include",
                ]),
            ),
            "LDFLAGS": self._append_env(
                "LDFLAGS",
                " ".join([
                    f"-L{curl_prefix}/lib",
                    f"-L{openssl}/lib",
                    f"-L{zlib}/lib",
                    f"-L{sysroot}/lib",
                    f"-Wl,-rpath,{sysroot}/lib",
                ]),
            ),
            "CCACHE": "env",
        }
        return " ".join(f"{key}={shlex.quote(value)}" for key, value in assignments.items())

    def _build_private_curl(self):
        curl_src = os.path.join(self.source_folder, "_curl")
        self._patch_curl_config_sub(curl_src)
        self._patch_curl_configure(curl_src)
        openssl = self._dep_folder("openssl")
        zlib = self._dep_folder("zlib")
        args = [
            f"--prefix={self._curl_prefix()}",
            "--disable-shared",
            "--enable-static",
            f"--with-openssl={openssl}",
            f"--with-zlib={zlib}",
            "--without-libpsl",
            "--without-brotli",
            "--without-zstd",
            "--without-nghttp2",
            "--without-ngtcp2",
            "--without-nghttp3",
            "--disable-ldap",
            "--disable-ldaps",
            "--disable-rtsp",
            "--disable-dict",
            "--disable-telnet",
            "--disable-tftp",
            "--disable-pop3",
            "--disable-imap",
            "--disable-smb",
            "--disable-smtp",
            "--disable-gopher",
            "--disable-mqtt",
            "--disable-manual",
            "--disable-docs",
            "--disable-dependency-tracking",
            f"--build={self._build_triplet()}",
            f"--host={self._host_triplet()}",
        ]
        assignments = {
            "CPPFLAGS": self._append_env(
                "CPPFLAGS",
                f"-I{openssl}/include -I{zlib}/include",
            ),
            "LDFLAGS": self._append_env(
                "LDFLAGS",
                f"-L{openssl}/lib -L{zlib}/lib",
            ),
            "LIBS": self._append_env("LIBS", "-ldl -pthread"),
        }
        env_prefix = " ".join(f"{key}={shlex.quote(value)}" for key, value in assignments.items())
        self.run(f"{env_prefix} {shlex.quote(os.path.join(curl_src, 'configure'))} {' '.join(args)}", cwd=curl_src)
        self.run("make -j1", cwd=curl_src)
        self.run("make install", cwd=curl_src)

    def _patch_curl_config_sub(self, curl_src):
        config_sub = os.path.join(curl_src, "config.sub")
        if not os.path.isfile(config_sub):
            raise ConanInvalidConfiguration("curl config.sub is missing")
        original = config_sub + ".orig"
        if not os.path.exists(original):
            shutil.copy2(config_sub, original)
        with open(config_sub, "w", encoding="utf-8") as script:
            script.write(
                "#!/bin/sh\n"
                "case \"$1\" in\n"
                "    *-linux-ohos) echo \"$1\"; exit 0 ;;\n"
                "esac\n"
                "exec \"$(dirname \"$0\")/config.sub.orig\" \"$@\"\n"
            )
        os.chmod(config_sub, os.stat(config_sub).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def _patch_curl_configure(self, curl_src):
        configure = os.path.join(curl_src, "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration("curl configure is missing")
        replace_in_file(self, configure, "umask 077", "umask 022", strict=False)

    def _patch_configure(self, configure):
        replace_in_file(
            self,
            configure,
            """\tfor x in $*; do
\t\tif command -v $x >/dev/null 2>&1 && [ -x $(command -v $x) ]; then
\t\t\tbinary="$(command -v $x)"
\t\t\tprintf " $binary\\n" >&2
\t\t\techo "${binary}"
\t\t\texit 0
\t\tfi
\tdone
""",
            """\tfor x in $*; do
\t\tbinary="$(command -v "$x" 2>/dev/null || true)"
\t\tcase "$binary" in
\t\t\t*=*) binary="${binary#*=}" ;;
\t\tesac
\t\tif [ -n "$binary" ]; then
\t\t\tprintf " $binary\\n" >&2
\t\t\techo "${binary}"
\t\t\texit 0
\t\tfi
\tdone
""",
            strict=True,
        )
        replace_in_file(
            self,
            configure,
            """REALPATH=${REALPATH:-$(find_program realpath realpath grealpath)}
[ $? -eq 0 ] || die "error: need realpath" # exit code of find_program()
""",
            """REALPATH=${REALPATH:-$(find_program realpath realpath grealpath)}
[ -n "${REALPATH}" ] || die "error: need realpath"
""",
            strict=True,
        )

    def _patch_makefile_in(self):
        makefile_in = os.path.join(self.source_folder, "Makefile.in")
        replace_in_file(
            self,
            makefile_in,
            """lex.yy.c: y.tab.h @SRCDIR@/src/pgen/lexer.l
\t$(LEX) @SRCDIR@/src/pgen/lexer.l
""",
            """lex.yy.c: @SRCDIR@/res/pgen_lexer.c
\tcp @SRCDIR@/res/pgen_lexer.c lex.yy.c
""",
            strict=True,
        )
        replace_in_file(
            self,
            makefile_in,
            "lex.yy.pgen$(OBJEXT_FOR_BUILD): lex.yy.c\n",
            "lex.yy.pgen$(OBJEXT_FOR_BUILD): y.tab.h lex.yy.c\n",
            strict=True,
        )

    def build(self):
        args = [
            "--prefix=/",
            "--disable-libedit",
            "--disable-libreadline",
            "--disable-liblowdown",
            "--disable-librt",
            "--release",
        ]
        configure = os.path.join(self.source_folder, "configure")
        self._patch_configure(configure)
        self._patch_makefile_in()
        self._build_private_curl()
        self.run(f"{self._env_prefix()} {shlex.quote(configure)} {' '.join(args)}")
        self.run("make -j1")

    def _sign_binary(self, path):
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(path) and os.path.isfile(sign_tool)):
            return
        if os.path.isfile(objcopy):
            self.run(f"{objcopy} --remove-section .codesign {path}", quiet=True)
        tmp_signed = path + ".signed"
        self.run(f"{sign_tool} sign -inFile {path} -outFile {tmp_signed} -selfSign 1", quiet=True)
        os.replace(tmp_signed, path)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package(self):
        self.run(f"make install DESTDIR={shlex.quote(self.package_folder)}")
        gcli = os.path.join(self.package_folder, "bin", "gcli")
        if os.path.isfile(gcli):
            os.chmod(gcli, os.stat(gcli).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            self._sign_binary(gcli)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        sysroot = self._default_prefix()
        for dep_name in ("openssl", "zlib"):
            dep_folder = self._dep_folder(dep_name)
            if dep_folder:
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(dep_folder, "lib"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(sysroot, "lib"))
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
