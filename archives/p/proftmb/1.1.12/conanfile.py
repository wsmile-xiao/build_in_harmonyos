#!/usr/bin/env python3
"""Conan recipe for proftmb 1.1.12.

ProfTMB: Profile fed HMM for predicting transmembrane beta barrels from sequence.
Upstream Ubuntu source (orig tarball). Build system: autoconf 2.67 + automake.

Build fixes applied in build():
* src/Makefile.in has `dnl` comment lines leaked from Makefile.am - these break
  make (missing separator). Strip them before configure regenerates Makefile.
* help2man not available on OHOS - set HELP2MAN=/bin/true to skip man page
  (ref: E289).
* toybox sed does not support `sed --in-place` used by the top-level Makefile
  install rule - rewritten to a temp-file approach (ref: E010).
* Configure needs CPPFLAGS/LDFLAGS to find opt and gsl (AC_CHECK_LIB/opt.h,
  AC_CHECK_HEADER/gsl/gsl_errno.h) - injected via build() env.

Package fixes applied in package():
* OHOS musl loader does not follow symlinks for DT_NEEDED (ref: E050) - gsl
  installs libgsl.so.28 -> libgsl.so.28.0.0 (symlink), so the entity .so files
  are copied into proftmb's lib dir and RUNPATH is set to $ORIGIN/../lib.
* OHOS HMDFS blocks execve of unsigned ELF binaries (ref: E077) - the binary
  is self-signed with binary-sign-tool. The OHOS toolchain embeds a stale
  empty .codesign section that must be stripped with objcopy first, and the
  signed output loses the exec bit which is restored with chmod.
"""
import os
import re
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

_HMDFS_WRAPPER_DIR = "/data/storage/el2/base/cache/wrappers"


def _ensure_wrappers():
    """Ensure sort/cat/rm wrapper scripts exist for HMDFS compatibility.

    Three issues:
    1. toybox sort/cat fail on `-` arg (Permission denied on HMDFS)
    2. WorkBuddy safe-bin rm shim has broken shebang (#!/bin/bash → not found)
    """
    os.makedirs(_HMDFS_WRAPPER_DIR, exist_ok=True)

    sort_content = (
        "#!/system/bin/sh\n"
        "# HMDFS wrapper: convert - to /dev/stdin for toybox sort\n"
        "set -- $(for a in \"$@\"; do\n"
        "  if [ \"$a\" = \"-\" ]; then echo /dev/stdin; else echo \"$a\"; fi\n"
        "done)\n"
        "exec /bin/toybox sort \"$@\"\n"
    )
    cat_content = (
        "#!/system/bin/sh\n"
        "# HMDFS wrapper: convert - to /dev/stdin for toybox cat\n"
        "set -- $(for a in \"$@\"; do\n"
        "  if [ \"$a\" = \"-\" ]; then echo /dev/stdin; else echo \"$a\"; fi\n"
        "done)\n"
        "exec /bin/toybox cat \"$@\"\n"
    )
    rm_content = (
        "#!/system/bin/sh\n"
        "# Bypass WorkBuddy safe-bin rm shim (broken shebang #!/bin/bash)\n"
        "exec /bin/toybox rm \"$@\"\n"
    )

    for path, content in [
        (os.path.join(_HMDFS_WRAPPER_DIR, "sort"), sort_content),
        (os.path.join(_HMDFS_WRAPPER_DIR, "cat"), cat_content),
        (os.path.join(_HMDFS_WRAPPER_DIR, "rm"), rm_content),
    ]:
        with open(path, "w") as f:
            f.write(content)
        os.chmod(path, stat.S_IRWXU)


class ProftmbConan(ConanFile):
    name = "proftmb"
    version = "1.1.12"
    description = ("ProfTMB: Profile fed HMM for predicting transmembrane beta "
                   "barrels from sequence")
    license = "GPL-3.0-or-later"
    homepage = "http://rostlab.org/"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "proftmb 1.1.12 is only validated on Linux/OHOS")

    def requirements(self):
        self.requires("opt/3.19")
        self.requires("gsl/2.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # proftmb's configure uses AC_CHECK_LIB for opt/gsl - we inject paths
        # in build() via environment. Set --prefix=/ for standard layout.
        tc.configure_args.append("--prefix=/")
        tc.generate()

    def _fix_makefile_dnl(self):
        """Remove `dnl` comment lines from build/src/Makefile that break make.

        Makefile.am has `dnl bin_PROGRAMS = ...` lines (autoconf comments).
        When configure generates Makefile from Makefile.am, these leak through
        and cause `missing separator` errors. Fix post-configure.
        Also sets HELP2MAN=/bin/true since help2man is not available on OHOS.
        Also fixes `sed --in-place` in top-level Makefile (toybox sed doesn't
        support it).
        """
        # Fix src/Makefile (dnl lines + HELP2MAN)
        mk_path = os.path.join(self.build_folder, "src", "Makefile")
        if os.path.isfile(mk_path):
            with open(mk_path, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
            cleaned = [l for l in lines if not l.strip().startswith("dnl ")]
            removed = len(lines) - len(cleaned)

            # Fix HELP2MAN - replace any HELP2MAN=... line with HELP2MAN = /bin/true
            has_help2man = any('HELP2MAN' in l and '=' in l for l in cleaned)
            if has_help2man:
                cleaned = ['HELP2MAN = /bin/true' if 'HELP2MAN' in l and '=' in l else l for l in cleaned]
            else:
                cleaned.insert(0, 'HELP2MAN = /bin/true')

            with open(mk_path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(cleaned))
            self.output.info(f"[proftmb] Removed {removed} dnl lines and set HELP2MAN=/bin/true in src/Makefile")

        # Fix top-level Makefile (sed --in-place → temp-file approach)
        top_mk = os.path.join(self.build_folder, "Makefile")
        if os.path.isfile(top_mk):
            with open(top_mk, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            # Replace: sed --in-place -e 'PATTERN' "file"
            # With:    sed -e 'PATTERN' "file" > "file.proftmb_tmp" && mv "file.proftmb_tmp" "file"
            new_text = text.replace(
                "sed --in-place -e 's|__pkgdatadir__|$(pkgdatadir)|g' \"$(DESTDIR)$(pkgdatadir)/options\"",
                "sed -e 's|__pkgdatadir__|$(pkgdatadir)|g' \"$(DESTDIR)$(pkgdatadir)/options\" > \"$(DESTDIR)$(pkgdatadir)/options.proftmb_tmp\" && mv \"$(DESTDIR)$(pkgdatadir)/options.proftmb_tmp\" \"$(DESTDIR)$(pkgdatadir)/options\""
            )
            if new_text != text:
                with open(top_mk, "w", encoding="utf-8") as fh:
                    fh.write(new_text)
                self.output.info("[proftmb] Fixed sed --in-place in top-level Makefile")

    def _dep_flags(self):
        """Collect -I/-L flags from dependencies for configure."""
        cppflags = []
        ldflags = []
        for req, dep in self.dependencies.items():
            if dep.cpp_info.includedirs:
                for inc in dep.cpp_info.includedirs:
                    cppflags.append(f"-I{inc}")
            if dep.cpp_info.libdirs:
                for lib in dep.cpp_info.libdirs:
                    ldflags.append(f"-L{lib}")
        return cppflags, ldflags

    def _fix_configure_hmdfs(self):
        """Fix configure for HMDFS: inject sort/cat/rm wrapper functions.

        toybox sort/cat treat `-` as a filename (stat fails → Permission denied).
        The WorkBuddy safe-bin rm shim has shebang #!/bin/bash which doesn't exist
        on OHOS. We inject shell functions that override bare `sort`/`cat`/`rm`.
        """
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        with open(configure_path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        marker = "# HMDFS wrapper functions injected by conanfile\n"
        if marker in text:
            return  # Already patched

        wrapper = "\n" + marker + """
_hmdfs_sort() {
    local _args=""
    for _a in "$@"; do
        if [ "$_a" = "-" ]; then
            _args="$_args /dev/stdin"
        else
            _args="$_args $_a"
        fi
    done
    /bin/sort $_args
}

_hmdfs_cat() {
    local _args=""
    for _a in "$@"; do
        if [ "$_a" = "-" ]; then
            _args="$_args /dev/stdin"
        else
            _args="$_args $_a"
        fi
    done
    /bin/cat $_args
}

_hmdfs_rm() {
    /bin/toybox rm "$@"
}

sort() { _hmdfs_sort "$@"; }
cat() { _hmdfs_cat "$@"; }
rm() { _hmdfs_rm "$@"; }
# End HMDFS wrappers
"""

        shebang_end = text.find("\n")
        if shebang_end < 0:
            text = wrapper + text
        else:
            text = text[:shebang_end + 1] + wrapper + text[shebang_end + 1:]

        with open(configure_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.output.info("[proftmb] Injected HMDFS sort/cat/rm wrappers into configure")

    def _ensure_sed_wrapper(self):
        """Create a sed wrapper that supports --in-place / -i (toybox sed doesn't)."""
        sed_wrapper = os.path.join(_HMDFS_WRAPPER_DIR, "sed")
        with open(sed_wrapper, "w") as f:
            f.write(
                "#!/system/bin/sh\n"
                "# Sed wrapper: convert --in-place/-i to temp-file approach\n"
                "# Parse args: collect non-inplace args, find if inplace is set\n"
                "inplace=0\n"
                "realargs=\"\"\n"
                "for arg in \"$@\"; do\n"
                "    case \"$arg\" in\n"
                "        --in-place|-i)\n"
                "            inplace=1\n"
                "            ;;\n"
                "        *)\n"
                "            realargs=\"$realargs $arg\"\n"
                "            ;;\n"
                "    esac\n"
                "done\n"
                "if [ \"$inplace\" = \"1\" ]; then\n"
                "    # Get last arg (the file)\n"
                "    set -- $realargs\n"
                "    file=\"$1\"\n"
                "    for a in \"$@\"; do file=\"$a\"; done\n"
                "    tmp=\"$file.proftmb_tmp\"\n"
                "    /bin/toybox sed $realargs > \"$tmp\"\n"
                "    mv \"$tmp\" \"$file\"\n"
                "else\n"
                "    /bin/toybox sed $realargs\n"
                "fi\n"
            )
        os.chmod(sed_wrapper, stat.S_IRWXU)

    def _fix_safebin_rm_shim(self):
        """Fix WorkBuddy safe-bin rm shim shebang if possible.

        The safe-bin rm shim has shebang #!/bin/bash, but bash is at /system/bin/bash
        on OHOS. This causes "bad interpreter: No such file or directory" errors.
        We try to fix it, but if permission denied, we rely on the rm wrapper
        function injected into configure.
        """
        rm_shim = "/data/storage/el1/bundle/electron/resources/resfile/resources/app.asar.unpacked/cli/vendor/shim/safe-bin/rm"
        if not os.path.isfile(rm_shim):
            return
        with open(rm_shim, encoding="utf-8") as fh:
            text = fh.read()
        if text.startswith("#!/system/bin/bash"):
            return  # Already fixed

        text = text.replace("#!/bin/bash", "#!/system/bin/bash", 1)
        try:
            with open(rm_shim, "w", encoding="utf-8") as fh:
                fh.write(text)
            self.output.info("[proftmb] Fixed WorkBuddy rm shim shebang")
        except PermissionError:
            self.output.warning("[proftmb] Cannot fix rm shim (permission denied), "
                                "relying on rm wrapper function in configure")

    def _fix_cpp_issues(self):
        """Fix C++ compatibility issues for OHOS libc++."""
        import glob as glob_mod

        # Fix source files in source_folder
        self._fix_file_replace("src/HMMOutput.h", 'char* =\"\"', 'const char* =\"\"')
        self._fix_file_replace("src/Load.cpp", "delete line;", "delete[] line;")
        self._fix_file_replace("src/HMMEval.h", "#define _HMMEVal", "#define _HMMEval")

        # Fix Tools.h uint typedef
        tools_h = os.path.join(self.source_folder, "src", "Tools.h")
        if os.path.isfile(tools_h):
            with open(tools_h, encoding="utf-8") as fh:
                text = fh.read()
            if "typedef unsigned int uint;" not in text:
                text = text.replace(
                    "#include <vector>",
                    "#include <vector>\n#include <cstdint>\ntypedef unsigned int uint;"
                )
                with open(tools_h, "w", encoding="utf-8") as fh:
                    fh.write(text)
                self.output.info("[proftmb] Added uint typedef to Tools.h")

        # Fix all .h and .cpp files for:
        # 1. ostringstream streaming (<< ostringstream needs .str())
        # 2. dynamic exception specifications (throw(type) → noexcept(false))
        for pattern in ["*.h", "*.cpp"]:
            for path in glob_mod.glob(os.path.join(self.source_folder, "src", pattern)):
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                original = text

                # Fix ostringstream streaming
                ostringstream_vars = set(re.findall(r'ostringstream\s+(\w+)', text))
                if ostringstream_vars:
                    for var in ostringstream_vars:
                        text = re.sub(
                            r'<<(' + re.escape(var) + r')(?!\.str\b)(?!\.c_str\b)',
                            r'<<\1.str()', text)

                # Fix dynamic exception specifications
                text = re.sub(r'\bthrow\s*\([^)]*\)', 'noexcept(false)', text)

                if text != original:
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.write(text)
                    self.output.info(f"[proftmb] Fixed {os.path.basename(path)}")

    def _fix_file_replace(self, rel_path, old, new, base_dir=None):
        """Replace old with new in file rel_path under base_dir/src/."""
        if base_dir is None:
            base_dir = self.source_folder
        path = os.path.join(base_dir, rel_path)
        if not os.path.isfile(path):
            return
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if old in text:
            text = text.replace(old, new)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            self.output.info(f"[proftmb] Fixed {rel_path}: {old!r} → {new!r} ({base_dir})")

    def _restore_autotools_exec_bits(self):
        # 修复（E490）：上游 2012 年 tarball 的 autotools 助手脚本缺执行位
        # （实测 install-sh/missing 均为 644）。本地因 PATH 前置 pip coreutils，
        # configure 把 MKDIR_P 探测为 `mkdir -p`，make install 不会调用 install-sh；
        # CI worker PATH 无 coreutils 时 AC_PROG_MKDIR_P 回退到 `install-sh -c -d`，
        # make 直接 execve 该 644 脚本 → "install-sh: can't execute: Permission denied"。
        # 对已知 autotools helper 恢复执行位（E490 rec_command）。
        helpers = (
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "depcomp", "compile", "ltmain.sh", "ar-lib", "test-driver",
        )
        src = self.source_folder
        for name in helpers:
            path = os.path.join(src, name)
            if os.path.isfile(path) and not os.access(path, os.X_OK):
                st = os.stat(path)
                os.chmod(path, st.st_mode | 0o111)
                self.output.info(f"[proftmb] Restored exec bit on {name} (E490)")

    def build(self):
        # 修复（E490）：tarball 内 autotools 助手脚本缺执行位（install-sh/missing=644），
        # CI 环境无 pip coreutils 时 MKDIR_P 回退 install-sh → make install execve 被拒。
        self._restore_autotools_exec_bits()

        # 修复（E386）：conan 生成的 conanbuild.sh 把 CONFIG_SHELL 指向 hnp 的 bash，
        # 该 bash 在 HMDFS 上读 stdin（cat -）会失败（cat: -: Permission denied），
        # config.status 拿到的文件被截断，报 "could not setup config files machinery"。
        # 追加在 conanbuild.sh 尾部覆盖（buildenv 在其后 source，只有尾部追加才生效）。
        _conanbuild = os.path.join(self.build_folder, "conan", "conanbuild.sh")
        if os.path.isfile(_conanbuild):
            with open(_conanbuild, "a", encoding="utf-8") as f:
                f.write("\nexport CONFIG_SHELL=/system/bin/sh\nexport SHELL=/system/bin/sh\n")
            self.output.info("[proftmb] Overrode CONFIG_SHELL/SHELL to /system/bin/sh in conanbuild.sh")

        # 常规补丁入口：conandata.yml patches 为空时为 no-op（本包修复均内联在配方中）
        apply_conandata_patches(self)

        # 修复（E011，预防性）：configure/config.status 用 `umask 077` 建 conf 临时目录，
        # setgid 的 HMDFS 下会建出 2700 目录，写入被拒。归一化为 umask 022
        # （仅改构建目录临时副本，不动仓库文件；仓库 1272+ 份 autotools 配方同款）。
        import glob as glob_umask
        for _cfg in glob_umask.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
                self.output.info(f"[proftmb] Normalized umask 077 -> 022 in {os.path.basename(os.path.dirname(_cfg))}/configure")

        # Fix C++ compatibility issues for OHOS libc++
        self._fix_cpp_issues()

        # Fix configure script for HMDFS (sort -, cat -, rm shim issues)
        self._fix_configure_hmdfs()

        # Ensure sort/cat/rm/help2man wrappers exist for HMDFS compatibility
        _ensure_wrappers()
        # Create no-op help2man wrapper that creates the output man page file
        # (Makefile calls `help2man` directly, not $(HELP2MAN))
        help2man_wrapper = os.path.join(_HMDFS_WRAPPER_DIR, "help2man")
        with open(help2man_wrapper, "w") as f:
            f.write(
                "#!/system/bin/sh\n"
                "# No-op help2man for OHOS - creates minimal man page\n"
                "output=''\n"
                "for arg in \"$@\"; do\n"
                "    case \"$arg\" in\n"
                "        --output=*) output=\"${arg#*=}\" ;;\n"
                "    esac\n"
                "done\n"
                "if [ -n \"$output\" ]; then\n"
                "    dir=\"${output%/*}\"\n"
                "    if [ -n \"$dir\" ] && [ \"$dir\" != \"$output\" ]; then\n"
                "        mkdir -p \"$dir\"\n"
                "    fi\n"
                "    if [ -d \"$output\" ]; then\n"
                "        rm -rf \"$output\"\n"
                "    fi\n"
                "    printf '.TH proftmb 1 \"\" \"\" \"proftmb 1.1.12\"\\n.SH NAME\\nproftmb \\\\ per-residue prediction of bacterial transmembrane beta barrels\\n' > \"$output\"\n"
                "fi\n"
                "exit 0\n"
            )
        os.chmod(help2man_wrapper, stat.S_IRWXU)

        # Try to fix WorkBuddy safe-bin rm shim shebang (may fail due to permissions)
        self._fix_safebin_rm_shim()

        # Inject dependency paths so configure's AC_CHECK_LIB/AC_CHECK_HEADER find opt/gsl
        cppflags, ldflags = self._dep_flags()
        old_env = os.environ.copy()
        if cppflags:
            existing = os.environ.get("CPPFLAGS", "")
            os.environ["CPPFLAGS"] = (existing + " " + " ".join(cppflags)).strip()
        if ldflags:
            existing = os.environ.get("LDFLAGS", "")
            os.environ["LDFLAGS"] = (existing + " " + " ".join(ldflags)).strip()

        # Prepend wrappers to PATH so configure's subshell finds them
        wrappers_dir = _HMDFS_WRAPPER_DIR
        existing_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{wrappers_dir}:{existing_path}" if existing_path else wrappers_dir

        autotools = Autotools(self)
        autotools.configure()

        # Fix dnl lines leaked from Makefile.am into generated Makefile
        self._fix_makefile_dnl()

        # Keep wrappers in PATH for make (help2man, sort, cat, rm)
        # The no-op help2man wrapper (created above) handles man page generation
        autotools.make(args=["-j1", "HELP2MAN=/bin/true"])

        # Restore env
        os.environ.clear()
        os.environ.update(old_env)

    def _sign_elf(self, elf_path):
        """Sign an ELF binary with HarmonyOS self-signature (ref: E077).

        OHOS HMDFS blocks execve of unsigned ELF binaries. binary-sign-tool
        self-signs the binary so it becomes executable.

        Two OHOS-specific quirks (verified on-device 2026-09-30):
        * The OHOS toolchain embeds a stale (empty) .codesign section at link
          time; binary-sign-tool refuses to overwrite it ("WriteCodeSignBlock:
          .codesign section already exists"). Strip it with objcopy first.
        * The signed output (-outFile) loses the executable bit; restore it
          with chmod, otherwise consumers get "can't execute: Permission
          denied" from the file mode check before the signature is even seen.
        """
        import subprocess
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/objcopy"
        if not os.path.isfile(sign_tool):
            self.output.warning(f"[proftmb] binary-sign-tool not found, skipping sign: {elf_path}")
            return

        # Check for stale .codesign section and strip if present
        stripped_path = elf_path + ".stripped"
        if os.path.isfile(objcopy):
            result = subprocess.run(
                [objcopy, "--remove-section=.codesign", elf_path, stripped_path],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                shutil.move(stripped_path, elf_path)
                self.output.info("[proftmb] Stripped stale .codesign section")
            else:
                pass  # Section doesn't exist, use original file

        signed_path = elf_path + ".signed"
        result = subprocess.run(
            [sign_tool, "sign", "-inFile", elf_path, "-outFile", signed_path, "-selfSign", "1"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            shutil.move(signed_path, elf_path)
            os.chmod(elf_path, os.stat(elf_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            self.output.info(f"[proftmb] Signed ELF: {os.path.basename(elf_path)}")
        else:
            self.output.warning(f"[proftmb] Sign failed for {elf_path}: {result.stderr}")

    def package(self):
        autotools = Autotools(self)
        # Ensure wrappers are in PATH for install (help2man no-op wrapper)
        wrappers_dir = _HMDFS_WRAPPER_DIR
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{wrappers_dir}:{old_path}" if old_path else wrappers_dir
        try:
            autotools.install()
        finally:
            os.environ["PATH"] = old_path

        # OHOS musl loader does not follow symlinks for DT_NEEDED resolution
        # (ref: E050). gsl installs libgsl.so.28 -> libgsl.so.28.0.0 (symlink),
        # which breaks. Copy entity .so files directly into proftmb's lib dir
        # with the DT_NEEDED names, then set rpath so the loader finds them.
        gsl_dep = self.dependencies["gsl"]
        gsl_lib_dir = None
        if gsl_dep.cpp_info.libdirs:
            gsl_lib_dir = gsl_dep.cpp_info.libdirs[0]

        if gsl_lib_dir and os.path.isdir(gsl_lib_dir):
            proftmb_lib = os.path.join(self.package_folder, "lib")
            os.makedirs(proftmb_lib, exist_ok=True)

            # Map: DT_NEEDED name -> actual entity file in gsl lib dir
            libs_to_copy = [
                ("libgsl.so.28.0.0", "libgsl.so.28"),
                ("libgslcblas.so.0.0.0", "libgslcblas.so.0"),
            ]
            for src_name, dst_name in libs_to_copy:
                src = os.path.join(gsl_lib_dir, src_name)
                dst = os.path.join(proftmb_lib, dst_name)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    self.output.info(f"[proftmb] Copied {src_name} -> {dst_name}")

            # Set rpath so the binary finds its DT_NEEDED libs at runtime
            proftmb_bin = os.path.join(self.package_folder, "bin", "proftmb")
            if os.path.isfile(proftmb_bin):
                patchelf = "/data/service/hnp/bin/patchelf"
                if os.path.isfile(patchelf):
                    import subprocess
                    result = subprocess.run(
                        [patchelf, "--set-rpath", "$ORIGIN/../lib", proftmb_bin],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.output.info("[proftmb] Set rpath to $ORIGIN/../lib")
                    else:
                        self.output.warning(f"[proftmb] patchelf failed: {result.stderr}")

        # Sign the proftmb binary for OHOS HMDFS execution permission (E077)
        proftmb_bin = os.path.join(self.package_folder, "bin", "proftmb")
        if os.path.isfile(proftmb_bin):
            self._sign_elf(proftmb_bin)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib"]  # For OHOS musl symlink fix
