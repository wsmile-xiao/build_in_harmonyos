from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

import os
import shutil


def _prepare_autotools_env():
    """The automake/aclocal/libtoolize pulled in as tool_requires hardcode
    absolute interpreter paths for autoconf/autom4te/sed that may not exist
    in this environment.  Point the env vars at whatever is on PATH."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(path):
    """E114/E011: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` (and the now-orphaned parentheses) from the generated
    configure so it and its config.status can create their temp dirs."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class LibconfigConan(ConanFile):
    name = "libconfig"
    version = "1.8"
    description = "C/C++ configuration file processing library"
    license = "LGPL-2.1"
    homepage = "https://github.com/hyperrealm/libconfig"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # The v1.8 git tag archive ships no pre-generated `configure`, so
        # build() must run `autoreconf` to bootstrap.  The CI build host only
        # ships the autoconf suite under /data/service/hnp/bin (no automake /
        # libtoolize), so pull them in as tool_requires (same approach as the
        # abiword plugins and argp-standalone recipes).  tool_requires are
        # resolved with the *build* profile, so both -pr:h and -pr:b must be
        # passed to conan create.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: only Linux/OHOS targets are supported by this recipe
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libconfig is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # doc/ builds .info pages with makeinfo, which is not present on the
        # OHOS build image, and the git tag archive ships no pre-built .info.
        tc.configure_args.append("--disable-doc")
        # examples/ registers example1..4 as automake TESTS; they read
        # example.cfg via a relative path and fail under VPATH (out-of-source)
        # builds ("file I/O error").  They are demo programs, not tests, and
        # the real upstream tinytest suite (16 cases) is vendored in
        # test_package/ and executed there against the installed library —
        # same verification split as the merged libconfig 1.7.3 recipe.
        tc.configure_args.append("--disable-examples")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        # The git tag archive ships no `configure`: regenerate one from
        # configure.ac.  Plain `autoreconf -f` (no -i) keeps the patched
        # aux-build/config.guess + config.sub in place - with -i automake
        # would overwrite them with stock versions that cannot identify
        # HarmonyOS (E007).
        self.run("autoreconf -f", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits the HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["config"]
        self.cpp_info.set_property("cmake_file_name", "libconfig")
        self.cpp_info.set_property("cmake_target_name", "libconfig::libconfig")
        self.cpp_info.set_property("pkg_config_name", "libconfig")
