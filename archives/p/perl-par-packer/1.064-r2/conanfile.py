#!/usr/bin/env python3
"""Conan recipe — perl-par-packer 1.064-r2 (Perl XS module).

PAR::Packer: pack Perl programs into standalone executables.
Build system: Perl ExtUtils::MakeMaker (Makefile.PL).
Contains XS code (C/XS compiled to .so) and C executables (myldr/parl).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class PerlParPackerConan(ConanFile):
    name = "perl-par-packer"
    version = "1.064-r2"
    description = "PAR::Packer - pack Perl programs into standalone executables"
    license = "Perl_5"
    homepage = "https://metacpan.org/release/PAR-Packer"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Perl module dependencies (installed separately via cpan)
        pass

    def layout(self):
        # Use simple layout - no cmake/autotools
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        tmpdir = os.environ.get("TMPDIR", "/tmp")

        # OHOS: set OHOS_SYSROOT for patches that use $ENV{OHOS_SYSROOT}
        if self.settings.os == "OHOS":
            if not os.environ.get("OHOS_SYSROOT"):
                hnp_home = os.environ.get("HNP_PUBLIC_HOME", "/data/service/hnp")
                os.environ["OHOS_SYSROOT"] = os.path.join(
                    hnp_home, "ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot")

        # OHOS: create ldd wrapper if ldd is not available
        ldd_path = os.path.join(tmpdir, "ldd")
        if self.settings.os in ("Linux", "OHOS") and not shutil.which("ldd"):
            with open(ldd_path, "w") as f:
                f.write("#!/system/bin/sh\n")
                f.write('readelf -d "$1" 2>/dev/null | grep NEEDED | while read line; do '
                        'lib=$(echo "$line" | sed "s/.*\\[\\(.*\\)\\].*/\\1/"); '
                        'found=""; for dir in /system/lib64 /system/lib /lib64 /lib; do '
                        '[ -f "$dir/$lib" ] && found="$dir/$lib" && break; done; '
                        '[ -n "$found" ] && printf "\\t%s => %s\\n" "$lib" "$found" || '
                        'printf "\\t%s => not found\\n" "$lib"; done\n')
            os.chmod(ldd_path, 0o755)
            os.environ["PATH"] = tmpdir + ":" + os.environ.get("PATH", "")

        # Ensure TMPDIR is in PATH for ldd wrapper
        os.environ["PATH"] = tmpdir + ":" + os.environ.get("PATH", "")

        # Run perl Makefile.PL
        self.run("perl Makefile.PL", env="build")

        # Build with make -j1 (PAR::Packer requires sequential build)
        # Use -k to continue past parl build failure (OHOS HMDFS platform limitation)
        try:
            self.run("make -j1 -k", env="build")
        except Exception as e:
            self.output.warning(f"make failed: {e}")
            if self.settings.os != "OHOS":
                raise
            # On OHOS, parl binary may fail due to HMDFS directory safety check
            # parl/parldyn are regenerated below using PAR_GLOBAL_TEMP workaround

        # OHOS: Generate parl/parldyn using PAR_GLOBAL_TEMP to bypass
        # HMDFS isSafeDir() check in par_mktmpdir()
        # par_init_env() copies PAR_GLOBAL_TEMP to PAR_TEMP, which skips
        # all temp directory creation and safety checks
        if self.settings.os == "OHOS":
            par_temp = os.path.join(tmpdir, "par_global_temp")
            par_temp_dyn = os.path.join(tmpdir, "par_global_temp_dyn")
            os.makedirs(par_temp, exist_ok=True)
            os.makedirs(par_temp_dyn, exist_ok=True)

            myldr = os.path.join(self.build_folder, "myldr")
            blib = os.path.join(self.build_folder, "blib")

            # Generate parl (static) from boot
            # Note: This requires Perl deps (Archive::Zip, PAR, etc.) which may
            # not be available in CI. Failure is non-fatal — parl/parldyn are
            # platform-specific binaries; .pm modules are still packaged.
            try:
                self.run(f'PAR_GLOBAL_TEMP="{par_temp}" '
                         f'perl -Mblib=.. run_with_inc.pl ./boot -q -B -Oparl',
                         cwd=myldr, env="build")
            except Exception as e:
                self.output.warning(f"parl generation failed: {e}")

            # Generate parldyn (dynamic) from par
            try:
                self.run(f'PAR_GLOBAL_TEMP="{par_temp_dyn}" '
                         f'perl -Mblib=.. run_with_inc.pl ./par -q -B -Oparldyn',
                         cwd=myldr, env="build")
            except Exception as e:
                self.output.warning(f"parldyn generation failed: {e}")

            # OHOS: Sign parl/parldyn to fix signature invalidation
            # parl = boot + appended PAR data; appending data invalidates .codesign
            # Solution: embed PAR data as .pardata ELF section, then re-sign
            hnp_home = os.environ.get("HNP_PUBLIC_HOME", "/data/service/hnp")
            sign_tool = os.path.join(hnp_home, "bin/binary-sign-tool")
            objcopy_tool = shutil.which("objcopy") or os.path.join(hnp_home, "bin/objcopy")

            for exe, base in [("parl", "boot"), ("parldyn", "par")]:
                exe_path = os.path.join(myldr, exe)
                base_path = os.path.join(myldr, base)
                if not os.path.exists(exe_path) or not os.path.exists(base_path):
                    continue

                # Step 1: Extract appended PAR data from parl/parldyn
                base_size = os.path.getsize(base_path)
                exe_size = os.path.getsize(exe_path)
                par_data_size = exe_size - base_size
                if par_data_size <= 0:
                    continue

                par_data_file = os.path.join(tmpdir, f"{exe}_pardata.bin")
                with open(exe_path, "rb") as f_in:
                    f_in.seek(base_size)
                    with open(par_data_file, "wb") as f_out:
                        f_out.write(f_in.read())

                # Step 2: Strip .codesign from base binary
                base_nosig = os.path.join(myldr, f"{base}_nosig")
                self.run(f'"{objcopy_tool}" --remove-section=.codesign "{base_path}" "{base_nosig}"',
                         env="build")

                # Step 3: Add PAR data as .pardata ELF section
                with_section = os.path.join(myldr, f"{exe}_with_section")
                self.run(
                    f'"{objcopy_tool}" --add-section .pardata="{par_data_file}" '
                    f'--set-section-flags .pardata=alloc,load,contents,data '
                    f'"{base_nosig}" "{with_section}"',
                    env="build")

                # Step 4: Sign with binary-sign-tool
                signed_out = os.path.join(tmpdir, f"{exe}_signed")
                self.run(
                    f'{sign_tool} sign -keyAlias "{exe}-key" '
                    f'-signAlg SHA256withECDSA -selfSign 1 '
                    f'-inFile "{with_section}" -outFile "{signed_out}"',
                    env="build")

                # Step 5: Replace original with signed version
                if os.path.exists(signed_out):
                    shutil.copy2(signed_out, exe_path)
                    os.chmod(exe_path, 0o755)

            # Copy signed parl/parldyn to blib/script
            blib_script = os.path.join(blib, "script")
            os.makedirs(blib_script, exist_ok=True)
            for exe in ("parl", "parldyn"):
                src = os.path.join(myldr, exe)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(blib_script, exe))
                    os.chmod(os.path.join(blib_script, exe), 0o755)

    def package(self):
        # On OHOS, make install fails because it triggers parl build (HMDFS limitation)
        # Directly copy blib files to package folder instead
        blib = os.path.join(self.build_folder, "blib")

        # Copy lib files (.pm modules)
        blib_lib = os.path.join(blib, "lib")
        if os.path.exists(blib_lib):
            copy(self, "*", blib_lib, os.path.join(self.package_folder, "lib", "perl5"))

        # Copy arch files (.so XS extensions)
        blib_arch = os.path.join(blib, "arch")
        if os.path.exists(blib_arch):
            copy(self, "*", blib_arch, os.path.join(self.package_folder, "lib", "perl5"))

        # Copy scripts (including parl/parldyn)
        blib_script = os.path.join(blib, "script")
        if os.path.exists(blib_script):
            copy(self, "*", blib_script, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # This is a Perl module package, not a C library
        # The .so files are Perl XS extensions
        self.cpp_info.libs = []
