#!/usr/bin/env python3
"""Conan recipe for VCFtools 0.1.17 (Autotools) on OpenHarmony.

The release builds one C++ executable and installs a suite of Perl tools. The
C++ executable links zlib; the Perl tools use bgzip/tabix from HTSlib for
indexed VCF operations.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class VcftoolsConan(ConanFile):
    name = "vcftools"
    version = "0.1.17"
    description = "C++ and Perl command-line tools for working with VCF files"
    license = "LGPL-3.0-only"
    homepage = "https://vcftools.github.io/"
    url = "https://github.com/vcftools/vcftools"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires(
            "htslib/1.24-r0",
            headers=False,
            libs=False,
            run=True,
        )

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # The release archive omits src/perl/test.t even though it is present
        # in the matching upstream tag. Fetch that exact test with a checksum.
        test_data = self.conan_data["upstream_tests"]["perl_test"]
        test_path = os.path.join(self.source_folder, "src", "perl", "test.t")
        download(self, filename=test_path, **test_data)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()

        tc = AutotoolsToolchain(self)
        triplet = "aarch64-unknown-linux-ohos"
        tc.configure_args.extend([
            # Do not set --build to the target triplet: Autoconf would then
            # treat this as a native build and try to run target binaries.
            f"--host={triplet}",
            "--prefix=/",
            "--disable-silent-rules",
            "--with-pmdir=lib/perl5/site_perl",
        ])
        tc.generate()

        # OHOS /tmp may be read-only. Autoconf and the Perl tests both honor
        # TMPDIR, so provide a writable location through Conan's build env.
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define_path("TMPDIR", tmpdir)
        # vcf-stats and vcf-merge compare text fixtures whose ordering is
        # derived from Perl hashes. Keep that ordering reproducible on OHOS.
        env.define("PERL_HASH_SEED", "0")
        env.define("PERL_PERTURB_KEYS", "0")
        env.vars(self).save_script("vcftools_tmpdir")

    @staticmethod
    def _patch_configure_tempdir(configure):
        """Keep config.status temporary scripts off the HMDFS build directory."""
        with open(configure, encoding="utf-8") as file:
            contents = file.read()
        patched = contents.replace(
            '(umask 077 && mktemp -d "./confXXXXXX")',
            '(umask 002 && mktemp -d "${TMPDIR:-.}/confXXXXXX")',
        ).replace(
            'tmp=./conf$$-$RANDOM',
            'tmp=${TMPDIR:-.}/conf$$-$RANDOM',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            '(umask 002 && mkdir "$tmp")',
        )
        if patched == contents:
            raise ConanException(
                f"Could not patch {configure} temporary directory handling"
            )
        with open(configure, "w", encoding="utf-8", newline="") as file:
            file.write(patched)
        os.utime(configure, None)

    def build(self):
        apply_conandata_patches(self)

        if str(self.settings.os) == "OHOS":
            tmpdir = os.path.expanduser("~/tmp/vcftools")
            os.makedirs(tmpdir, exist_ok=True)
            # Make configure and the generated config.status use an executable
            # temporary directory instead of the HMDFS-backed build folder.
            os.environ["TMPDIR"] = tmpdir
            configure = os.path.join(self.build_folder, "configure")
            os.chmod(configure, 0o755)
            self._patch_configure_tempdir(configure)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        test_path = os.path.join(self.source_folder, "src", "perl", "test.t")

        # Test::Most is not part of Perl core, while every assertion used by
        # upstream test.t is provided by core Test::More. Keep all 75 tests.
        replace_in_file(
            self,
            test_path,
            "use Test::Most tests => 75;",
            "use Test::More tests => 75;",
        )

        # Upstream test.t lives in src/perl but points one level up for the
        # top-level examples directory. Correct the omitted directory level.
        replace_in_file(
            self,
            test_path,
            "$path/../examples",
            "$path/../../examples",
        )

        # The release archive keeps examples/ at the source root while the
        # Perl tools remain in src/perl/.  Adjust only test command paths.
        replace_in_file(
            self,
            test_path,
            "../perl/",
            "../src/perl/",
        )

        # The release archive stores examples/ at the source root.  The test
        # helpers already receive that absolute directory, so avoid a second
        # relative traversal before opening their expected-output fixtures.
        replace_in_file(
            self,
            test_path,
            'chdir("$path/../../examples");',
            "chdir($path);",
        )

        # These three helpers receive $path rather than an examples/ path in
        # the upstream script.  Keep every helper on the same absolute
        # examples/ directory after the release-layout rewrite above.
        replace_in_file(
            self, test_path, "test_merge($path,", 'test_merge("$path/../../examples",'
        )
        replace_in_file(
            self, test_path, "test_compare($path,", 'test_compare("$path/../../examples",'
        )
        replace_in_file(
            self, test_path, "test_isec($path,", 'test_isec("$path/../../examples",'
        )

        # Data::Dumper's textual hash order varies between Perl releases.
        # Compare the generated statistics as Perl data structures instead.
        replace_in_file(
            self,
            test_path,
            '    is_deeply(\\@out,\\@exp,"Testing vcf-stats .. $cmd");',
            '''    is_deeply(
        eval("no strict; " . join('', @out)),
        eval("no strict; " . join('', @exp)),
        "Testing vcf-stats .. $cmd"
    );''',
        )

        # Perl hash ordering must not affect VCF semantic comparisons.  INFO
        # attributes and FILTER header declarations are unordered VCF fields.
        replace_in_file(
            self,
            test_path,
            "my $path = $FindBin::RealBin;",
            '''my $path = $FindBin::RealBin;

sub normalize_vcf_info
{
    my ($line) = @_;
    return $line if $line =~ /^#/;
    my @fields = split(/\\t/,$line,-1);
    return $line if @fields < 8;
    $fields[7] = join(';',sort split(/;/,$fields[7]));
    return join("\\t",@fields);
}

sub normalize_annotate_output
{
    my (@lines) = @_;
    my @filters = sort grep { /^##FILTER=/ } @lines;
    my @out;
    my $inserted_filters = 0;
    for my $line (@lines)
    {
        if ( $line =~ /^##FILTER=/ )
        {
            if ( !$inserted_filters ) { push @out,join('',@filters); $inserted_filters=1; }
            next;
        }
        push @out,normalize_vcf_info($line);
    }
    return @out;
}''',
        )
        replace_in_file(
            self,
            test_path,
            '    is_deeply(\\@out,\\@exp,"Testing vcf-annotate .. $cmd");',
            '    is_deeply([normalize_annotate_output(@out)],[normalize_annotate_output(@exp)],"Testing vcf-annotate .. $cmd");',
        )
        replace_in_file(
            self,
            test_path,
            'is_deeply(\\@out,\\@exp,"Testing vcf-contrast .. $cmd");',
            'is_deeply([map { normalize_vcf_info($_) } @out],[map { normalize_vcf_info($_) } @exp],"Testing vcf-contrast .. $cmd");',
        )
        replace_in_file(
            self,
            test_path,
            " | vcf-query -f '",
            " | perl -I../src/perl/ -MVcf ../src/perl/vcf-query -f '",
        )

        self.run(
            "perl test.t",
            cwd=os.path.dirname(test_path),
            env=["conanrun", "vcftools_tmpdir"],
        )

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

        perl_lib = os.path.join(self.package_folder, "lib", "perl5", "site_perl")
        self.runenv_info.prepend_path("PERL5LIB", perl_lib)
        self.buildenv_info.prepend_path("PERL5LIB", perl_lib)
