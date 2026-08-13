#!/usr/bin/env python3
"""Conan recipe for perl-params-validate — Perl XS module (ExtUtils::MakeMaker + manual XS).

Build system: perl Makefile.PL + make (for .pm files) + manual xsubpp/cc (for XS)
XS module: lib/Params/Validate/XS.xs → XS.c → XS.so
Has pure Perl fallback via Module::Implementation (auto-fallback when XS unavailable).

Source ships with Build.PL (Module::Build), but Module::Build is not available
on the CI worker Perl installation. We generate a Makefile.PL using
ExtUtils::MakeMaker for .pm file installation, and manually compile the XS
file (ExtUtils::MakeMaker doesn't auto-detect .xs files for sub-modules).

On OHOS:
  - musl C library headers at ~/usr/local/include (sys/types.h etc.)
  - musl libc at ~/usr/local/lib
  - E137: Perl 5.42.0 lddlflags has -fstack-protector-strong, ld.lld rejects it
  - Fix: use clang -shared with -nostartfiles -nodefaultlibs -lc for XS linking
  - XS .so may fail to load at runtime due to SELinux/HMDFS (PP fallback works)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlParamsValidateConan(ConanFile):
    name = "perl-params-validate"
    version = "1.31"
    description = "Validate method/function parameters (Perl XS module)"
    license = "Artistic-2.0"
    homepage = "https://metacpan.org/release/Params-Validate"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_perl(self):
        """Find perl binary path.

        Probes known OHOS locations before falling back to PATH.
        Some CI workers don't have perl in the default PATH.
        """
        candidates = [
            "/data/service/hnp/bin/perl",
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin", "perl"),
            "/usr/bin/perl",
            "/usr/local/bin/perl",
        ]
        for p in candidates:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return "perl"

    def _perl_config(self, key):
        """Get a value from Perl's Config.

        Uses self.run() (not subprocess.run) because conan's self.run()
        sources the conanbuild.sh environment file, which sets up PATH
        to include the perl binary directory. subprocess.run() would
        not find perl on CI workers where perl is not in the default PATH.
        """
        perl = self._find_perl()
        out = os.path.join(self.build_folder, f".perl_cfg_{key}")
        self.run(
            f'"{perl}" -MConfig -e \'print $Config{{{key}}}\' > "{out}"',
            cwd=self.source_folder,
        )
        with open(out, "r") as f:
            val = f.read().strip()
        os.remove(out)
        return val

    def _find_musl_paths(self):
        """Detect musl C library header and library paths.

        R33: Do not rely on undefined shell env vars. Instead, probe
        known OHOS locations and verify the path exists before use.
        """
        candidates_inc = [
            os.path.join(os.path.expanduser("~"), "usr", "local", "include"),
            "/data/service/hnp/usr/local/include",
            "/usr/local/include",
        ]
        candidates_lib = [
            os.path.join(os.path.expanduser("~"), "usr", "local", "lib"),
            "/data/service/hnp/usr/local/lib",
            "/usr/local/lib",
        ]

        sys_inc = next((p for p in candidates_inc if os.path.isdir(p)), "")
        sys_lib = next((p for p in candidates_lib if os.path.isdir(p)), "")
        return sys_inc, sys_lib

    def _resolve_cc(self):
        """Resolve compiler name to full path.

        R33: Do not rely on undefined shell env vars. Perl's Config
        returns just "clang" (the name), but CI workers may not have
        clang in PATH (same issue as perl). Resolve to full path.
        """
        cc_name = self._perl_config("cc")
        full_path = shutil.which(cc_name)
        if full_path:
            return full_path
        candidates = [
            "/data/service/hnp/bin/clang",
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin", "clang"),
            "/usr/bin/clang",
            "/usr/local/bin/clang",
        ]
        for p in candidates:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return cc_name

    def build(self):
        # Apply conandata patches (if any)
        apply_conandata_patches(self)

        # --- Step 1: Create Makefile.PL for .pm file installation ---
        # Source ships with Build.PL (Module::Build), which is not available
        # on the CI worker. Create a Makefile.PL (ExtUtils::MakeMaker) fallback.
        # Note: ExtUtils::MakeMaker won't auto-compile XS.xs for sub-modules,
        # so we handle XS compilation manually (Step 3).
        makefile_pl = os.path.join(self.source_folder, "Makefile.PL")
        makefile_pl_content = """\
use strict;
use warnings;
use ExtUtils::MakeMaker;

WriteMakefile(
    NAME          => 'Params::Validate',
    VERSION_FROM  => 'lib/Params/Validate.pm',
    ABSTRACT_FROM => 'lib/Params/Validate.pm',
    AUTHOR        => 'Dave Rolsky <autarch@urth.org>',
    LICENSE       => 'artistic_2',
    INC           => '-Ic',
    PREREQ_PM     => {
        'Module::Implementation' => 0,
        'Scalar::Util'           => '1.10',
        'XSLoader'               => 0,
    },
    NO_MYMETA => 1,
);
"""
        with open(makefile_pl, "w") as f:
            f.write(makefile_pl_content)

        # --- Step 2: Build .pm files via Makefile.PL + make ---
        perl_bin = self._find_perl()
        self.run(f'"{perl_bin}" Makefile.PL INSTALLDIRS=site', cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

        # --- Step 3: Manually compile XS module ---
        # ExtUtils::MakeMaker doesn't auto-detect lib/Params/Validate/XS.xs
        # because it belongs to the Params::Validate::XS sub-module, not the
        # NAME (Params::Validate). We compile it manually following the
        # perl-net-libresolv pattern.
        sys_inc, sys_lib = self._find_musl_paths()
        inc_flags = f' -I"{sys_inc}"' if sys_inc else ""
        lib_flags = f' -L"{sys_lib}"' if sys_lib else ""

        # Get Perl build tool paths via self.run() (R33: no subprocess.run
        # for perl — CI workers may not have perl in default PATH)
        scriptdir = self._perl_config("scriptdir")
        archlibexp = self._perl_config("archlibexp")
        privlibexp = self._perl_config("privlibexp")
        xsubpp = os.path.join(scriptdir, "xsubpp")
        typemap = os.path.join(privlibexp, "ExtUtils", "typemap")
        perl_inc = os.path.join(archlibexp, "CORE")
        cc = self._resolve_cc()
        ccflags = self._perl_config("ccflags")
        optimize = self._perl_config("optimize")
        cccdlflags = self._perl_config("cccdlflags")

        # 3a: xsubpp — convert .xs to .c
        xs_file = os.path.join(self.source_folder, "lib", "Params", "Validate", "XS.xs")
        c_file = os.path.join(self.source_folder, "lib", "Params", "Validate", "XS.c")
        self.run(
            f'"{perl_bin}" "{xsubpp}" -typemap "{typemap}" "{xs_file}" > "{c_file}"',
            cwd=self.source_folder
        )

        # 3b: Compile .c to .o
        # Perl CORE headers define Off_t as off64_t, but musl/OHOS only
        # provides off_t (already 64-bit on aarch64). Map off64_t→off_t.
        obj_file = os.path.join(self.source_folder, "lib", "Params", "Validate", "XS.o")
        self.run(
            f'{cc} -c -Doff64_t=off_t -I"{perl_inc}" -I"c"{inc_flags} '
            f'{ccflags} {optimize} {cccdlflags} -o "{obj_file}" "{c_file}"',
            cwd=self.source_folder
        )

        # 3c: Link .o to .so
        # E137: Use clang -shared with -nostartfiles -nodefaultlibs -lc to
        # provide minimal CRT (ld.lld rejects -fstack-protector-strong without CRT)
        blib_dir = os.path.join(
            self.source_folder, "blib", "arch", "auto", "Params", "Validate", "XS"
        )
        os.makedirs(blib_dir, exist_ok=True)
        so_file = os.path.join(blib_dir, "XS.so")
        self.run(
            f'{cc} -shared -nostartfiles -nodefaultlibs -lc '
            f'{lib_flags} -L/system/lib64 -o "{so_file}" "{obj_file}"',
            cwd=self.source_folder
        )

    def package(self):
        # Install .pm files with DESTDIR to package folder
        dest = os.path.join(self.package_folder, "")
        self.run(f'make install DESTDIR="{dest}"', cwd=self.source_folder)

        # Dynamically resolve Perl's sitearch path (avoid hardcoding version/arch).
        # sitearchexp is like /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux
        # make install DESTDIR=dest installs to dest + sitearchexp
        site_arch = os.path.join(dest, self._perl_config("sitearchexp").lstrip("/"))
        so_src = os.path.join(
            self.source_folder, "blib", "arch", "auto", "Params", "Validate", "XS", "XS.so"
        )
        so_dst_dir = os.path.join(site_arch, "auto", "Params", "Validate", "XS")
        os.makedirs(so_dst_dir, exist_ok=True)
        if os.path.isfile(so_src):
            shutil.copy2(so_src, os.path.join(so_dst_dir, "XS.so"))

        # Also copy .so to standard lib/ for package integrity checks (L5)
        lib_dst = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dst, exist_ok=True)
        if os.path.isfile(so_src):
            shutil.copy2(so_src, os.path.join(lib_dst, "XS.so"))

    def package_info(self):
        # Perl XS module — .so is loaded dynamically by Perl, not linked by
        # other Conan packages. Declare empty libs (consistent with other
        # Perl XS recipes like perl-net-libresolv).
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]
