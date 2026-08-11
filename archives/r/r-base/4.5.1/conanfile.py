#!/usr/bin/env python3
"""Conan 2 recipe for R 4.5.1 on native HarmonyOS aarch64."""
import hashlib
import os
import shlex
import shutil
import subprocess
from contextlib import contextmanager

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class RBaseConan(ConanFile):
    name = "r-base"
    version = "4.5.1"
    description = "R language interpreter and base runtime"
    license = "GPL-2.0-or-later"
    homepage = "https://www.r-project.org/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    _data_root = "/data/storage/el2/base"
    _shell = "/system/bin/sh"
    _clang = "/data/service/hnp/bin/clang"
    _clangxx = "/data/service/hnp/bin/clang++"
    _ar = "/data/service/hnp/bin/llvm-ar"
    _ranlib = "/data/service/hnp/bin/llvm-ranlib"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "curl_https_probe.c", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "cacert.pem", src=os.path.join(self.recipe_folder, "res"), dst=self.export_sources_folder)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("r-base 4.5.1 only supports native OHOS/armv8")

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("pcre2/10.45.1")
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")
        self.requires("libiconv/1.17")
        self.requires("curl/8.15.0#4ae5a3c702753d2fc507808204655813")
        self.requires("openblas/0.3.33#a9af176238a4720b044e1250be00743f")
        self.requires("openssl/3.5.6.1#d871951ad035e2c4eecb6112af441801")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def source(self):
        get(self, **self.conan_data["sources"]["r-base"], strip_root=True)
        apply_conandata_patches(self)
        get(
            self,
            **self.conan_data["sources"]["curl"],
            destination=os.path.join(self.source_folder, "private-curl"),
            strip_root=True,
        )

    def _paths(self):
        root = os.path.join(self._data_root, f"r-base-{self.version}-source")
        return root, os.path.join(root, "src"), os.path.join(root, "build"), os.path.join(root, "stage"), os.path.join(root, "tmp")

    def _reset_root(self, root):
        expected = os.path.join(self._data_root, f"r-base-{self.version}-source")
        if root != expected:
            raise ConanException(f"refusing to reset unexpected path: {root}")
        if os.path.lexists(root):
            if os.path.islink(root):
                os.unlink(root)
            else:
                def _onerror(func, p, exc):
                    try:
                        os.chmod(p, 0o755)
                    except OSError:
                        pass
                    try:
                        os.unlink(p)
                    except OSError:
                        pass
                shutil.rmtree(root, onerror=_onerror)
                if os.path.lexists(root):
                    shutil.rmtree(root)
        os.makedirs(root, mode=0o755)

    def _flang(self):
        folder = self.dependencies.build["flang-ohos"].package_folder
        return folder, os.path.join(folder, "bin", "flang")

    @staticmethod
    def _append_unique(destination, values):
        for value in values:
            if value not in destination:
                destination.append(value)

    def _dependency_contract(self, dependency, transitive=True):
        includes, libdirs, libraries, system_libs = [], [], [], []
        defines, cflags, linkflags, objects = [], [], [], []
        visited = set()

        def collect(current):
            key = str(current.ref)
            if key in visited:
                return
            visited.add(key)
            info = current.cpp_info.aggregated_components()
            if current.package_folder:
                self._append_unique(includes, info.includedirs)
                self._append_unique(libdirs, info.libdirs)
                self._append_unique(objects, info.objects)
                self._append_unique(libraries, info.libs)
                self._append_unique(system_libs, info.system_libs)
                self._append_unique(defines, info.defines)
                self._append_unique(cflags, info.cflags)
                self._append_unique(linkflags, info.sharedlinkflags)
                self._append_unique(linkflags, info.exelinkflags)
            if transitive:
                for child in current.dependencies.host.values():
                    collect(child)

        collect(dependency)
        cpp_tokens = [f"-I{path}" for path in includes]
        cpp_tokens.extend(f"-D{value}" for value in defines)
        cpp_tokens.extend(cflags)
        link_tokens = [f"-L{path}" for path in libdirs]
        link_tokens.extend(objects)
        link_tokens.extend(f"-l{value}" for value in libraries)
        link_tokens.extend(f"-l{value}" for value in system_libs)
        link_tokens.extend(linkflags)
        return cpp_tokens, link_tokens, libdirs

    def _dependency_flags(self):
        includes, libdirs = [], []
        for dependency in self.dependencies.host.values():
            info = dependency.cpp_info.aggregated_components()
            self._append_unique(includes, info.includedirs)
            self._append_unique(libdirs, info.libdirs)
        cppflags = " ".join(shlex.quote(f"-I{path}") for path in includes)
        ldflags = " ".join(shlex.quote(f"-L{path}") for path in libdirs)
        return cppflags, ldflags

    def _verify_private_curl_https(self, build, tmpdir, private_curl):
        cpp_tokens = [f"-I{os.path.join(private_curl, 'include')}"]
        link_tokens = [f"-L{os.path.join(private_curl, 'lib')}", "-lcurl"]
        runtime_dirs = [os.path.join(private_curl, "lib")]
        source = os.path.join(self.export_sources_folder, "curl_https_probe.c")
        binary = os.path.join(build, "conan-curl-https")
        compile_result = subprocess.run(
            [self._clang, source, "-o", binary, *cpp_tokens, *link_tokens],
            check=False,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
        if compile_result.returncode:
            raise ConanException(
                "curl HTTPS consumer failed to link: "
                + compile_result.stdout
                + compile_result.stderr
            )
        run_environment = os.environ.copy()
        run_environment["TMPDIR"] = tmpdir
        run_environment["LD_LIBRARY_PATH"] = os.pathsep.join(runtime_dirs)
        run_result = subprocess.run(
            [binary],
            check=False,
            capture_output=True,
            text=True,
            env=run_environment,
        )
        if run_result.returncode:
            raise ConanException(
                "curl HTTPS consumer did not find the https protocol: "
                + run_result.stdout
                + run_result.stderr
            )
        self.output.info(run_result.stdout.strip())

    def _build_private_curl(self, build):
        source = os.path.join(self.source_folder, "private-curl")
        target = os.path.join(build, "private-curl-build")
        install = os.path.join(build, "private-curl-install")
        rules = os.path.join(build, "private-curl-ohos-rules.cmake")
        openssl = self.dependencies.host["openssl"]
        zlib = self.dependencies.host["zlib"]
        openssl_info = openssl.cpp_info.aggregated_components()
        zlib_info = zlib.cpp_info.aggregated_components()
        openssl_folder = openssl.package_folder
        zlib_folder = zlib.package_folder
        prefix_map = f"{source}=/usr/src/curl-8.15.0"
        flags = " ".join((
            f"-ffile-prefix-map={prefix_map}",
            f"-fmacro-prefix-map={prefix_map}",
            f"-fdebug-prefix-map={prefix_map}",
        ))
        with open(rules, "w", encoding="utf-8") as stream:
            stream.write(chr(10).join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "-Wl,-rpath-link,")',
                'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
            )) + chr(10))
        args = [
            "/data/service/hnp/bin/cmake", "-S", source, "-B", target, "-G", "Ninja",
            "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_INSTALL_PREFIX={install}",
            f"-DCMAKE_C_COMPILER={self._clang}", f"-DCMAKE_C_FLAGS={flags}",
            f"-DCMAKE_USER_MAKE_RULES_OVERRIDE_C={rules}",
            "-DBUILD_SHARED_LIBS=ON", "-DBUILD_STATIC_LIBS=OFF", "-DBUILD_STATIC_CURL=OFF",
            "-DBUILD_CURL_EXE=OFF", "-DBUILD_TESTING=OFF", "-DBUILD_EXAMPLES=OFF",
            "-DCURL_LIBCURL_SOVERSION=OFF", "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            "-DCMAKE_INSTALL_RPATH=$ORIGIN/../lib;$ORIGIN",
            "-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=OFF", "-DCURL_USE_PKGCONFIG=OFF",
            "-DCURL_USE_OPENSSL=ON", "-DOPENSSL_USE_STATIC_LIBS=ON",
            f"-DOPENSSL_ROOT_DIR={openssl_folder}",
            f"-DOPENSSL_INCLUDE_DIR={os.path.join(openssl_folder, openssl_info.includedirs[0])}",
            f"-DOPENSSL_SSL_LIBRARY={os.path.join(openssl_folder, openssl_info.libdirs[0], 'libssl.a')}",
            f"-DOPENSSL_CRYPTO_LIBRARY={os.path.join(openssl_folder, openssl_info.libdirs[0], 'libcrypto.a')}",
            "-DCURL_ZLIB=ON", f"-DZLIB_INCLUDE_DIR={zlib_info.includedirs[0]}",
            f"-DZLIB_LIBRARY={os.path.join(zlib_info.libdirs[0], 'libz.a')}",
            "-DENABLE_ARES=OFF", "-DCURL_BROTLI=OFF", "-DCURL_ZSTD=OFF",
            "-DUSE_NGHTTP2=OFF", "-DUSE_LIBIDN2=OFF", "-DCURL_USE_LIBPSL=OFF",
            "-DCURL_USE_LIBSSH2=OFF", "-DCURL_USE_LIBSSH=OFF", "-DCURL_USE_GSASL=OFF",
            "-DCURL_USE_GSSAPI=OFF", "-DUSE_LIBRTMP=OFF", "-DCURL_DISABLE_LDAP=ON",
            "-DCURL_DISABLE_LDAPS=ON", "-DUSE_NGTCP2=OFF", "-DUSE_NGHTTP3=OFF",
            "-DUSE_QUICHE=OFF", "-DUSE_MSH3=OFF", "-DUSE_OPENSSL_QUIC=OFF",
            "-DHAVE_LINUX_TCP_H=OFF",
        ]
        subprocess.run(args, check=True, env=os.environ.copy())
        subprocess.run(["/data/service/hnp/bin/cmake", "--build", target, "-j2"], check=True)
        subprocess.run(["/data/service/hnp/bin/cmake", "--install", target], check=True)
        library = os.path.join(install, "lib", "libcurl.so")
        if not os.path.isfile(library):
            raise ConanException("private prefix-mapped libcurl was not installed")
        sign = "/data/service/hnp/bin/binary-sign-tool"
        signed = library + ".signed"
        result = subprocess.run(
            [sign, "sign", "-inFile", library, "-outFile", signed, "-selfSign", "1"],
            check=False, capture_output=True, text=True,
        )
        if result.returncode or not os.path.isfile(signed):
            raise ConanException("private prefix-mapped libcurl signing failed: " + result.stderr)
        os.replace(signed, library)
        os.chmod(library, 0o755)
        return install

    @contextmanager
    def _environment(self, work, tmpdir, private_curl):
        flang_folder, flang = self._flang()
        cppflags, ldflags = self._dependency_flags()
        openblas = self.dependencies.host["openblas"]
        openblas_lib = os.path.join(openblas.package_folder, "lib", "libopenblas.so")
        libraries = [openblas_lib]
        env = Environment()
        env.define("PATH", os.pathsep.join(["/data/service/hnp/bin", "/system/bin", "/bin", "/usr/bin", os.environ.get("PATH", "")]))
        env.define("SHELL", self._shell)
        env.define("CONFIG_SHELL", self._shell)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.define("PWD", work)
        env.define("CC", self._clang)
        env.define("CXX", self._clangxx)
        env.define("FC", flang)
        env.define("F77", flang)
        prefix_map = f"{work}=/usr/src/r-base-{self.version}"
        c_prefix_flags = " ".join((
            f"-ffile-prefix-map={prefix_map}",
            f"-fmacro-prefix-map={prefix_map}",
            f"-fdebug-prefix-map={prefix_map}",
        ))
        env.define("CFLAGS", f"-g -O2 {c_prefix_flags}")
        env.define("CXXFLAGS", f"-g -O2 {c_prefix_flags}")
        env.define("FCFLAGS", "-g -O2")
        env.define("FFLAGS", "-g -O2")
        env.define("AR", self._ar)
        env.define("RANLIB", self._ranlib)
        curl_cpp = [f"-I{os.path.join(private_curl, 'include')}"]
        curl_libs = [f"-L{os.path.join(private_curl, 'lib')}", "-lcurl"]
        env.define("CPPFLAGS", cppflags)
        env.define("LDFLAGS", ldflags)
        env.define("CURL_CPPFLAGS", " ".join(shlex.quote(value) for value in curl_cpp))
        env.define("CURL_LIBS", " ".join(shlex.quote(value) for value in curl_libs))
        env.define("FLIBS", " ".join(libraries + ["-lm"]))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(flang_folder, "lib"))
        env.compose_env(VirtualBuildEnv(self).environment())
        with env.vars(self).apply():
            yield

    def build(self):
        root, work, build, stage, tmpdir = self._paths()
        self._reset_root(root)
        shutil.copytree(self.source_folder, work, symlinks=True)
        os.chmod(work, 0o755)
        for path in (build, stage, tmpdir):
            os.makedirs(path, mode=0o755)

        args = [
            "--prefix=/",
            "--without-x",
            "--without-tcltk",
            "--disable-java",
            "--without-readline",
            "--without-recommended-packages",
            "--without-ICU",
            "--without-libpng",
            "--without-jpeglib",
            "--without-libtiff",
            "--without-cairo",
            "--disable-openmp",
            "--with-internal-tzcode",
            f"--with-blas={os.path.join(self.dependencies.host['openblas'].package_folder, 'lib', 'libopenblas.so')}",
            "--with-lapack",
        ]
        configure = os.path.join(work, "configure")
        command = " ".join([shlex.quote(self._shell), shlex.quote(configure)] + [shlex.quote(arg) for arg in args])
        private_curl = self._build_private_curl(build)
        with self._environment(work, tmpdir, private_curl):
            self._verify_private_curl_https(build, tmpdir, private_curl)
            self.run(command, cwd=build, env=None)
            shutil.copy2(os.path.join(self.export_sources_folder, "cacert.pem"), os.path.join(build, "etc", "cacert.pem"))
            self.run("make -j1", cwd=build, env=None)
            self.run("make -j1 check", cwd=build, env=None)
            self.run(f"make -j1 DESTDIR={shlex.quote(stage)} install", cwd=build, env=None)

    def package(self):
        _root, _work, _build, stage, _tmpdir = self._paths()
        if not os.path.isdir(stage):
            raise ConanException(f"R staging directory is missing: {stage}")
        shutil.copytree(stage, self.package_folder, symlinks=False, dirs_exist_ok=True)
        self._prepare_relocatable_runtime()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._sign_elf_files()
        required = [os.path.join(self.package_folder, "bin", name) for name in ("R", "Rscript")]
        if not all(os.path.isfile(path) for path in required):
            raise ConanException("package validation failed: bin/R or bin/Rscript is missing")
        self.output.info("PACKAGE_VALIDATION_R_BINARIES=2/2")

    def _prepare_relocatable_runtime(self):
        rhome = os.path.join(self.package_folder, "lib", "R")
        rlib = os.path.join(rhome, "lib")
        etc = os.path.join(rhome, "etc")
        os.makedirs(rlib, exist_ok=True)
        os.makedirs(etc, exist_ok=True)

        _root, _work, build, _stage, _tmpdir = self._paths()
        curl_library = os.path.join(build, "private-curl-install", "lib", "libcurl.so")
        if not os.path.isfile(curl_library):
            raise ConanException("relocatable runtime requires packaged libcurl.so")
        shutil.copy2(curl_library, os.path.join(rlib, "libcurl.so"))

        openblas_folder = self.dependencies.host["openblas"].package_folder
        openblas_library = os.path.join(openblas_folder, "lib", "libopenblas.so")
        if not os.path.isfile(openblas_library):
            raise ConanException("relocatable runtime requires packaged libopenblas.so")
        shutil.copy2(openblas_library, os.path.join(rlib, "libopenblas.so"))
        shutil.copy2(
            os.path.join(openblas_folder, "lib", "libopenblas.so.0"),
            os.path.join(rlib, "libopenblas.so.0"),
        )
        shutil.copy2(
            os.path.join(self.export_sources_folder, "cacert.pem"),
            os.path.join(etc, "cacert.pem"),
        )

        ldpaths = os.path.join(etc, "ldpaths")
        with open(ldpaths, "w", encoding="utf-8") as stream:
            stream.write('R_LD_LIBRARY_PATH="${R_HOME}/lib"\n')
            stream.write('if test -z "${LD_LIBRARY_PATH}"; then\n')
            stream.write('  LD_LIBRARY_PATH="${R_LD_LIBRARY_PATH}"\n')
            stream.write('else\n')
            stream.write('  LD_LIBRARY_PATH="${R_LD_LIBRARY_PATH}:${LD_LIBRARY_PATH}"\n')
            stream.write('fi\nexport LD_LIBRARY_PATH\n')

        makeconf = os.path.join(etc, "Makeconf")
        if os.path.exists(makeconf):
            with open(makeconf, "r", encoding="utf-8") as stream:
                lines = stream.readlines()
            blocked = ("/storage/Users/", ".conan2", ".conan-build-")
            safe = []
            for line in lines:
                if any(token in line for token in blocked):
                    key = line.split("=", 1)[0].strip() if "=" in line else ""
                    if key in {"CPPFLAGS", "LDFLAGS", "FLIBS", "FC", "F77"}:
                        replacement = {"FC": "false", "F77": "false"}.get(key, "")
                        safe.append(f"{key} = {replacement}\n")
                    else:
                        safe.append("## removed non-relocatable build-cache metadata\n")
                else:
                    safe.append(line)
            with open(makeconf, "w", encoding="utf-8") as stream:
                stream.writelines(safe)

        libtool = os.path.join(rhome, "bin", "libtool")
        if os.path.exists(libtool):
            os.remove(libtool)

        public_rscript = os.path.join(self.package_folder, "bin", "Rscript")
        wrapper = """#!/system/bin/sh
script_dir=`dirname "$0"`
script_dir=`cd "$script_dir" 2>/dev/null && pwd -P`
RHOME=`cd "$script_dir/../lib/R" 2>/dev/null && pwd -P`
if test -z "$RHOME" || ! test -x "$RHOME/bin/Rscript"; then
    echo "Rscript: relocatable R home not found" >&2
    exit 1
fi
export RHOME
exec "$RHOME/bin/Rscript" "$@"
"""
        with open(public_rscript, "w", encoding="utf-8") as stream:
            stream.write(wrapper)
        os.chmod(public_rscript, 0o755)
        self._strip_elf_debug_paths()
        self._reject_build_paths()

    def _strip_elf_debug_paths(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(objcopy) or not os.path.isfile(readelf):
            raise ConanException("ELF debug stripping tools are missing")
        for root, _dirs, files in os.walk(self.package_folder):
            for filename in files:
                path = os.path.join(root, filename)
                header = subprocess.run(
                    [readelf, "-h", path], check=False, capture_output=True
                )
                if header.returncode:
                    continue
                sections = subprocess.run(
                    [readelf, "-S", path], check=False, capture_output=True
                )
                if sections.returncode or b".debug_" not in sections.stdout:
                    continue
                stripped = path + ".stripped"
                result = subprocess.run(
                    [objcopy, "--strip-debug", path, stripped],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode or not os.path.isfile(stripped):
                    raise ConanException(
                        f"failed to strip ELF debug paths from {path}: {result.stderr}"
                    )
                os.replace(stripped, path)
                os.chmod(path, 0o755)

    def _reject_build_paths(self):
        forbidden = (
            b"/storage/Users/currentUser",
            b".conan2",
            b".conan-build-r-base",
        )
        offenders = []
        for root, _dirs, files in os.walk(self.package_folder):
            for filename in files:
                path = os.path.join(root, filename)
                try:
                    with open(path, "rb") as stream:
                        data = stream.read()
                except OSError:
                    continue
                strings = data.split(bytes((0,)))
                allowed_compiler = (
                    b"$compiler: clang --target=aarch64-linux-ohos -fPIC -pthread "
                    b"-fPIC -O2 -fPIC -DOPENSSL_USE_NODELETE -DOPENSSL_PIC "
                    b"-DOPENSSL_BUILDING_OPENSSL -DNDEBUG "
                    b"-I/storage/Users/currentUser/usr/local/include"
                )
                bad = False
                for value in strings:
                    if not any(token in value for token in forbidden):
                        continue
                    if value == allowed_compiler or value.endswith(allowed_compiler):
                        continue
                    bad = True
                    break
                if bad:
                    offenders.append(os.path.relpath(path, self.package_folder))
        if offenders:
            raise ConanException(
                "non-relocatable build paths remain: " + ", ".join(offenders[:20])
            )

    def _sign_elf_files(self):
        sign = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign) or not os.path.isfile(objcopy):
            raise ConanException("ELF signing tools are missing")
        failures = []
        for root, _dirs, files in os.walk(self.package_folder):
            for filename in files:
                path = os.path.join(root, filename)
                try:
                    with open(path, "rb") as stream:
                        if stream.read(4) != bytes.fromhex("7f454c46"):
                            continue
                except OSError:
                    continue
                signed = path + ".signed"
                subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False, capture_output=True)
                result = subprocess.run([sign, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"], check=False, capture_output=True, text=True)
                if result.returncode or not os.path.isfile(signed):
                    failures.append(f"{path}: {result.stderr.strip() or result.returncode}")
                    continue
                os.replace(signed, path)
                os.chmod(path, 0o755)
        if failures:
            raise ConanException("ELF signing failed:\n" + "\n".join(failures))

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        rhome = os.path.join(self.package_folder, "lib", "R")
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", bindir)
        self.runenv_info.define_path("R_HOME", rhome)
        self.runenv_info.define_path("RHOME", rhome)
        self.buildenv_info.prepend_path("PATH", bindir)
        self.buildenv_info.define_path("R_HOME", rhome)
        self.buildenv_info.define_path("RHOME", rhome)
