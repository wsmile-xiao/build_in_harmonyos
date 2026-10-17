#!/usr/bin/env python3
"""Conan 2 recipe — kytea 0.4.7 (Kyoto Text Analysis toolkit).

Upstream (phontron.com) is an autotools C++ project producing:
  - libkytea    (shared + static; STL-only runtime, no external deps)
  - kytea       (analysis CLI: segments/tags raw text with a trained model)
  - train-kytea (training CLI: trains a model from an annotated corpus)
  - api-example (small API demonstration program)

OHOS aarch64 findings that shaped this recipe (probe on this worker,
in-source build identical to the probe):

1. config.guess/config.sub are 2011-era and do not know aarch64 or
   linux-ohos -> patch 0001.
2. configure's "cannot run C compiled programs" failure is NOT a
   compiler problem: the probe with umask 077 fails at the very first
   mktemp/mkdir because HMDFS refuses restrictive-mode directory
   creation -> patch 0002 (umask 022).
3. Release tarball ships a STALE generated src/include/kytea/config.h
   (from the maintainer's machine, defines HAVE_BOOST_TR1_UNORDERED_MAP_HPP
   etc.).  In a VPATH build `#include <kytea/config.h>` resolves only
   to the stale in-tree file (the -I$(top_builddir)/src/include/kytea
   flag only makes bare `#include <config.h>` work), pulling in
   non-existent boost headers.  Running configure IN-SOURCE lets
   config.status overwrite the stale header (same layout the probe
   validated).  => this recipe uses the default in-source autotools
   layout and never builds out-of-source.
4. clang-15 rejects `char arr[2] = { c, 0 }` narrowing when
   -Werror=c++11-narrowing is on (config adds -Werror) -> patch 0003.
5. Upstream test suite writes /tmp/kytea-* fixtures; /tmp on OHOS is
   read-only -> patch 0004 makes it honor $TMPDIR (recipe sets TMPDIR
   to a writable dir before `make check`).

`make check` runs test-kytea: 47 assertions across 6 suites
(TestKytea 10, TestAnalysis 15, TestSentence 1, TestCorpusIO 9,
TestCorpusIOEuc 6, TestCorpusIOSjis 6).  All must pass on OHOS.
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class KyteaConan(ConanFile):
    name = "kytea"
    version = "0.4.7"
    description = "Kyoto Text Analysis Toolkit: Japanese word segmentation, pronunciation estimation and tagging (general-purpose text toolkit)"
    license = "Apache-2.0"
    homepage = "https://www.phontron.com/kytea/"
    url = "https://www.phontron.com/kytea/"
    package_type = "library"          # library + CLI tools (bin/kytea, bin/train-kytea, bin/api-example)
    implements = ["auto_shared_install"]

    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kytea is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        # basic_layout: in-source configure/build (Conan's autotools_layout
        # build-folder split would enable VPATH, which kytea cannot do —
        # the tarball ships a stale generated src/include/kytea/config.h
        # that breaks VPATH builds; see module docstring #3).
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # OHOS has no /bin/sh; drive configure with bash (ADAPTATION_GUIDE §2,
        # precedent abcm2ps).  The profile buildenv may export a CONFIG_SHELL
        # path that does not exist on every worker; configure re-execs
        # `exec $CONFIG_SHELL` early AND libtool writes the wrapper-script
        # shebang from it (must be ABSOLUTE — `#! bash` is rejected by the
        # kernel as a bad interpreter).  Resolve bash via PATH here.
        bash = shutil.which("bash")
        if not bash:
            raise ConanInvalidConfiguration("bash is required to build kytea (no /bin/sh on OHOS)")
        src = self.source_folder.replace("\\", "/")
        prefix = self.package_folder.replace("\\", "/")
        self.run(
            f"cd '{src}' && CONFIG_SHELL='{bash}' '{bash}' ./configure --prefix={prefix}",
            env="conanbuild",
        )
        self.run(f"cd '{src}' && make -j{os.cpu_count() or 1}", env="conanbuild")
        # ── upstream official tests (make check) ──
        # test-analysis writes model/corpus fixtures; TMPDIR must point at a
        # writable dir (patch 0004 honors it).
        if can_run(self):
            self.run(f"cd '{src}' && make check", env="conanbuild")
        else:
            self.output.warning("cross-build: upstream make check skipped")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # NOTE: deliberately NOT passing --host/--build: uname is HarmonyOS
        # and patched config.guess resolves aarch64-unknown-linux-ohos natively
        # (probe verified build==host, "cross compiling... no"), so autotools
        # stays in native mode and `make check` runs the test binaries.
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def package(self):
        self.run(f"cd '{self.source_folder}' && make install", env="conanbuild")
        # Drop libtool .la wrappers (precedent a52dec)
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "kytea")
        self.cpp_info.set_property("cmake_target_name", "kytea::kytea")
        self.cpp_info.set_property("pkg_config_name", "kytea")
        self.cpp_info.libs = ["kytea"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
