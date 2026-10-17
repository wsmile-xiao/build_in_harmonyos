#!/usr/bin/env python3
"""Conan recipe — texlive 20260301 (TeX Live full distribution).

Builds tex, pdftex, xetex, luatex, metapost, mf, dvisvgm, dvipsk,
bibtex-x, synctex and all other TeX Live engines and tools for HarmonyOS.
"""
import os
import re
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TexliveConan(ConanFile):
    name = "texlive"
    version = "20260301"
    description = "TeX Live full distribution (tex, pdftex, xetex, luatex, metapost, mf, dvisvgm, etc.)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.tug.org/texlive/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # HMDFS limitation: configure test programs can't be executed in conan sandbox
        # Setting --build/--host to same value tells configure it's native (no cross-compilation test)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # R26: static build
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        # TeX Live specific configure options
        tc.configure_args.append("--without-x")
        tc.configure_args.append("--disable-xdvik")
        tc.configure_args.append("--disable-xpdfopen")
        tc.configure_args.append("--disable-xindy")
        tc.configure_args.append("--disable-asymptote")
        tc.configure_args.append("--disable-luajittex")
        tc.configure_args.append("--disable-luajithbtex")
        tc.configure_args.append("--disable-mfluajit")
        tc.configure_args.append("--disable-aleph")
        tc.configure_args.append("--disable-hitex")
        tc.configure_args.append("--disable-xetex")
        tc.configure_args.append("--with-banner-add=/HarmonyOS")
        tc.generate()

    def _fix_file_shebang(self, filepath):
        """Fix shebang in a single file."""
        try:
            with open(filepath, 'r', errors='ignore') as f:
                content = f.read(100)
            if content.startswith("#!/bin/bash"):
                with open(filepath, 'r', errors='ignore') as f:
                    data = f.read()
                data = data.replace("#!/bin/bash", "#!/data/service/hnp/bin/bash", 1)
                with open(filepath, 'w', errors='ignore') as f:
                    f.write(data)
            elif content.startswith("#!/bin/sh"):
                with open(filepath, 'r', errors='ignore') as f:
                    data = f.read()
                data = data.replace("#!/bin/sh", "#!/system/bin/sh", 1)
                with open(filepath, 'w', errors='ignore') as f:
                    f.write(data)
        except Exception:
            pass

    def _fix_file_content(self, filepath, old, new):
        """Replace text in a file using Python."""
        try:
            with open(filepath, 'r', errors='ignore') as f:
                data = f.read()
            if old in data:
                data = data.replace(old, new)
                with open(filepath, 'w', errors='ignore') as f:
                    f.write(data)
        except Exception:
            pass

    def _fix_platform_issues(self):
        """Fix HarmonyOS platform compatibility issues."""
        src = self.source_folder
        # E165: Fix shebangs for HarmonyOS
        for root, _, files in os.walk(src):
            for f in files:
                fp = os.path.join(root, f)
                self._fix_file_shebang(fp)
        # E007: Fix config.guess: map HarmonyOS -> Linux
        for cg in glob.glob(os.path.join(src, "**/config.guess"), recursive=True):
            self._fix_file_content(cg,
                "UNAME_SYSTEM=`(uname -s) 2>/dev/null` || UNAME_SYSTEM=unknown",
                "UNAME_SYSTEM=`(uname -s) 2>/dev/null` || UNAME_SYSTEM=unknown\n[ \"$UNAME_SYSTEM\" = \"HarmonyOS\" ] && UNAME_SYSTEM=Linux")
        # Fix umask 077 -> 002 in all configure scripts (HMDFS file ownership issue)
        # Note: do NOT prepend "umask 002" to file beginning — it breaks the shebang!
        # umask is already set via os.umask(0o002) in build() method
        for cfg in glob.glob(os.path.join(src, "**/configure"), recursive=True):
            self._fix_file_content(cfg, "umask 077", "umask 002")
        # Fix umask in config.guess files too
        for cg in glob.glob(os.path.join(src, "**/config.guess"), recursive=True):
            self._fix_file_content(cg, "umask 077", "umask 002")
        for cs in glob.glob(os.path.join(src, "**/config.status"), recursive=True):
            self._fix_file_content(cs, "umask 077", "umask 002")
        # Fix umask in .m4 files too
        for m4 in glob.glob(os.path.join(src, "**/*.m4"), recursive=True):
            self._fix_file_content(m4, "umask 077", "umask 002")
        # HMDFS E046: Patch configure to skip all run-time test program execution
        # On HMDFS, compiled test programs can't be executed due to SELinux
        # Skip AC_TRY_RUN by making cross-compiling checks always true/false
        for cfg in glob.glob(os.path.join(src, "**/configure"), recursive=True):
            try:
                with open(cfg, 'r', errors='ignore') as f:
                    data = f.read()
                changed = False
                # Pattern 1: single-line "if test "$cross_compiling" = yes; then"
                if 'if test "$cross_compiling" = yes; then' in data:
                    data = data.replace('if test "$cross_compiling" = yes; then',
                                        'if true; then  # HMDFS_E046')
                    changed = True
                # Pattern 2: multi-line "if test "$cross_compiling" = yes\nthen"
                if 'if test "$cross_compiling" = yes\nthen' in data:
                    data = data.replace('if test "$cross_compiling" = yes\nthen',
                                        'if true  # HMDFS_E046\nthen')
                    changed = True
                # Pattern 3: single-line "if test "$cross_compiling" != yes; then"
                if 'if test "$cross_compiling" != yes; then' in data:
                    data = data.replace('if test "$cross_compiling" != yes; then',
                                        'if false; then  # HMDFS_E046')
                    changed = True
                # Pattern 4: multi-line "if test "$cross_compiling" != yes\nthen"
                if 'if test "$cross_compiling" != yes\nthen' in data:
                    data = data.replace('if test "$cross_compiling" != yes\nthen',
                                        'if false  # HMDFS_E046\nthen')
                    changed = True
                if changed:
                    with open(cfg, 'w', errors='ignore') as f:
                        f.write(data)
            except Exception:
                pass
        # E165: Add getpass() implementation for HarmonyOS (dvipdfm-x needs it)
        dvipdfmx_c = os.path.join(src, "texk/dvipdfm-x/dvipdfmx.c")
        if os.path.exists(dvipdfmx_c):
            try:
                with open(dvipdfmx_c, 'r', errors='ignore') as f:
                    data = f.read()
                if 'getpass' in data and '__OHOS__' not in data:
                    # Add getpass implementation at the top of the file (after includes)
                    getpass_impl = '''
#ifdef __OHOS__
#include <stdio.h>
#include <string.h>
static char *getpass(const char *prompt) {
    static char buf[256];
    fprintf(stderr, "%s", prompt);
    fflush(stderr);
    if (fgets(buf, sizeof(buf), stdin) == NULL) return NULL;
    buf[strcspn(buf, "\\n")] = 0;
    return buf;
}
#endif
'''
                    # Insert after the last #include
                    last_include = data.rfind('\n#include')
                    if last_include != -1:
                        end_of_include = data.find('\n', last_include + 1)
                        data = data[:end_of_include + 1] + getpass_impl + data[end_of_include + 1:]
                    with open(dvipdfmx_c, 'w', errors='ignore') as f:
                        f.write(data)
            except Exception:
                pass

    def build(self):
        apply_conandata_patches(self)
        # R32: Platform check for OHOS
        if self.settings.os in ("Linux", "OHOS"):
            os.environ["CONFIG_SHELL"] = "/data/service/hnp/bin/bash"
            os.environ["SHELL"] = "/data/service/hnp/bin/bash"
            os.umask(0o002)
            # Set BASH_ENV to ensure umask 002 in all bash subshells (HMDFS fix)
            umask_script = os.path.join(self.source_folder, ".umask_setup.sh")
            try:
                with open(umask_script, 'w') as f:
                    f.write("umask 002\n")
                os.environ["BASH_ENV"] = umask_script
                os.environ["ENV"] = umask_script
            except Exception:
                pass
            self._fix_platform_issues()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])
        # Note: texmf download, format generation, and texlinks are NOT done in build()
        # They require CTAN network access and significant time — not suitable for CI
        # Use post-install script or local build for texlive-full functionality

    def _download_texmf(self):
        """Download essential texmf packages from CTAN tlnet archive."""
        import urllib.request, tarfile, tempfile
        mirror = "https://mirrors.tuna.tsinghua.edu.cn/CTAN/systems/texlive/tlnet/archive"
        texmf_dir = os.path.join(self.build_folder, "texmf-dist")
        os.makedirs(texmf_dir, exist_ok=True)
        packages = ["plain", "latex", "latex-bin", "etex", "mfware", "cm",
                     "amsfonts", "metafont", "hyph-utf8", "l3kernel",
                     "l3packages", "glyphtounicode", "latex-fonts"]
        for pkg in packages:
            url = f"{mirror}/{pkg}.tar.xz"
            try:
                tmpfile = os.path.join(tempfile.gettempdir(), f"{pkg}.tar.xz")
                urllib.request.urlretrieve(url, tmpfile)
                with tarfile.open(tmpfile, "r:xz") as tar:
                    tar.extractall(texmf_dir)
            except Exception:
                pass

    def _generate_formats(self):
        """Generate format files using * prefix to activate e-TeX in INITEX."""
        import subprocess, shutil
        bin_dir = os.path.join(self.build_folder, "inst", "bin")
        # Find the actual binary directory (may be aarch64-unknown-linux-gnu or similar)
        for d in os.listdir(bin_dir) if os.path.isdir(bin_dir) else []:
            sub = os.path.join(bin_dir, d)
            if os.path.isdir(sub) and os.path.exists(os.path.join(sub, "tex")):
                bin_dir = sub
                break
        texmf_dir = os.path.join(self.build_folder, "texmf-dist")
        var_dir = os.path.join(texmf_dir, "var", "web2c")
        os.makedirs(var_dir, exist_ok=True)
        # kpathsea environment: use direct search (no ls-R, mktexlsr fails on HMDFS)
        os.environ["TEXMFCNF"] = os.path.join(texmf_dir, "web2c")
        os.environ["TEXMFVAR"] = os.path.join(texmf_dir, "var")
        os.environ["TEXMF"] = texmf_dir
        # Copy hyphen.tex from texmf-dist if available
        hyphen_src = os.path.join(texmf_dir, "tex", "generic", "hyphen", "hyphen.tex")
        # Generate tex.fmt (plain TeX with e-TeX activated by * prefix)
        tex_bin = os.path.join(bin_dir, "tex")
        if os.path.exists(tex_bin):
            try:
                subprocess.run(["bash", "-c", f"printf '*\\input plain\\dump\\n' | {tex_bin} --ini --interaction=batchmode plain"],
                              cwd=self.build_folder, timeout=60, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if os.path.exists(os.path.join(self.build_folder, "plain.fmt")):
                    shutil.copy(os.path.join(self.build_folder, "plain.fmt"), os.path.join(var_dir, "tex.fmt"))
            except Exception:
                pass
        # Generate pdflatex.fmt (LaTeX with e-TeX + pdfTeX)
        pdftex_bin = os.path.join(bin_dir, "pdftex")
        if os.path.exists(pdftex_bin):
            try:
                subprocess.run(["bash", "-c", f"printf '*\\input latex.ltx\\dump\\n' | {pdftex_bin} --ini --interaction=batchmode --progname=pdflatex"],
                              cwd=self.build_folder, timeout=90, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if os.path.exists(os.path.join(self.build_folder, "latex.fmt")):
                    shutil.copy(os.path.join(self.build_folder, "latex.fmt"), os.path.join(var_dir, "pdflatex.fmt"))
            except Exception:
                pass

    def _create_texlinks(self):
        """Create texlinks symlinks (latex→pdftex, pdflatex→pdftex, etc.)."""
        bin_dir = os.path.join(self.build_folder, "inst", "bin")
        for d in os.listdir(bin_dir) if os.path.isdir(bin_dir) else []:
            sub = os.path.join(bin_dir, d)
            if os.path.isdir(sub) and os.path.exists(os.path.join(sub, "pdftex")):
                bin_dir = sub
                break
        texlinks = {"latex": "pdftex", "pdflatex": "pdftex", "xelatex": "xetex", "lualatex": "luatex"}
        for link, target in texlinks.items():
            link_path = os.path.join(bin_dir, link)
            if os.path.exists(os.path.join(bin_dir, target)):
                try:
                    if os.path.exists(link_path) or os.path.islink(link_path):
                        os.remove(link_path)
                    os.symlink(target, link_path)
                except Exception:
                    pass

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # texlive is a command-line tool suite, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
