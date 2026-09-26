#!/usr/bin/env python3
"""Conan recipe for checkit-tiff 1.7.3 on OpenHarmony.

checkit_tiff is a C conformance checker for baseline TIFFs. Upstream is a
plain CMake project (src/CMakeLists.txt) that requires PCRE2. We wire PCRE2
through the upstream's "explicit variables" branch (PCRE2_INCLUDE_DIR /
PCRE2_LIBRARY / PCRE2_POSIX_LIBRARY) so no pkg-config binary is needed at
configure time.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
)
from conan.tools.scm import Git

# Upstream's test harness (t/Testcall.pm) hardcodes the binaries as
# "../build/checkit_tiff" relative to the t/ directory. Upstream's own
# out-of-source layout puts them in <repo>/build, so we stage them there.
_UPSTREAM_TEST_BINARIES = ("checkit_tiff", "checkit_check_config", "checkit_tiff_risk")

# Upstream's t/*.t harness needs these two CPAN modules, which are NOT in the
# perl core. On a stock perl (verified on the OHOS CI worker: perl 5.42, and on
# Ubuntu 5.34) both are absent, which is what silently kept the upstream suite
# from running. We drop in minimal pure-perl stand-ins via PERL5LIB instead of
# editing any upstream test, so every assertion stays upstream-authentic:
#   File::Slurp  -> only read_file/write_file are used (raw bytes, no encoding)
#   Data::Printer-> only p(@err) is used, and only to dump stderr *after* an
#                   assertion has already failed (diagnostics, never verdict)
_PERL_SHIM_FILE_SLURP = """package File::Slurp;
use strict;
use warnings;
use Exporter 'import';
our @EXPORT_OK = qw(read_file write_file);
our @EXPORT = @EXPORT_OK;
sub read_file {
    my ($f) = @_;
    open(my $fh, '<', $f) or die "read_file($f): $!\\n";
    binmode $fh;
    local $/;
    my $c = <$fh>;
    close $fh;
    return defined $c ? $c : '';
}
sub write_file {
    my ($f, $c) = @_;
    open(my $fh, '>', $f) or die "write_file($f): $!\\n";
    binmode $fh;
    print $fh (defined $c ? $c : '') or die "write_file($f): $!\\n";
    close $fh or die "write_file($f): $!\\n";
    return 1;
}
1;
"""

_PERL_SHIM_DATA_PRINTER = """package Data::Printer;
use strict;
use warnings;
use Exporter 'import';
our @EXPORT_OK = qw(p);
our @EXPORT = @EXPORT_OK;
sub p {
    my @a = @_;
    print STDERR join('', map { defined $_ ? $_ : '(undef)' } @a), "\\n";
    return 1;
}
1;
"""


class CheckitTiffConan(ConanFile):
    name = "checkit-tiff"
    version = "1.7.3"
    description = (
        "Incredibly fast conformance checker for baseline TIFFs "
        "(policy-oriented rule sets)."
    )
    # Upstream LICENSE states the project "uses pieces from libtiff, therefore
    # licensed under same conditions" and reprints the libtiff permissive
    # notice. Follow the repo's libtiff recipe SPDX identifier.
    license = "libtiff"
    homepage = "https://git.fsfe.org/art1pirat/checkit_tiff"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("pcre2/10.47")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("checkit-tiff only supports Linux/OHOS")

    def source(self):
        # Do not clone directly into source_folder: conan copies export_sources
        # (patches/ etc.) there before source() runs, and `git clone .` would
        # wipe them (and fail on a non-empty dir). Cloning into a temp subdir
        # and merging back keeps those files intact.
        source = self.conan_data["sources"]
        clone_folder = os.path.join(self.source_folder, "_clone")
        git = Git(self)
        git.clone(url=source["url"], target="_clone")
        git.run(f'-C _clone checkout {source["commit"]}')
        for name in os.listdir(clone_folder):
            src = os.path.join(clone_folder, name)
            dst = os.path.join(self.source_folder, name)
            if os.path.isdir(src) and not os.path.islink(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        shutil.rmtree(clone_folder, ignore_errors=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Windows conan worker without sh: force Ninja generator (ninja is on
        # PATH via WinLibs). MinGW Makefiles would demand sh.exe.
        tc.generator = "Ninja"
        pcre2 = self.dependencies["pcre2"]
        root = pcre2.package_folder.replace("\\", "/")
        tc.variables["PCRE2_INCLUDE_DIR"] = os.path.join(root, "include").replace("\\", "/")
        tc.variables["PCRE2_LIBRARY"] = os.path.join(root, "lib", "libpcre2-8.a").replace("\\", "/")
        tc.variables["PCRE2_POSIX_LIBRARY"] = os.path.join(root, "lib", "libpcre2-posix.a").replace("\\", "/")
        # Do not let pkg_check_modules fall back to a system pkg-config that
        # may reinterpret freshly-built objects for the build host.
        tc.variables["PKG_CONFIG_EXECUTABLE"] = "NOTFOUND"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream keeps CMakeLists.txt under src/ and references ../example_configs
        # (repo root) from install rules, so the whole repo is cloned into
        # source_folder and the CMake source dir is the src/ subdir.
        cmake.configure(build_script_folder="src")
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Really execute the 5 upstream cases, never silently skip them.

        src/CMakeLists.txt already registers all five with ctest
        (01_test_stack, 01_grammar, 02_config, 03_validfiles,
        03_invalidfiles) behind find_package(Perl). We just have to invoke
        ctest and let a non-zero exit fail the build.
        """
        if not can_run(self):
            # Only reachable when cross-compiling to a foreign arch with no
            # emulator. Say so loudly -- a quiet skip is what got this PR
            # failed review before.
            self.output.warning(
                "checkit-tiff: target binaries cannot execute on this build host "
                f"(target {self.settings.os}/{self.settings.arch}); the 5 upstream "
                "ctest cases were NOT executed here."
            )
            return

        # Testcall.pm resolves the binaries as ../build/<exe> from t/, i.e.
        # <source>/build, while conan builds into <b>/build/Release. Stage the
        # freshly built executables where upstream's own harness looks for them.
        staged = os.path.join(self.source_folder, "build")
        os.makedirs(staged, exist_ok=True)
        for exe in _UPSTREAM_TEST_BINARIES:
            built = os.path.join(self.build_folder, exe)
            if os.path.isfile(built):
                shutil.copy2(built, os.path.join(staged, exe))
            else:
                self.output.warning(f"checkit-tiff: {exe} not found in {self.build_folder}")

        shim = self._write_perl_shims()
        self.output.info(f"checkit-tiff: PERL5LIB shims for File::Slurp/Data::Printer -> {shim}")
        self.output.info("checkit-tiff: running the 5 upstream ctest cases")

        # ConanFile.run() has no run_environment kwarg, so activate the build env
        # by name and inject PERL5LIB through os.environ, which the runner
        # inherits. Self.run raises on a non-zero exit, so a genuine upstream
        # regression fails conan create instead of being waved through.
        previous = os.environ.get("PERL5LIB")
        os.environ["PERL5LIB"] = shim
        try:
            # ctest reads CTestTestfile.c from the cwd, so run it in build_folder.
            # --output-on-failure keeps the real upstream assertions in the log.
            self.run("ctest --output-on-failure", cwd=self.build_folder,
                     env="conanbuild")
        finally:
            if previous is None:
                os.environ.pop("PERL5LIB", None)
            else:
                os.environ["PERL5LIB"] = previous

    def _write_perl_shims(self):
        shim = os.path.join(self.build_folder, "perl-shim")
        os.makedirs(os.path.join(shim, "File"), exist_ok=True)
        os.makedirs(os.path.join(shim, "Data"), exist_ok=True)
        for rel, body in (
            (os.path.join("File", "Slurp.pm"), _PERL_SHIM_FILE_SLURP),
            (os.path.join("Data", "Printer.pm"), _PERL_SHIM_DATA_PRINTER),
        ):
            with open(os.path.join(shim, rel), "w", encoding="utf-8") as fh:
                fh.write(body)
        return shim

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream CMakeLists.txt only installs checkit_tiff; also ship
        # checkit_check_config and checkit_tiff_risk for complete toolset.
        # NOTE: conan.tools.files.copy() takes a literal path for dst -- unlike
        # Conan 1's self.copy() it does NOT resolve "bin" against the package
        # folder, so pass an absolute dst or the binaries land in ./bin.
        bindir = os.path.join(self.package_folder, "bin")
        for extra in ("checkit_check_config", "checkit_tiff_risk"):
            src = os.path.join(self.build_folder, extra)
            if os.path.isfile(src):
                copied = copy(self, extra, src=self.build_folder, dst=bindir)
                self.output.info(f"checkit-tiff: packaged {extra} -> {bindir} ({len(copied)} file)")
            else:
                self.output.warning(f"checkit-tiff: {extra} not found in {self.build_folder}")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []