#!/usr/bin/env python3
"""Conan recipe — abiword-plugin-opml 3.0.8.

Builds the AbiWord OPML (.opml) import plugin module for HarmonyOS PC.
The upstream tarball is the full AbiWord 3.0.8 source; only the
self-contained OPML plugin is built (minimal configure.ac + Makefile.am,
mirroring the sibling abiword-plugin-clarisworks adaptation).

The AbiWord runtime API (IE_Imp / IE_Imp_XML / PD_Document / XAP_Module /
fl_AutoNum / UT_* string classes) used by the plugin is provided by a
compile-time compat shim (exported via export_sources).  The OPML plugin
parses XML through AbiWord's own IE_Imp_XML base class — it does NOT depend
on libxml2 (verified: plugins/opml/plugin.m4 only references
${PLUGIN_CFLAGS}/${PLUGIN_LIBS}).  AbiWord core is NOT published for OHOS,
so the shim keeps the module dependency-free.

OHOS adaptations:
  patches (conandata.yml, modified-file diffs only):
    0001-Makefile.am.patch   - replace full AbiWord Makefile.am with a minimal
                              plugin build
    0002-configure.ac.patch  - replace full AbiWord configure.ac with a minimal one
  export_sources (no new-file patches — toybox `patch --dry-run` on OHOS
  applies new-file patches for real, polluting the pristine orig dir and
  breaking the patch pipeline; modified-file diffs are safe):
    compat/  - AbiWord runtime shim (incl. a minimal SAX XML parser)
    tests/   - tests/test_opml_plugin.cpp (end-to-end, R34)

Build notes:
  - the git archive ships no `configure`, so build() runs `autoreconf -fi`;
  - OHOS kernel/SELinux blocks shebang-based script execution on /data
    mounts, so the conan-packaged automake/aclocal/libtoolize scripts
    cannot be exec'd directly.  _prepare_autotools_tools() compiles small
    ELF launchers that invoke perl/bash explicitly (and inject -I for the
    Automake perl modules).  libtoolize additionally needs _lt_pkgdatadir
    (its baked //share/libtool prefix is a broken build-time path), so a
    fake pkgdatadir tree (build-aux + m4 + libltdl) is staged first.
  - the generated configure is then patched to drop `umask 077` from the
    config.status temp-dir creation (E114: HMDFS turns a 0700 temp dir into
    an unwritable drwx--S--- dir);
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM);
  - `make check` runs the end-to-end plugin test (L1 test).  Because the
    libtool shell wrapper cannot execute on OHOS, the check target runs the
    real ELF test binary (check-local) after `make install` so the plugin
    module is reachable via the test binary's RUNPATH.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches, copy,
)
from conan.tools.gnu import AutotoolsToolchain
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


def _prepare_autotools_env():
    """The installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that do not exist in this environment.  Point the
    env vars at whatever is actually on PATH."""
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
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its temp dir."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _c_str(v):
    """Escape a value as a C double-quoted string literal."""
    return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _find_real_clang(cc):
    """The OHOS SDK 'clang' on PATH is a /bin/sh wrapper script; conan's
    subprocess domain cannot execute scripts (SELinux).  Resolve the real
    clang-<ver> ELF binary the wrapper execs."""
    candidates = []

    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _collect(d):
        try:
            names = os.listdir(d)
        except OSError:
            return
        for name in names:
            if (name.startswith("clang-") and name != "clang"
                    and name[6:].isdigit()):
                cand = os.path.join(d, name)
                if _is_elf(cand):
                    candidates.append(cand)

    if cc and os.path.isfile(cc):
        try:
            with open(cc, "rb") as f:
                if f.read(2) != b"#!":
                    return cc  # already a real binary
        except OSError:
            pass
        real = os.path.realpath(cc)
        _collect(os.path.dirname(real))

    # Fallbacks: known OHOS SDK layout and common tool dirs
    for d in (os.path.dirname(cc or ""),
              "/data/service/hnp/bin",
              "/data/service/hnp/ohos-sdk.org"):
        if d:
            _collect(d)
    if not candidates:
        import glob
        for g in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang-[0-9]*",
                  "/data/app/bin/clang-[0-9]*"):
            for cand in sorted(glob.glob(g)):
                if _is_elf(cand):
                    candidates.append(cand)
    if candidates:
        # prefer the highest version
        return sorted(candidates)[-1]
    return cc

def _stage_clang(conanfile):
    """Resolve the real OHOS SDK clang-<N> ELF binary.  The SDK copy lives in
    the hnp_file SELinux context and is exec-able from the build domain,
    whereas copies staged under appdat/hmdfs mounts fail to exec (OHOS loader
    restriction on large ELF binaries outside hnp).  So use the SDK path."""
    staged = os.environ.get("_OHOS_REAL_CC", "")
    if staged and os.path.isfile(staged):
        return staged
    ccs = conanfile.conf.get("tools.build:compiler_executables", default={}) or {}
    real = _find_real_clang(ccs.get("c") or "")
    if real and os.path.isfile(real):
        os.environ["_OHOS_REAL_CC"] = real
    return real


def _fix_compiler_env(conanfile):
    """Patch the generated conanbuild toolchain env so CC/CXX point at the
    staged real clang-<N> ELF binary instead of the /bin/sh wrapper scripts
    (which conan's subprocess domain cannot execute on OHOS)."""
    gens = conanfile.generators_folder
    sh = os.path.join(gens, "conanautotoolstoolchain.sh")
    if not os.path.isfile(sh):
        return
    data = open(sh, encoding="utf-8").read()
    staged = _stage_clang(conanfile)
    if staged:
        data = data.replace('export CC="/data/service/hnp/bin/clang"',
                            'export CC="' + staged + '"')
        data = data.replace('export CXX="/data/service/hnp/bin/clang++"',
                            'export CXX="' + staged + '"')
    open(sh, "w", encoding="utf-8").write(data)


def _patch_conanbuild_env(conanfile, launcher_dir, ltpkg):
    """Patch the generated conanbuild env files so the AUTOMAKE / ACLOCAL /
    LIBTOOLIZE env vars (which autoreconf prefers over PATH) and _lt_pkgdatadir
    point at the staged ELF launchers / fake pkgdatadir, and the launcher dir
    is on PATH.  The conan cache tool scripts cannot be exec'd on OHOS."""
    gens = conanfile.generators_folder
    for fname in ("conanbuildenv-release-armv8.sh",):
        path = os.path.join(gens, fname)
        if not os.path.isfile(path):
            continue
        data = open(path, encoding="utf-8").read()
        data = data.replace(
            'export AUTOMAKE="/storage/Users/currentUser/.conan2/p/autom3efab95d532f9/p/bin/automake"',
            'export AUTOMAKE="' + os.path.join(launcher_dir, "automake") + '"')
        data = data.replace(
            'export ACLOCAL="/storage/Users/currentUser/.conan2/p/autom3efab95d532f9/p/bin/aclocal"',
            'export ACLOCAL="' + os.path.join(launcher_dir, "aclocal") + '"')
        data = data.replace(
            'export LIBTOOLIZE="/storage/Users/currentUser/.conan2/p/libto9be71649e7cec/p/bin/libtoolize"',
            'export LIBTOOLIZE="' + os.path.join(launcher_dir, "libtoolize") + '"')
        # _lt_pkgdatadir -> fake tree we staged
        data = data.replace(
            'export _lt_pkgdatadir="/storage/Users/currentUser/.conan2/p/libto9be71649e7cec/p/share/libtool-conan"',
            'export _lt_pkgdatadir="' + ltpkg + '"')
        # launcher dir first on PATH
        data = data.replace(
            'export PATH="' + '/data/service/hnp/bin',
            'export PATH="' + launcher_dir + ':' + '/data/service/hnp/bin')
        open(path, "w", encoding="utf-8").write(data)


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
    cc = staged
    out = os.path.join(launcher_dir, name)
    cmd = [cc, "-o", out, src]
    conanfile.run(" ".join(cmd), env="conanbuild", cwd=conanfile.build_folder)


def _prepare_autotools_tools(conanfile):
    """Stage ELF launchers for automake/aclocal/libtoolize/libtool and the
    fake libtool pkgdatadir, and prepend the launcher dir to PATH."""
    launcher_dir = os.path.join(conanfile.build_folder, "autotools-launchers")
    os.makedirs(launcher_dir, exist_ok=True)

    autom = conanfile.dependencies.build["automake"].package_folder
    libt = conanfile.dependencies.build["libtool"].package_folder

    perl = shutil.which("perl") or "/data/service/hnp/bin/perl"
    bash = shutil.which("bash") or "/data/service/hnp/bin/bash"

    # Ensure the real clang ELF is staged (used by launcher compile + build)
    _stage_clang(conanfile)

    # automake: perl -I <modpath> <real> --libdir=<share/automake-1.18> "$@"
    _compile_launcher(
        conanfile, launcher_dir, "automake", perl,
        os.path.join(autom, "bin", ".automake-real"),
        {"modpath": os.path.join(autom, "share", "automake-1.18"),
         "fixed1": "--libdir=" + os.path.join(autom, "share", "automake-1.18")})
    # aclocal: also add the libtool m4 dir via -I so LT_INIT is found
    _compile_launcher(
        conanfile, launcher_dir, "aclocal", perl,
        os.path.join(autom, "bin", ".aclocal-real"),
        {"modpath": os.path.join(autom, "share", "automake-1.18"),
         "fixed1": "--automake-acdir=" + os.path.join(autom, "share", "aclocal-1.18"),
         "fixed2": "--system-acdir=" + os.path.join(autom, "share", "aclocal"),
         "fixed3": "-I" + os.path.join(libt, "share", "aclocal")})

    # fake libtool pkgdatadir (build-aux + m4 + libltdl) for libtoolize.
    # Stage under $TMPDIR: the HMDFS build-folder tree breaks `cd`/`ls`
    # inside libtoolize's func_nonemptydir_p check (getcwd EPERM).
    ltpkg = os.path.join(
        os.environ.get("TMPDIR", "/tmp"),
        "opml-ltpkg-" + os.path.basename(conanfile.build_folder))
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
    # non-hidden file: libtoolize's func_nonemptydir_p uses `ls` (no -a),
    # so a dotfile would be invisible and the check would fail
    with open(os.path.join(ltpkg, "libltdl", "keep.txt"), "w") as f:
        f.write("x\n")
    os.environ["_lt_pkgdatadir"] = ltpkg

    # libtoolize / libtool: shell scripts -> launcher through bash
    _compile_launcher(conanfile, launcher_dir, "libtoolize", bash,
                      os.path.join(libt, "bin", "libtoolize"), {})
    _compile_launcher(conanfile, launcher_dir, "libtool", bash,
                      os.path.join(libt, "bin", "libtool"), {})

    # prepend launchers to PATH (and versioned names for automake/aclocal)
    for name in ("automake-1.18", "aclocal-1.18"):
        base = name.replace("-1.18", "")
        try:
            os.symlink(base, os.path.join(launcher_dir, name))
        except OSError:
            shutil.copy2(os.path.join(launcher_dir, base), os.path.join(launcher_dir, name))
    os.environ["PATH"] = launcher_dir + os.pathsep + os.environ.get("PATH", "")
    _patch_conanbuild_env(conanfile, launcher_dir, ltpkg)


class AbiwordPluginOpmlConan(ConanFile):
    name = "abiword-plugin-opml"
    version = "3.0.8"
    description = "AbiWord OPML (.opml) import plugin"
    license = "GPL-2.0-or-later"
    homepage = "https://www.abisource.com/"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # compat/ (AbiWord shim) and tests/ are source files, not patches:
        # toybox patch --dry-run on OHOS applies new-file patches for real
        # (pollutes orig dir and breaks the patch pipeline).  Exporting them
        # keeps the patch set limited to modified-file diffs (Makefile.am,
        # configure.ac).
        copy(self, "*", src=os.path.join(self.recipe_folder, "compat"),
             dst=os.path.join(self.export_sources_folder, "compat"))
        copy(self, "*", src=os.path.join(self.recipe_folder, "tests"),
             dst=os.path.join(self.export_sources_folder, "tests"))

    def requirements(self):
        # dependency-free: the OPML plugin parses XML via AbiWord's own
        # IE_Imp_XML (not libxml2); AbiWord core / libgsf APIs are provided
        # by the compat shim embedded in the module.
        pass

    def build_requirements(self):
        # The git archive ships no `configure`, so build() must run
        # `autoreconf -fi` to bootstrap.  The build host lacks
        # automake/aclocal/libtoolize on PATH, so pull them in as
        # tool_requires (same approach as abiword-plugin-clarisworks).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "abiword-plugin-opml is only supported on Linux/OHOS, "
                "not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        # export sources (patches/, compat/, tests/) are auto-merged into the
        # source folder by conan before source() runs.
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS"),
        # so pass the triplet explicitly (config.sub supports *-linux-ohos);
        # same approach as abiword-plugin-clarisworks.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # keep the toolchain configure args for build() (configure is run
        # through `bash` there because the script cannot be exec'd on OHOS)
        self._my_configure_args = list(tc.configure_args)
        tc.generate()
        _fix_compiler_env(self)

    def build(self):
        _prepare_autotools_env()
        _prepare_autotools_tools(self)
        # The git archive ships no `configure`: generate one from the
        # minimal configure.ac applied by the patches (run in source folder).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        # configure is a /bin/sh script on an HMDFS mount; OHOS SELinux
        # blocks shebang-based script exec from this domain, so run it
        # explicitly through bash (same effect).  In-source build: keep
        # everything under the source folder.
        cfg_args = " ".join(getattr(self, "_my_configure_args", []))
        self.run("bash ./configure " + cfg_args,
                 cwd=self.source_folder, env="conanbuild")
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")
        # L1: run the end-to-end plugin test (check-local drives the real
        # ELF test binary; the plugin module is located via LD_LIBRARY_PATH)
        self.run("make check -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # in-source build: install from the source folder with DESTDIR
        self.run("make install DESTDIR=%s" % self.package_folder,
                 cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        # dlopen-based plugin module: consumers never link against it, but
        # they need to locate it in lib/abiword-3.0/plugins/
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/abiword-3.0/plugins"]
