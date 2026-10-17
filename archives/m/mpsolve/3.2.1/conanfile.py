#!/usr/bin/env python3
"""Conan recipe — mpsolve 3.2.1 (autotools, polynomial root-finder).

MPSolve solves polynomials/secular equations with arbitrary precision. The
GitHub tag archive ships no generated `configure`, so the recipe bootstraps
with `autoreconf -fi` (tool_requires automake/libtool, applied through ELF
launchers — see below).

Dependencies: gmp/6.3.0.1 — the CXX-enabled build (`--enable-cxx` in its
recipe). libmps unconditionally compiles src/libmps/formal/*.cpp, which use
the GMP C++ bindings (mpq_class from gmpxx.h); the base gmp/6.3.0 package
ships no gmpxx. check/0.15.2 is picked up through PKG_CHECK_MODULES and
drives the upstream `make check` suites (check programs in src/tests).

OHOS adaptations (pattern adopted from the merged abiword-plugin-* recipes):
  - OHOS blocks shebang-based script execution for the conan tool scripts,
    so automake/aclocal/libtoolize/libtool run through small ELF launchers
    compiled at build time (_prepare_autotools_tools);
  - the generated configure is run explicitly via `bash ./configure`;
  - `umask 077` is dropped from the generated configure (E114: HMDFS makes
    the 0700 temp dir unwritable even for its owner);
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
  - make check needs TEMP redirected (check's IPC temp file; host /tmp is
    read-only) and LD_LIBRARY_PATH for the shared libgmpxx/libcheck.
"""
import os
import re
import shutil

SHELL_FIX = "env -u CONFIG_SHELL SHELL=/bin/sh"

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# C source for the ELF launcher.  {interp}/{script}/{modpath}/{fixedN} are
# baked in at build time via str.format (repr() -> valid C string literals).
_LAUNCHER_TEMPLATE = (
    "#include <unistd.h>\n"
    "static const char * INTERP = {interp};\n"
    "static const char * SCRIPT = {script};\n"
    "static const char * MODPATH = {modpath};\n"
    "static const char * FIXED1 = {fixed1};\n"
    "static const char * FIXED2 = {fixed2};\n"
    "static const char * FIXED3 = {fixed3};\n"
    "int main(int argc, char **argv) {{\n"
    "    char *nargv[128];\n"
    "    int n = 0;\n"
    "    nargv[n++] = (char*)INTERP;\n"
    "    if (MODPATH[0] != '\\0') {{ nargv[n++] = (char*)\"-I\"; nargv[n++] = (char*)MODPATH; }}\n"
    "    nargv[n++] = (char*)SCRIPT;\n"
    "    if (FIXED1[0] != '\\0') nargv[n++] = (char*)FIXED1;\n"
    "    if (FIXED2[0] != '\\0') nargv[n++] = (char*)FIXED2;\n"
    "    if (FIXED3[0] != '\\0') nargv[n++] = (char*)FIXED3;\n"
    "    for (int i = 1; i < argc && n < 124; i++) nargv[n++] = argv[i];\n"
    "    nargv[n] = NULL;\n"
    "    execv(INTERP, nargv);\n"
    "    return 127;\n"
    "}}\n"
)


def _c_str(v):
    """Escape a value as a C double-quoted string literal."""
    return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _is_elf(path):
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except OSError:
        return False


def _find_real_clang(cc):
    """The OHOS SDK 'clang' on PATH may be a /bin/sh wrapper script; resolve
    the real ELF clang binary (hnp_file SELinux context, exec-able from the
    build domain)."""
    candidates = []
    if cc:
        real = os.path.realpath(cc)
        if _is_elf(real):
            return real
    import glob
    for g in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang-[0-9]*",
              "/data/service/hnp/bin/clang-[0-9]*"):
        for cand in sorted(glob.glob(g)):
            if _is_elf(cand):
                candidates.append(cand)
    if candidates:
        return sorted(candidates)[-1]
    return cc


def _stage_clang(conanfile):
    staged = os.environ.get("_OHOS_REAL_CC", "")
    if staged and os.path.isfile(staged):
        return staged
    ccs = conanfile.conf.get("tools.build:compiler_executables", default={}) or {}
    real = _find_real_clang(ccs.get("c") or shutil.which("clang") or "")
    if real and os.path.isfile(real):
        os.environ["_OHOS_REAL_CC"] = real
    return real


def _fix_compiler_env(conanfile):
    """Patch the generated conanautotoolstoolchain.sh so CC/CXX point at the
    real clang ELF (the profile path may be an unexecutable wrapper)."""
    sh = os.path.join(conanfile.generators_folder, "conanautotoolstoolchain.sh")
    if not os.path.isfile(sh):
        return
    data = open(sh, encoding="utf-8").read()
    staged = _stage_clang(conanfile)
    if staged:
        cxx = staged.replace("/clang-", "/clang++-")
        if not os.path.isfile(cxx):
            cxx = os.path.join(os.path.dirname(staged), "clang++")
        data = re.sub(r'export CC="[^"]*"', 'export CC="' + staged + '"', data)
        if os.path.isfile(cxx):
            data = re.sub(r'export CXX="[^"]*"', 'export CXX="' + cxx + '"', data)
    open(sh, "w", encoding="utf-8").write(data)


def _prepare_autotools_env():
    """Point AUTOCONF/AUTOM4TE etc. at whatever is on PATH (the installed
    automake scripts hardcode absolute paths that may not exist here)."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _compile_launcher(conanfile, launcher_dir, name, interp, script, extra_args):
    """Compile a tiny ELF launcher that execs `interp script extra_args "$@"`.
    OHOS blocks shebang-based script execution, so this is the only way to
    run the perl/shell tool scripts packaged by conan."""
    modpath = extra_args.pop("modpath", "")
    fixed = ["", "", ""]
    idx = 0
    for k in sorted([k for k in extra_args if k.startswith("fixed")]):
        if idx < 3:
            fixed[idx] = extra_args[k]
        idx += 1
    body = _LAUNCHER_TEMPLATE.format(
        interp=_c_str(interp), script=_c_str(script), modpath=_c_str(modpath),
        fixed1=_c_str(fixed[0]), fixed2=_c_str(fixed[1]), fixed3=_c_str(fixed[2]))
    src = os.path.join(launcher_dir, name + ".c")
    with open(src, "w", encoding="utf-8") as f:
        f.write(body)
    staged = os.environ.get("_OHOS_REAL_CC", "")
    if not staged or not os.path.isfile(staged):
        ccs = conanfile.conf.get("tools.build:compiler_executables", default={}) or {}
        staged = _find_real_clang(ccs.get("c") or shutil.which("clang") or "clang")
    out = os.path.join(launcher_dir, name)
    conanfile.run(" ".join([staged, "-o", out, src]), env="conanbuild",
                  cwd=conanfile.build_folder)


def _patch_conanbuild_env(conanfile, launcher_dir, ltpkg):
    """Rewrite the generated conanbuild env so AUTOMAKE/ACLOCAL/LIBTOOLIZE
    (which autoreconf prefers over PATH) and _lt_pkgdatadir point at the
    staged ELF launchers / fake pkgdatadir; put the launcher dir first on
    PATH.  Generic regex rewrite: the conan cache paths vary per CONAN_HOME."""
    gens = conanfile.generators_folder
    for fname in os.listdir(gens):
        if not (fname.startswith("conanbuildenv-") and fname.endswith(".sh")):
            continue
        path = os.path.join(gens, fname)
        data = open(path, encoding="utf-8").read()
        data = re.sub(r'export AUTOMAKE="[^"]*"',
                      'export AUTOMAKE="' + os.path.join(launcher_dir, "automake") + '"', data)
        data = re.sub(r'export ACLOCAL="[^"]*"',
                      'export ACLOCAL="' + os.path.join(launcher_dir, "aclocal") + '"', data)
        data = re.sub(r'export LIBTOOLIZE="[^"]*"',
                      'export LIBTOOLIZE="' + os.path.join(launcher_dir, "libtoolize") + '"', data)
        data = re.sub(r'export _lt_pkgdatadir="[^"]*"',
                      'export _lt_pkgdatadir="' + ltpkg + '"', data)
        data = data.replace('export PATH="' + "/data/service/hnp/bin",
                            'export PATH="' + launcher_dir + ":" + "/data/service/hnp/bin")
        open(path, "w", encoding="utf-8").write(data)


def _prepare_autotools_tools(conanfile):
    """Stage ELF launchers for automake/aclocal/libtoolize/libtool and the
    fake libtool pkgdatadir, and prepend the launcher dir to PATH."""
    launcher_dir = os.path.join(conanfile.build_folder, "autotools-launchers")
    os.makedirs(launcher_dir, exist_ok=True)

    autom = conanfile.dependencies.build["automake"].package_folder
    libt = conanfile.dependencies.build["libtool"].package_folder

    perl = shutil.which("perl") or "/data/service/hnp/bin/perl"
    bash = shutil.which("bash") or "/data/service/hnp/bin/bash"

    _stage_clang(conanfile)

    _compile_launcher(
        conanfile, launcher_dir, "automake", perl,
        os.path.join(autom, "bin", ".automake-real"),
        {"modpath": os.path.join(autom, "share", "automake-1.18"),
         "fixed1": "--libdir=" + os.path.join(autom, "share", "automake-1.18")})
    _compile_launcher(
        conanfile, launcher_dir, "aclocal", perl,
        os.path.join(autom, "bin", ".aclocal-real"),
        {"modpath": os.path.join(autom, "share", "automake-1.18"),
         "fixed1": "--automake-acdir=" + os.path.join(autom, "share", "aclocal-1.18"),
         "fixed2": "--system-acdir=" + os.path.join(autom, "share", "aclocal"),
         "fixed3": "-I" + os.path.join(libt, "share", "aclocal")})

    ltpkg = os.path.join(
        os.environ.get("TMPDIR", "/tmp"),
        "mpsolve-ltpkg-" + os.path.basename(conanfile.build_folder))
    for sub in ("build-aux", "m4", "libltdl"):
        os.makedirs(os.path.join(ltpkg, sub), exist_ok=True)
    src_aux = os.path.join(libt, "share", "libtool", "build-aux")
    if os.path.isdir(src_aux):
        for fn in os.listdir(src_aux):
            shutil.copy2(os.path.join(src_aux, fn), os.path.join(ltpkg, "build-aux", fn))
    src_m4 = os.path.join(libt, "share", "aclocal")
    if os.path.isdir(src_m4):
        for fn in os.listdir(src_m4):
            if fn.endswith(".m4"):
                shutil.copy2(os.path.join(src_m4, fn), os.path.join(ltpkg, "m4", fn))
    with open(os.path.join(ltpkg, "libltdl", "keep.txt"), "w") as f:
        f.write("x\n")
    os.environ["_lt_pkgdatadir"] = ltpkg

    _compile_launcher(conanfile, launcher_dir, "libtoolize", bash,
                      os.path.join(libt, "bin", "libtoolize"), {})
    _compile_launcher(conanfile, launcher_dir, "libtool", bash,
                      os.path.join(libt, "bin", "libtool"), {})

    for name in ("automake-1.18", "aclocal-1.18"):
        base = name.replace("-1.18", "")
        try:
            os.symlink(base, os.path.join(launcher_dir, name))
        except OSError:
            shutil.copy2(os.path.join(launcher_dir, base),
                         os.path.join(launcher_dir, name))
    os.environ["PATH"] = launcher_dir + os.pathsep + os.environ.get("PATH", "")
    _patch_conanbuild_env(conanfile, launcher_dir, ltpkg)


class MpsolveConan(ConanFile):
    name = "mpsolve"
    version = "3.2.1"
    description = "MPSolve — multiprecision polynomial root-finder (arbitrary precision)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/robol/MPSolve"
    url = ""  # CI fills this
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gmp/6.3.0.1 is the CXX-enabled build; libmps's formal module needs
        # the GMP C++ bindings (gmpxx) which the base gmp/6.3.0 lacks.
        self.requires("gmp/6.3.0.1")
        # check: upstream test suites (PKG_CHECK_MODULES([CHECK], ...)), run in build().
        self.requires("check/0.15.2")

    def build_requirements(self):
        # The GitHub tag archive ships no `configure`: bootstrap with
        # autoreconf. automake/libtoolize come from conan (same approach as
        # the merged abiword-plugin-* recipes).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # keep the toolchain configure args for build() (configure is run
        # through `bash` there because the script cannot be exec'd on OHOS)
        self._my_configure_args = (
            "--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos "
            f"--prefix={self.package_folder} "
            # GUI/docs/examples off: OHOS has no GTK/Qt desktop stack here.
            "--disable-ui --disable-graphical-debugger --disable-documentation "
            "--disable-examples --disable-tcmalloc"
        ).split()
        tc.generate()
        _fix_compiler_env(self)
        # check.pc for PKG_CHECK_MODULES([CHECK], [check >= 0.9.4]).
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        _prepare_autotools_env()
        _prepare_autotools_tools(self)
        sf = self.source_folder
        gmp = self.dependencies["gmp"]
        check = self.dependencies["check"]
        gmp_inc = os.path.join(gmp.package_folder, gmp.cpp_info.includedirs[0])
        gmp_lib = os.path.join(gmp.package_folder, gmp.cpp_info.libdirs[0])
        check_lib = os.path.join(check.package_folder, check.cpp_info.libdirs[0])
        # configure.ac consumes GMP_CFLAGS/GMP_LIBS from the environment and
        # appends them to CFLAGS/LDFLAGS for every target ("easy way for the
        # user to override system libgmp", upstream words). GMP_LIBS carries
        # -lgmpxx because libmps's formal module links the C++ bindings.
        gmp_env = (
            f"GMP_CFLAGS='-I{gmp_inc}' "
            f"GMP_LIBS='-L{gmp_lib} -lgmpxx -lgmp'"
        )
        # pkg.m4 for PKG_CHECK_MODULES lives outside the default aclocal path.
        pkg_aclocal = "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal"
        # GitHub tag archives never ship the generated `configure`.
        self.run(f"{SHELL_FIX} ACLOCAL_PATH={pkg_aclocal} autoreconf -fi",
                 cwd=sf, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS).
        _drop_umask_077(self, os.path.join(sf, "configure"))
        # configure is a shell script on an HMDFS mount; shebang exec is
        # blocked in this domain, and hnp bash has a broken getcwd() there,
        # so run it through /bin/sh (SHELL_FIX).
        cfg_args = " ".join(getattr(self, "_my_configure_args", []))
        self.run(f"{SHELL_FIX} {gmp_env} sh ./configure {cfg_args}",
                 cwd=sf, env="conanbuild")
        # E074: parallel make hits the HMDFS jobserver fifo EPERM.
        self.run(f"{SHELL_FIX} {gmp_env} make -j1", cwd=sf, env="conanbuild")
        # Upstream test suites: the src/tests check(3) programs, executed for
        # real.  `make -C src check` keeps the check-recursion out of
        # examples/python/tests (python bindings are disabled via
        # --disable-examples: OHOS has no python dev environment for the
        # bindings module; that example-level suite is reported as a
        # documented non-executed item).  check's IPC temp file needs a
        # writable TEMP (/tmp is read-only) and the test binaries load the
        # shared libs at runtime.
        tmpdir = os.path.join(sf, "check-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        self.run(
            f"{SHELL_FIX} {gmp_env} TEMP={tmpdir} "
            f"LD_LIBRARY_PATH={gmp_lib}:{check_lib}:$LD_LIBRARY_PATH "
            "make -C src check -j1",
            cwd=sf,
            env="conanbuild",
        )

    def package(self):
        self.run(f"{SHELL_FIX} make install -j1", cwd=self.source_folder, env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
