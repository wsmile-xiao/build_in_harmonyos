import os
import shlex
from pathlib import Path
from conan import ConanFile
from conan.tools.files import replace_in_file
from conan.tools.files import get, copy, rm, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment, VirtualRunEnv


class LibpagemakerConan(ConanFile):
    name = "libpagemaker"
    version = "0.0.4"
    package_type = "library"
    license = "MPL-2.0"
    homepage = "https://wiki.documentfoundation.org/DLP/Libraries/libpagemaker"
    description = "Adobe PageMaker document importer"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Public PageMaker headers expose RVNG stream/drawing types to consumers.
        self.requires("librevenge/0.0.5", transitive_headers=True, transitive_libs=True)
        # Match librevenge's published full-header Boost provider, not the
        # newer application-specific slim provider with absent headers.
        self.requires("boost/1.90.0.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local = os.environ.get("LIBPAGEMAKER_SOURCE_ARCHIVE")
        if local:
            source["url"] = Path(local).resolve(strict=True).as_uri()
        get(self, **source, strip_root=True)

    def generate(self):
        # Do not inject dependency-global -L paths: Libtool would select
        # relocated provider .la metadata ahead of the scoped archive path.
        tc = AutotoolsToolchain(self)
        # Preserve dependency header closure without global Libtool -L paths.
        for dep in self.dependencies.host.values():
            for item in dep.cpp_info.includedirs:
                directory = item if os.path.isabs(item) else os.path.join(dep.package_folder, item)
                tc.extra_cxxflags.append("-I" + shlex.quote(directory))
        tc.configure_args.extend(["--without-docs", "--disable-tools", "--disable-werror",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static"])
        tc.generate()
        VirtualRunEnv(self).generate()
        env = Environment()
        for dep in self.dependencies.host.values():
            for item in dep.cpp_info.libdirs:
                directory = item if os.path.isabs(item) else os.path.join(dep.package_folder, item)
                if os.path.isdir(directory):
                    env.prepend_path("LD_LIBRARY_PATH", directory)
        revenge = self.dependencies["librevenge"].package_folder
        includes = "-I" + shlex.quote(os.path.join(revenge, "include", "librevenge-0.0"))
        shadow = os.path.join(self.build_folder, "private-revenge-archives")
        for name in ("librevenge-0.0.a", "librevenge-stream-0.0.a", "librevenge-generators-0.0.a"):
            if not os.path.isfile(os.path.join(revenge, "lib", name)):
                raise RuntimeError("Expected published static archive missing: " + name)
            copy(self, name, os.path.join(revenge, "lib"), shadow, keep_path=False)
        if any(Path(shadow).glob("*.la")):
            raise RuntimeError("Private dependency directory must be .la-free")
        libs = "-L" + shlex.quote(shadow)
        for prefix, name in (("REVENGE", "revenge-0.0"), ("REVENGE_STREAM", "revenge-stream-0.0")):
            env.define(prefix + "_CFLAGS", includes)
            env.define(prefix + "_LIBS", libs + " -l" + name)
        zlib = self.dependencies["zlib"].package_folder
        env.append("REVENGE_STREAM_LIBS", "-L" + shlex.quote(os.path.join(zlib, "lib")) + " -lz")
        env.define("BOOST_CFLAGS", "-I" + shlex.quote(os.path.join(self.dependencies["boost"].package_folder, "include")))
        env.vars(self).save_script("conanbuildenv_private_deps")

    def _configure_tmpdir(self):
        # HMDFS preserves creation-time access semantics; chmod afterward
        # cannot repair Autoconf's private 0700 temporary directories.
        configure = os.path.join(self.source_folder, "configure")
        original_stat = os.stat(configure)
        replacements = (
            ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
             'tmp="${TMPDIR:-.}/conf$$-$RANDOM"; (umask 022 && mkdir "$tmp") &&'),
            ('tmp=./conf$$-$RANDOM', 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"'),
            ('(umask 077 && mkdir "$tmp")', '(umask 022 && mkdir "$tmp")'),
        )
        for old, new in replacements:
            replace_in_file(self, configure, old, new, strict=True)
        os.utime(configure, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        scratch = os.path.join(self.build_folder, ".autoconf-tmp")
        previous = os.umask(0o022)
        try:
            os.mkdir(scratch, mode=0o755)
        finally:
            os.umask(previous)
        return scratch

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
            guess = os.path.join(self.source_folder, "config.guess")
            self.run("sh " + shlex.quote(guess))
            self.run("sh " + shlex.quote(os.path.join(self.source_folder, "config.sub")) + " aarch64-unknown-linux-ohos")
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            scratch = self._configure_tmpdir()
            # Prefix after Conan activation, so the ambient TMPDIR cannot win.
            configure = shlex.quote(os.path.join(self.source_folder, "configure"))
            self.run("TMPDIR=" + shlex.quote(scratch) + " sh " + configure +
                     " " + autotools._configure_args, env=["conanbuild", "conanrun"])
        else:
            autotools.configure()
        autotools.make(args=["-j2"])
        autotools.make(target="check", args=["-j1"])
        self.output.info("UPSTREAM_RELEASE_CHECK_COMPLETE registered_tests=0")

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["pagemaker-0.0"]
        self.cpp_info.includedirs = ["include/libpagemaker-0.0"]
        self.cpp_info.set_property("cmake_file_name", "libpagemaker")
        self.cpp_info.set_property("cmake_target_name", "libpagemaker::libpagemaker")
        self.cpp_info.set_property("pkg_config_name", "libpagemaker-0.0")
