#!/usr/bin/env python3
"""Conan recipe for cgvg 1.6.3 — Code Grep / Vi Grepped CLI pair (pure Perl).

cgvg is a pure-Perl developer toolkit: two scripts (`cg` code grep, `vg`
vi-grepped editor jump) plus a shared cgvg-common.pl. The upstream tarball is
an autotools *shell* used only to rewrite the `#!@PERL@` shebang, substitute
@VERSION@/@prefix@/@datadir@ and install scripts + data + man pages. There
are no C/C++ sources and no libraries (no .c/.h/.cpp files at all).

Source provenance (R39): the upstream site uzix.org is defunct; the pristine
official release is taken from the Debian pool orig tarball
(cgvg_1.6.3.orig.tar.gz — bit-identical upstream 1.6.3 source, no Debian
modifications; sha256 pinned in conandata.yml).

OHOS adaptation (script-package paradigm, cf. check-jsonschema/alot):
- Direct file install instead of running the autotools configure step:
  configure would bake the build machine's absolute perl path and the
  configure-time --prefix datadir into the scripts — not relocatable for a
  Conan package. The recipe performs exactly the same @PERL@/@VERSION@/
  @prefix@/@datadir@ substitutions itself.
- The shebang is rewritten to `#!/usr/bin/env perl` so the interpreter is
  resolved from PATH at run time (HarmonyOS PC ships perl.org 5.42.0 at
  /data/service/hnp/bin/perl).
- Upstream scripts locate cgvg-common.pl through
  `use lib dirname($0), "<datadir>/cgvg"`. The first (@INC) entry is the
  script's own directory; we drop the configure-time datadir fallback and
  install cgvg-common.pl + cgvgrc-example next to the scripts, keeping the
  package fully relocatable.
- Runtime dependency: a perl 5 interpreter on PATH (system-provided on
  HarmonyOS PC; no OHOS perl Conan package exists yet).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class CgvgConan(ConanFile):
    name = "cgvg"
    version = "1.6.3"
    description = "cg/vg code grep and vi grepped tools: recursively grep source code and open an editor at each match"
    license = "GPL-2.0-or-later"
    homepage = "https://waterlan.home.xs4all.nl/cgvg/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _transform_script(self, src_name, dst_name):
        """Rewrite cg.in/vg.in the way the upstream autotools build does.

        configure would substitute #!@PERL@ (absolute perl path), @VERSION@,
        $prefix and the configure-time @datadir@/cgvg library fallback.
        We bake in a relocatable equivalent:
          - shebang -> #!/usr/bin/env perl  (perl resolved from PATH)
          - cgvg-common.pl is installed next to the scripts (the first
            @INC entry the upstream scripts already search, dirname($0));
            the build-machine-dependent datadir fallback is removed.
        """
        src = os.path.join(self.source_folder, src_name)
        dst = os.path.join(self.build_folder, dst_name)
        with open(src, "r", encoding="utf-8") as f:
            text = f.read()
        text = text.replace("#!@PERL@", "#!/usr/bin/env perl")
        text = text.replace("@VERSION@", self.version)
        text = text.replace('$prefix = "@prefix@"', '$prefix = ""')
        text = text.replace('use lib dirname($0), "@datadir@/cgvg";',
                            "use lib dirname($0);")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(dst, 0o755)

    def build(self):
        apply_conandata_patches(self)
        self._transform_script("cg.in", "cg")
        self._transform_script("vg.in", "vg")
        # Upstream ships no test suite (Makefile.am declares no TESTS/check_
        # targets — `make check` has nothing to run). Sanity-check the
        # generated scripts with perl -c when an interpreter is available.
        perl = shutil.which("perl")
        if perl:
            for script in ("cg", "vg"):
                self.run('"%s" -c "%s"' % (perl, os.path.join(self.build_folder, script)),
                         env="conanbuild")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for script in ("cg", "vg"):
            copy(self, script, src=self.build_folder, dst=bin_dir, keep_path=False)
        for data in ("cgvg-common.pl", "cgvgrc-example"):
            copy(self, data, src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "cg.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "vg.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
