from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, \
    export_conandata_patches, download
import os

required_conan_version = ">=2.0"


class LsquicConan(ConanFile):
    name = "lsquic"
    version = "4.9.4"
    description = ("LiteSpeed QUIC (LSQUIC) Library - open-source "
                   "implementation of QUIC and HTTP/3 functionality")
    license = "MIT"
    url = "https://github.com/litespeedtech/lsquic"
    homepage = "https://github.com/litespeedtech/lsquic"
    topics = ("quic", "http3", "network", "transport")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The GitHub release tarball does not include the two git
        # submodules (ls-qpack, lshpack) which are required to build.
        # conandata.yml lists all three official tarballs; the submodule
        # archives are unpacked into place after the main source.
        import shutil
        import tarfile
        # CI rewrites "url:" into a mirror-fallback list (conan get()
        # natively accepts both a single string and a list of mirrors).
        main_kwargs = {k: v for k, v in self.conan_data["sources"].items()
                       if k not in ("ls_qpack", "ls_hpack")}
        get(self, **main_kwargs, strip_root=True)
        for sub_key, target in (("ls_qpack", "src/liblsquic/ls-qpack"),
                                ("ls_hpack", "src/lshpack")):
            sub = self.conan_data["sources"][sub_key]
            sub_urls = sub["url"] if isinstance(sub["url"], list) \
                       else [sub["url"]]
            archive = None
            last_err = None
            for url in sub_urls:
                archive = os.path.join(self.source_folder, f"{sub_key}.tar.gz")
                try:
                    download(self, url, archive, sha256=sub["sha256"])
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    archive = None
            if last_err is not None:
                raise last_err
            with tarfile.open(archive) as tf:
                members = tf.getmembers()
                tops = {m.name.split("/")[0] for m in members
                        if "/" in m.name}
                if len(tops) != 1:
                    raise ConanInvalidConfiguration(
                        f"{sub_key}: expected one top-level dir, got {sorted(tops)}")
                tf.extractall(self.source_folder,
                              filter="tar" if hasattr(tarfile, "tar_filter")
                                     else None)
            top = tops.pop()
            dest = os.path.join(self.source_folder, target)
            # shutil.move onto an existing dir nests instead of
            # replacing; make the destination deterministic.
            if os.path.exists(dest):
                shutil.rmtree(dest)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(os.path.join(self.source_folder, top), dest)
            os.unlink(archive)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMakeLists declares cmake_minimum_required(3.0...3.23); toolchain
        # CMake 4.x needs the policy floor on the command line.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # lsquic's CMake probes (check_symbol_exists on SSL_set_quic_tls_cbs)
        # need a full compile+link against the OpenSSL package; the probe
        # fails in cross builds.  LSQUIC_LIBSSL=OPENSSL skips detection and
        # defines HAVE_OPENSSL directly (openssl >= 3.5 provides the
        # SSL_set_quic_tls_cbs pull-model QUIC TLS API used by the port).
        tc.variables["LSQUIC_LIBSSL"] = "OPENSSL"
        # The library is the deliverable; example binaries need libevent
        # and tests need a Debug build with a network environment.
        tc.variables["LSQUIC_BIN"] = False
        tc.variables["LSQUIC_TESTS"] = False
        # lsquic does not use find_package(OpenSSL); feed the conan
        # package paths to its custom variables instead.
        openssl = self.dependencies["openssl"]
        openssl_info = openssl.cpp_info.aggregated_components()
        tc.variables["SSLLIB_INCLUDE"] = openssl_info.includedirs[0]
        for libdir in openssl_info.libdirs:
            for libname in ("ssl", "crypto"):
                candidate = os.path.join(libdir, f"lib{libname}.a")
                if os.path.exists(candidate):
                    tc.variables[f"LIBSSL_LIB_{libname}"] = candidate
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["lsquic"]
        self.cpp_info.set_property("cmake_file_name", "lsquic")
        self.cpp_info.set_property("cmake_target_name", "lsquic::lsquic")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m", "c++_static"]
