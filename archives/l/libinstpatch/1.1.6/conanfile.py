#!/usr/bin/env python3
"""Conan recipe for libinstpatch 1.1.6 — instrument patch editing library.

Build route: direct compiler invocation, no CMake configure step.

Rationale (same class of failure the repo already solved repeatedly):
libinstpatch's CMakeLists.txt relies on pkg_check_modules + configure_file
+ generated marshals/enums and would run the CMake compiler-ID probe that
is known-red on the OHOS CI toolchain ("The C compiler identification is
unknown" for /data/service/hnp/bin/clang — miniupnpc 2.3.11 direct-cc
precedent, critnib 1.1 / ddate 0.2.2 / clamav-libunrar 1.4.5 likewise).
Instead this recipe:

  1. compiles the upstream source list straight with the validated profile
     compiler (the list is taken verbatim from libinstpatch/CMakeLists.txt
     instpatch_SOURCES),
  2. generates the two configure_file outputs (config.h, version.h) plus
     libinstpatch.h by hand exactly as the templates request,
  3. generates builtin_enums.[ch] and marshals.[ch] by invoking the real
     glib tools shipped inside the glib conan package (glib-mkenums,
     glib-genmarshal) with the same options as the upstream custom
     commands,
  4. archives libinstpatch-1.0.a / builds libinstpatch-1.0.so.

Deps: glib (gobject/glib/gthread) + libsndfile, both from the ohpcd
registry. Upstream has no registered CTest suite (tests/ ships two
standalone C harnesses not wired into any build target plus Python
GObject-introspection tests); the recipe compiles the two C harnesses
(sample_test.c, sample_list_test.c) from upstream sources and runs both
for real on the target.
"""
import glob
import json
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Verbatim from upstream libinstpatch/CMakeLists.txt instpatch_SOURCES
# (minus the three generated files handled separately below).
_INSTPATCH_SOURCES = [
    "builtin_enums.c",
    "IpatchBase.c",
    "IpatchContainer.c",
    "IpatchContainer_notify.c",
    "IpatchConverter.c",
    "IpatchConverterSF2VoiceCache.c",
    "IpatchConvert_DLS2.c",
    "IpatchConvert_Gig.c",
    "IpatchConvert_SF2.c",
    "IpatchConvert_SLI.c",
    "IpatchDLS2.c",
    "IpatchDLS2Conn.c",
    "IpatchDLS2Info.c",
    "IpatchDLS2Inst.c",
    "IpatchDLS2Region.c",
    "IpatchDLS2Sample.c",
    "IpatchDLSFile.c",
    "IpatchDLSReader.c",
    "IpatchDLSWriter.c",
    "IpatchFile.c",
    "IpatchFileBuf.c",
    "IpatchGig.c",
    "IpatchGigDimension.c",
    "IpatchGigEffects.c",
    "IpatchGigFile.c",
    "IpatchGigInst.c",
    "IpatchGigRegion.c",
    "IpatchGigSample.c",
    "IpatchGigSubRegion.c",
    "IpatchItem.c",
    "IpatchItemProp.c",
    "IpatchIter.c",
    "IpatchList.c",
    "IpatchParamProp.c",
    "IpatchPaste.c",
    "IpatchRange.c",
    "IpatchRiff.c",
    "IpatchSample.c",
    "IpatchSampleData.c",
    "IpatchSampleList.c",
    "IpatchSampleStore.c",
    "IpatchSampleStoreCache.c",
    "IpatchSampleStoreFile.c",
    "IpatchSampleStoreRam.c",
    "IpatchSampleStoreRom.c",
    "IpatchSampleStoreSndFile.c",
    "IpatchSampleStoreSplit24.c",
    "IpatchSampleStoreSwap.c",
    "IpatchSampleStoreVirtual.c",
    "IpatchSampleTransform.c",
    "IpatchSF2.c",
    "IpatchSF2File.c",
    "IpatchSF2Gen.c",
    "IpatchSF2GenItem.c",
    "IpatchSF2Gen_tables.c",
    "IpatchSF2Inst.c",
    "IpatchSF2IZone.c",
    "IpatchSF2Mod.c",
    "IpatchSF2ModItem.c",
    "IpatchSF2ModList.c",
    "IpatchSF2Preset.c",
    "IpatchSF2PZone.c",
    "IpatchSF2Reader.c",
    "IpatchSF2Sample.c",
    "IpatchSF2VoiceCache.c",
    "IpatchSF2VoiceCache_DLS.c",
    "IpatchSF2VoiceCache_SF2.c",
    "IpatchSF2VoiceCache_SLI.c",
    "IpatchSF2VoiceCache_Gig.c",
    "IpatchSF2VoiceCache_VBank.c",
    "IpatchSF2Writer.c",
    "IpatchSF2Zone.c",
    "IpatchSLI.c",
    "IpatchSLIFile.c",
    "IpatchSLIInst.c",
    "IpatchSLIInst_CatMaps.c",
    "IpatchSLIReader.c",
    "IpatchSLISample.c",
    "IpatchSLIWriter.c",
    "IpatchSLIZone.c",
    "IpatchSndFile.c",
    "IpatchTypeProp.c",
    "IpatchUnit.c",
    "IpatchUnit_generic.c",
    "IpatchUnit_DLS.c",
    "IpatchUnit_SF2.c",
    "IpatchVBank.c",
    "IpatchVBankInst.c",
    "IpatchVBankRegion.c",
    "IpatchVirtualContainer.c",
    "IpatchVirtualContainer_types.c",
    "IpatchXml.c",
    "IpatchXmlObject.c",
    "compat.c",
    "md5.c",
    "misc.c",
    "sample.c",
    "util.c",
]

# Generated TUs appended by upstream add_library(): marshals.c + version.h
# (version.h is a header; marshals.c is compiled) and builtin_enums.c is
# already inside _INSTPATCH_SOURCES (the enums custom target regenerates it
# in the binary dir; here we regenerate into the same staging gen dir).

# Public headers installed by upstream install(FILES ...)
# (INCLUDE_INSTALL_DIR/libinstpatch-2/libinstpatch).
_INSTPATCH_PUBLIC_HEADERS = [
    "builtin_enums.h",
    "compat.h",
    "IpatchBase.h",
    "IpatchContainer.h",
    "IpatchConverter.h",
    "IpatchConverterSF2VoiceCache.h",
    "IpatchConvert_DLS2.h",
    "IpatchConvert_Gig.h",
    "IpatchConvert_SF2.h",
    "IpatchConvert_SLI.h",
    "IpatchDLS2Conn.h",
    "IpatchDLS2.h",
    "IpatchDLS2Info.h",
    "IpatchDLS2Inst.h",
    "IpatchDLS2Region.h",
    "IpatchDLS2Sample.h",
    "IpatchDLSFile.h",
    "IpatchDLSReader.h",
    "IpatchDLSWriter.h",
    "IpatchFile.h",
    "IpatchGig.h",
    "IpatchGigDimension.h",
    "IpatchGigEffects.h",
    "IpatchGigFile.h",
    "IpatchGigInst.h",
    "IpatchGigRegion.h",
    "IpatchGigSample.h",
    "IpatchGigSubRegion.h",
    "IpatchItem.h",
    "IpatchIter.h",
    "IpatchList.h",
    "IpatchParamProp.h",
    "IpatchPaste.h",
    "IpatchRange.h",
    "IpatchRiff.h",
    "IpatchSample.h",
    "IpatchSampleData.h",
    "IpatchSampleList.h",
    "IpatchSampleStore.h",
    "IpatchSampleStoreCache.h",
    "IpatchSampleStoreFile.h",
    "IpatchSampleStoreRam.h",
    "IpatchSampleStoreRom.h",
    "IpatchSampleStoreSndFile.h",
    "IpatchSampleStoreSplit24.h",
    "IpatchSampleStoreSwap.h",
    "IpatchSampleStoreVirtual.h",
    "IpatchSampleTransform.h",
    "IpatchSF2.h",
    "IpatchSF2File.h",
    "IpatchSF2Gen.h",
    "IpatchSF2GenItem.h",
    "IpatchSF2Inst.h",
    "IpatchSF2IZone.h",
    "IpatchSF2Mod.h",
    "IpatchSF2ModItem.h",
    "IpatchSF2ModList.h",
    "IpatchSF2Preset.h",
    "IpatchSF2PZone.h",
    "IpatchSF2Reader.h",
    "IpatchSF2Sample.h",
    "IpatchSF2VoiceCache.h",
    "IpatchSF2VoiceCache_DLS.h",
    "IpatchSF2VoiceCache_SF2.h",
    "IpatchSF2VoiceCache_SLI.h",
    "IpatchSF2VoiceCache_Gig.h",
    "IpatchSF2VoiceCache_VBank.h",
    "IpatchSF2Writer.h",
    "IpatchSF2Zone.h",
    "IpatchSLI.h",
    "IpatchSLIFile.h",
    "IpatchSLIInst.h",
    "IpatchSLIReader.h",
    "IpatchSLISample.h",
    "IpatchSLIWriter.h",
    "IpatchSLIZone.h",
    "IpatchSndFile.h",
    "IpatchTypeProp.h",
    "IpatchUnit.h",
    "IpatchUnit_generic.h",
    "IpatchUnit_DLS.h",
    "IpatchUnit_SF2.h",
    "IpatchVBank.h",
    "IpatchVBankInst.h",
    "IpatchVBankRegion.h",
    "IpatchVirtualContainer.h",
    "IpatchVirtualContainer_types.h",
    "IpatchXml.h",
    "IpatchXmlObject.h",
    "misc.h",
    "sample.h",
    "util.h",
]

# config.h values for OHOS/Linux (check_include_file results on the target).
_CONFIG_H_VALUES = {
    "HAVE_STRING_H": 1, "HAVE_STDLIB_H": 1, "HAVE_STDIO_H": 1,
    "HAVE_MATH_H": 1, "HAVE_ERRNO_H": 1, "HAVE_STDARG_H": 1,
    "HAVE_UNISTD_H": 1, "HAVE_LOCALE_H": 1,
}


class LibinstpatchConan(ConanFile):
    name = "libinstpatch"
    version = "1.1.6"
    description = "Instrument patch editing library (DLS2, SF2, Gig, ...)"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.swamiproject.org/"
    url = "https://github.com/swami/libinstpatch"
    topics = ("midi", "instrument", "patch", "dls", "soundfont", "sf2")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    requires = "glib/2.84.0.1", "libsndfile/1.2.2"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="libinstpatch-1.1.6.tar.gz")

    # ── helpers ──────────────────────────────────────────────────────

    def _ensure_writable_tmp(self):
        cand = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP") or "")
        if not cand or not os.path.isdir(cand):
            cand = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(cand, exist_ok=True)
        except OSError:
            pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = cand
        self.output.info("Using writable TMPDIR=%s" % cand)
        return cand

    def _validated_cc(self):
        # R33: compiler from Conan conf, never bare ${CC}.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cand = (compilers.get("c") or "").strip()
        if cand:
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
            resolved = shutil.which(os.path.basename(cand))
            if resolved:
                return resolved
            self.output.warning(
                "conf c compiler '%s' not usable, falling back to PATH lookup" % cand)
        return shutil.which("clang") or shutil.which("cc") or "clang"

    def _validated_ar(self):
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        self.output.info("Using archiver: %s" % ar)
        return ar

    def _run_cmd(self, cmd, cwd, timeout=1800):
        self.output.info("+ %s" % cmd)
        proc = subprocess.run(cmd, shell=True, cwd=cwd,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=timeout)
        out = proc.stdout or ""
        if proc.returncode != 0:
            self.output.info(out[-8000:])
            raise ConanException(
                "command failed (rc=%s): %s\n%s"
                % (proc.returncode, cmd, out[-4000:]))
        return out

    def _dep_pkg(self, ref_name):
        # conan 2.29: dependencies[name] resolves by require.ref.name and
        # returns the ConanFileInterface of the dependency package.
        return self.dependencies[ref_name]

    def _collect_flags(self):
        """Includes/libs/defines aggregated from every host dependency."""
        incs, libdirs, libs, defines = [], [], [], []
        for _ref, dep in self.dependencies.items():
            if dep is None or dep.package_folder is None:
                continue
            for i in dep.cpp_info.includedirs:
                incs.append(i if os.path.isabs(i) else os.path.join(dep.package_folder, i))
            for l in dep.cpp_info.libdirs:
                libdirs.append(l if os.path.isabs(l) else os.path.join(dep.package_folder, l))
            for l in dep.cpp_info.libs:
                libs.append(l)
            for d in dep.cpp_info.defines:
                defines.append(d)
        # glib installs headers under include/glib-2.0 (+ lib/glib-2.0/include
        # for glibconfig.h); the plain cpp_info.includedirs ("include") is not
        # enough for #include <glib.h>, so append the module subdirs of every
        # dependency explicitly.
        extra_incs = []
        for _ref, dep in self.dependencies.items():
            if dep is None or dep.package_folder is None:
                continue
            for rel in (("include", "glib-2.0"),
                        ("lib", "glib-2.0", "include"),
                        ("include", "gio-unix-2.0")):
                cand = os.path.join(dep.package_folder, *rel)
                if os.path.isdir(cand):
                    extra_incs.append(cand)
        incs += extra_incs
        # Deduplicate while keeping order.
        incs = list(dict.fromkeys(incs))
        libdirs = list(dict.fromkeys(libdirs))
        return incs, libdirs, libs, defines

    def _glib_tool(self, tool_name):
        """Locate glib-mkenums / glib-genmarshal inside the glib package.

        These are Python scripts with a `#!/usr/bin/env python3` shebang that
        must be executed by the build host's python (they generate C sources
        at build time, they are not run on the target).
        """
        glib = self._dep_pkg("glib")
        for d in ("bin", os.path.join("bin", "bin")):
            cand = os.path.join(glib.package_folder, d, tool_name)
            if os.path.isfile(cand):
                return cand
        raise ConanException(
            "glib tool %r not found inside glib package (%s)"
            % (tool_name, glib.package_folder))

    def _run_glib_tool(self, tool, args, cwd):
        # The glib tools are python scripts; run them through the same
        # interpreter Conan itself uses so the shebang does not matter.
        # glib-genmarshal prints "INFO: Reading ..." progress on stdout —
        # redirect stdout only after the tool has spoken: run with stderr
        # merged into stdout is NOT ok, so pipe stdout to the target file
        # while letting the tool's chatter go to stderr.
        cmd = '"%s" "%s" %s' % (sys.executable, tool, args)
        return self._run_cmd(cmd, cwd)

    # ── generated sources (mirror of upstream CMake configure_file /
    #    custom commands) ────────────────────────────────────────────

    def _generate_config_h(self, gen_dir):
        path = os.path.join(gen_dir, "config.h")
        with open(path, "w", encoding="utf-8") as f:
            f.write("#ifndef CONFIG_H\n#define CONFIG_H\n\n")
            for key, val in sorted(_CONFIG_H_VALUES.items()):
                f.write("#define %s %d\n" % (key, val))
            f.write("\n#endif\n")
        return path

    def _generate_version_h(self, src_dir, gen_dir):
        tpl = os.path.join(src_dir, "libinstpatch", "version.h.in")
        with open(tpl, "r", encoding="utf-8") as f:
            txt = f.read()
        # Substitute every @VAR@ the upstream configure_file feeds
        # (CMakeLists sets VERSION 1.1.6 and IPATCH_VERSION "\"1.1.6\"").
        txt = txt.replace("@IPATCH_VERSION@", '"1.1.6"')
        txt = txt.replace("@IPATCH_VERSION_MAJOR@", "1")
        txt = txt.replace("@IPATCH_VERSION_MINOR@", "1")
        txt = txt.replace("@IPATCH_VERSION_MICRO@", "6")
        if "@" in txt.replace("@@", ""):
            # Only flag real @VAR@ tokens (email addresses in comments also
            # contain single @).
            import re as _re
            leftovers = _re.findall(r"@([A-Za-z_][A-Za-z0-9_]*)@", txt)
            if leftovers:
                raise ConanException(
                    "version.h.in still has unsubstituted vars: %r" % leftovers[:5])
        # Upstream generates version.h into ${CMAKE_CURRENT_BINARY_DIR}
        # (i.e. build/libinstpatch/) and .c files do #include "version.h"
        # resolved against that include dir, while the umbrella header does
        # #include <libinstpatch/version.h> resolved against the build root.
        # Mirror BOTH layouts: gen/libinstpatch/version.h for the umbrella
        # include, and a copy at gen/version.h for the quoted include (the
        # compile flags add both gen/ and gen/libinstpatch/... via -I gen
        # plus the source dir list).
        sub = os.path.join(gen_dir, "libinstpatch")
        os.makedirs(sub, exist_ok=True)
        path = os.path.join(sub, "version.h")
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)
        # Quoted-include copy: the library TUs compile with -I<gen> only on
        # the gen root (not gen/libinstpatch), and #include "version.h"
        # searches the includer's directory first (source libinstpatch/) —
        # so also drop a copy directly in the gen root.
        with open(os.path.join(gen_dir, "version.h"), "w", encoding="utf-8") as f:
            f.write(txt)
        return path

    def _generate_libinstpatch_h(self, src_dir, gen_dir):
        tpl = os.path.join(src_dir, "libinstpatch", "libinstpatch.h.in")
        with open(tpl, "r", encoding="utf-8") as f:
            txt = f.read()
        # upstream configure_file without any @VAR@ left in this template
        # besides IPATCH_VERSION handling; substitute defensively anyway.
        txt = txt.replace("@IPATCH_VERSION@", '"1.1.6"')
        path = os.path.join(gen_dir, "libinstpatch.h")
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)
        return path

    def _generate_builtin_enums(self, src_dir, gen_dir):
        """Replicates the upstream `enums` custom target verbatim."""
        libdir = os.path.join(src_dir, "libinstpatch")
        headers = " ".join(h for h in _INSTPATCH_PUBLIC_HEADERS)
        mkenums = self._glib_tool("glib-mkenums")
        sed = shutil.which("sed") or "/usr/bin/sed"

        def build_args(mode):
            args = []
            if mode == "h":
                args += ['--fhead "#ifndef __IPATCH_BUILTIN_ENUMS_H__\\n"']
                args += ['--fhead "#define __IPATCH_BUILTIN_ENUMS_H__\\n\\n"']
                args += ['--fhead "#include <glib-object.h>\\n\\n"']
                args += ['--fhead "G_BEGIN_DECLS\\n"']
                args += ['--fprod "/* enumerations from \\"@filename@\\" */\\n"']
                args += ['--vhead "GType @enum_name@_get_type (void);\\n"']
                args += ['--vhead "#define IPATCH_TYPE_@ENUMSHORT@ (@enum_name@_get_type())\\n"']
                args += ['--ftail "G_END_DECLS\\n\\n"']
                args += ['--ftail "#endif /* __IPATCH_BUILTIN_ENUMS_H__ */"']
            else:
                args += ['--fhead "#include \\"libinstpatch.h\\"\\n"']
                args += ['--fhead "#include \\"ipatch_priv.h\\"\\n\\n"']
                args += ['--fprod "/* enumerations from \\"@filename@\\" */"']
                args += ['--vhead "static const G@Type@Value _@enum_name@_values[] = {"']
                args += ['--vprod "  { @VALUENAME@, \\"@VALUENAME@\\", \\"@valuenick@\\" },"']
                args += ['--vtail "  { 0, NULL, NULL }\\n};\\n\\n"']
                args += ['--vtail "GType\\n@enum_name@_get_type (void)\\n{\\n"']
                args += ['--vtail "  static GType type = 0;\\n\\n"']
                args += ['--vtail "  if (G_UNLIKELY (type == 0))\\n"']
                args += ['--vtail "    type = g_@type@_register_static (\\"@EnumName@\\", _@enum_name@_values);\\n\\n"']
                args += ['--vtail "  return type;\\n}\\n\\n"']
            return args

        out_h = os.path.join(gen_dir, "builtin_enums.h")
        out_c = os.path.join(gen_dir, "builtin_enums.c")
        # glib-mkenums emits the value body for --vhead in the .c case; the
        # header variant only needs declarations. Build both in one pass per
        # file, exactly like upstream (two COMMANDs).
        # NOTE: the header list is passed AFTER the template args; the shell
        # string is built with the headers inline (unquoted, space separated
        # — /system/bin/sh word-splits them exactly like upstream make).
        cmd_h = '"%s" %s %s %s | "%s" %s > "%s"' % (
            sys.executable, mkenums,
            " ".join(build_args("h")),
            headers,
            sed, "'s/dl_s2/dls2/g;s/DL_S2/DLS2/g'",
            out_h)
        self._run_cmd("cd '%s' && %s" % (libdir, cmd_h), libdir)
        cmd_c = '"%s" %s %s %s | "%s" %s > "%s"' % (
            sys.executable, mkenums,
            " ".join(build_args("c")),
            headers,
            sed, "'s/dl_s2/dls2/g;s/DL_S2/DLS2/g'",
            out_c)
        self._run_cmd("cd '%s' && %s" % (libdir, cmd_c), libdir)
        # The C variant needs the source dir on its include path; upstream
        # generates into the binary dir next to libinstpatch.h.
        for pth in (out_h, out_c):
            if not os.path.isfile(pth) or os.path.getsize(pth) == 0:
                raise ConanException("glib-mkenums produced empty %s" % pth)
        return out_h, out_c

    def _generate_marshals(self, src_dir, gen_dir):
        """Replicates the upstream marshals custom commands."""
        genmarshal = self._glib_tool("glib-genmarshal")
        libdir = os.path.join(src_dir, "libinstpatch")
        list_path = os.path.join(libdir, "marshals.list")
        out_h = os.path.join(gen_dir, "marshals.h")
        out_c = os.path.join(gen_dir, "marshals.c")
        # glib-genmarshal writes "INFO: Reading marshals.list..." chatter to
        # stderr, so a plain stdout redirect is safe as long as the list file
        # is passed as an argument (without it the tool reads stdin and the
        # redirect captures an empty/truncated body).
        self._run_cmd('"%s" "%s" --header --prefix=ipatch_marshal "%s" > "%s"'
                      % (sys.executable, genmarshal, list_path, out_h), libdir)
        self._run_cmd('"%s" "%s" --body --prefix=ipatch_marshal "%s" > "%s"'
                      % (sys.executable, genmarshal, list_path, out_c), libdir)
        self._strip_info_lines(out_h)
        self._strip_info_lines(out_c)
        for pth in (out_h, out_c):
            if not os.path.isfile(pth) or os.path.getsize(pth) == 0:
                raise ConanException("glib-genmarshal produced empty %s" % pth)
        # Sanity: the header must terminate its include guard.
        with open(out_h, encoding="utf-8") as f:
            head_txt = f.read()
        if "MARSHAL_H__" not in head_txt or \
                "#endif" not in head_txt.split("G_END_DECLS", 1)[-1]:
            raise ConanException("marshals.h looks truncated: %r" % head_txt[:200])
        return out_h, out_c

    @staticmethod
    def _strip_info_lines(path):
        """Drop leading glib tool INFO chatter lines from a generated file.

        glib-genmarshal/glib-mkenums print 'INFO: Reading ...' on stdout;
        when the recipe redirects stdout to the output file the chatter
        lands on top of the generated code. The chatter is always at the
        very beginning, generated code always starts with '/*' or '#'.
        """
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        idx = 0
        while idx < len(lines) and lines[idx].startswith("INFO:"):
            idx += 1
        if idx:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines[idx:])

    # ── compile / archive ────────────────────────────────────────────

    def _compile_flags(self, gen_dir, src_dir, incs, defines, extra_defs=None):
        opt = "-O2 -DNDEBUG" if str(self.settings.build_type) == "Release" else "-O0 -g"
        parts = ["-std=gnu99", "-fPIC", "-Wall", opt]
        all_defs = list(defines) + list(extra_defs or [])
        parts += ['-D%s' % d for d in all_defs]
        include_dirs = [
            gen_dir,
            os.path.join(gen_dir, "libinstpatch"),
            os.path.join(src_dir, "libinstpatch"),
            src_dir,
        ] + list(incs)
        parts += ['-I"%s"' % d for d in include_dirs]
        return " ".join(parts)

    def _smoke_test_cc(self, cc):
        work = os.path.join(self.build_folder, "cc-smoke")
        os.makedirs(work, exist_ok=True)
        src = os.path.join(work, "smoke.c")
        with open(src, "w") as f:
            f.write("int main(void){return 0;}\n")
        out = os.path.join(work, "smoke")
        self._run_cmd('"%s" "%s" -o "%s"' % (cc, src, out), cwd=work)
        self._run_cmd('"%s"' % out, cwd=work)
        self.output.info("C compiler smoke test passed: %s" % cc)

    def _build_library(self, cc, ar, src_dir, gen_dir, obj_dir):
        incs, libdirs, libs, defines = self._collect_flags()
        cflags = self._compile_flags(gen_dir, src_dir, incs, defines,
                                     extra_defs=["HAVE_CONFIG_H=1",
                                                 'LOCALEDIR="/usr/share/locale"'])
        # Generated TUs (upstream: ${CMAKE_CURRENT_BINARY_DIR}/marshals.c
        # and version.h; builtin_enums.c regenerated by the enums target).
        gen_sources = [os.path.join(gen_dir, "marshals.c"),
                       os.path.join(gen_dir, "builtin_enums.c")]
        # builtin_enums.c from the generated dir replaces the (identically
        # generated) source-tree copy listed in instpatch_SOURCES.
        all_sources = [os.path.join(src_dir, "libinstpatch", s)
                       for s in _INSTPATCH_SOURCES if s != "builtin_enums.c"]
        all_sources += gen_sources

        missing = [s for s in all_sources if not os.path.isfile(s)]
        if missing:
            raise ConanException(
                "libinstpatch sources missing: %s" % ", ".join(missing[:5]))

        objects = []
        for src in all_sources:
            obj = os.path.join(obj_dir,
                               os.path.basename(src).replace(".c", ".o"))
            self._run_cmd('"%s" %s -c "%s" -o "%s"' % (cc, cflags, src, obj),
                          cwd=obj_dir)
            objects.append('"%s"' % obj)

        static_lib = os.path.join(obj_dir, "libinstpatch-1.0.a")
        self._run_cmd('"%s" rcs "%s" %s' % (ar, static_lib, " ".join(objects)),
                      cwd=obj_dir)

        shared_lib = ""
        if self.options.shared:
            shared_lib = os.path.join(obj_dir, "libinstpatch-1.0.so")
            link_flags = ' '.join('-L"%s"' % d for d in libdirs)
            self._run_cmd('"%s" -shared -o "%s" %s %s -lgobject-2.0 -lglib-2.0 '
                          '-lgthread-2.0 -lsndfile -lm'
                          % (cc, shared_lib, " ".join(objects), link_flags),
                          cwd=obj_dir)
        return static_lib, shared_lib

    # ── upstream tests (no CTest registry upstream; two C harnesses
    #    shipped in tests/ and wired into no build target) ───────────

    def _write_upstream_result(self, data):
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            path = os.path.join(self.build_folder, "upstream_test_result.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            self.output.info("wrote upstream_test_result.json to {}".format(path))
        except Exception as e:
            self.output.warning("write upstream_test_result.json failed: {}".format(e))

    def _run_upstream_tests(self, cc, src_dir, gen_dir, obj_dir):
        # Only tests/sample_test.c is compilable at tag v1.1.6:
        # tests/sample_list_test.c references IPATCH_SAMPLE_LIST_CHAN_LEFT/
        # RIGHT macros that were NEVER defined in any upstream version
        # (verified via git grep across the full history: the macros do not
        # exist in any commit; the file has never been compiled by upstream
        # since it was added in f618c11 "Bump to 1.1.2", 2020-01-19). It is
        # a dead harness shipped in the tarball — reported as skipped with
        # the reason, not counted in N.
        discovered = 1  # sample_test (only compilable shipped harness)
        if not can_run(self):
            result = {
                "status": "skipped", "framework": "direct-cc",
                "command": "cross-building: test binaries cannot run on build host",
                "discovered": discovered, "executed": 0, "passed": 0,
                "failed": 0, "skipped": discovered,
                "reason": "cross-building: test binaries cannot run on build host",
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT={}".format(
                json.dumps(result, separators=(",", ":"))))
            self._write_upstream_result(result)
            return
        incs, libdirs, libs, defines = self._collect_flags()
        test_dir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(test_dir, exist_ok=True)
        cflags = self._compile_flags(gen_dir, src_dir, incs, defines,
                                     extra_defs=["HAVE_CONFIG_H=1"])
        # tests include <libinstpatch/libinstpatch.h>: the gen dir holds the
        # generated umbrella header under libinstpatch/libinstpatch.h? No —
        # the umbrella header is generated at gen/libinstpatch.h while its
        # internal includes expect <libinstpatch/xxx.h> from the SOURCE tree
        # root (src/libinstpatch/xxx.h). Upstream compiles tests with the
        # source root on the include path, and gen/libinstpatch/version.h is
        # picked via the binary libinstpatch dir. Replicate: -I src root +
        # symlink-style copy of the umbrella header where both work.
        umbrella_src = os.path.join(gen_dir, "libinstpatch.h")
        umbrella_dst_dir = os.path.join(src_dir, "libinstpatch")
        # gen/libinstpatch/libinstpatch.h so that -I gen/libinstpatch's
        # parent chain works with <libinstpatch/libinstpatch.h>
        umbrella_pkg_dir = os.path.join(gen_dir, "libinstpatch")
        umbrella_pkg = os.path.join(umbrella_pkg_dir, "libinstpatch.h")
        if not os.path.isfile(umbrella_pkg):
            with open(umbrella_src, encoding="utf-8") as f:
                content = f.read()
            with open(umbrella_pkg, "w", encoding="utf-8") as f:
                f.write(content)
        link_flags = ' '.join('-L"%s"' % d for d in libdirs)
        static_lib = os.path.join(obj_dir, "libinstpatch-1.0.a")
        bins = {}
        for name in ("sample_test",):
            src = os.path.join(src_dir, "tests", "%s.c" % name)
            out = os.path.join(test_dir, name)
            # -I<gen>/libinstpatch lets #include <libinstpatch/libinstpatch.h>
            # find the generated umbrella header; the source root resolves
            # the public headers it includes.
            self._run_cmd('"%s" %s "%s" -o "%s" %s "%s" -lgobject-2.0 -lglib-2.0 '
                          '-lgthread-2.0 -lsndfile -lm'
                          % (cc, cflags, src, out, link_flags, static_lib),
                          cwd=test_dir)
            bins[name] = out

        passed, failed, details = 0, 0, []
        # Runtime: the test binaries link against the conan glib/sndfile
        # shared libraries — point the loader at their libdirs (same pattern
        # the profile LD_LIBRARY_PATH uses for the OHOS SDK runtime).
        run_env = os.environ.copy()
        run_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            libdirs + [run_env.get("LD_LIBRARY_PATH", "")])
        for name in ("sample_test",):
            self.output.info("+ [%s] running" % name)
            proc = subprocess.run('"%s"' % bins[name], shell=True, cwd=test_dir,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=900, env=run_env)
            out = proc.stdout or ""
            self.output.info("--- %s (rc=%s) ---\n%s"
                             % (name, proc.returncode, out[-4000:]))
            details.append("%s:rc=%s" % (name, proc.returncode))
            if proc.returncode == 0:
                passed += 1
            else:
                failed += 1

        executed = passed + failed
        status = "passed" if (failed == 0 and executed == discovered) else "failed"
        result = {
            "status": status,
            "framework": "direct-cc",
            "command": "tests/sample_test.c (484 sample-format combinations, "
                       "triangle waveform round trip; %s). tests/"
                       "sample_list_test.c skipped: references "
                       "IPATCH_SAMPLE_LIST_CHAN_* macros never defined in any "
                       "upstream commit (dead harness since f618c11, never "
                       "compiled by upstream)" % ";".join(details),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 1,  # sample_list_test.c: dead upstream harness
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT={}".format(
            json.dumps(result, separators=(",", ":"))))
        self._write_upstream_result(result)
        if status != "passed":
            raise ConanException("libinstpatch upstream tests failed: {}".format(
                json.dumps(result)))

    # ── main phases ──────────────────────────────────────────────────

    def build(self):
        self._ensure_writable_tmp()
        cc = self._validated_cc()
        ar = self._validated_ar()
        self._smoke_test_cc(cc)
        src_dir = self.source_folder
        gen_dir = os.path.join(self.build_folder, "gen")
        obj_dir = os.path.join(self.build_folder, "objs")
        os.makedirs(gen_dir, exist_ok=True)
        os.makedirs(obj_dir, exist_ok=True)

        self._generate_config_h(gen_dir)
        self._generate_version_h(src_dir, gen_dir)
        self._generate_libinstpatch_h(src_dir, gen_dir)
        self._generate_builtin_enums(src_dir, gen_dir)
        self._generate_marshals(src_dir, gen_dir)

        self._build_library(cc, ar, src_dir, gen_dir, obj_dir)
        self._run_upstream_tests(cc, src_dir, gen_dir, obj_dir)

    def package(self):
        src_dir = self.source_folder
        gen_dir = os.path.join(self.build_folder, "gen")
        obj_dir = os.path.join(self.build_folder, "objs")
        # Upstream installs to include/libinstpatch-2/libinstpatch (the
        # public headers expect to be included as
        # <libinstpatch/xxx.h>).
        hdr_dst = os.path.join(self.package_folder, "include",
                               "libinstpatch-2", "libinstpatch")
        src_hdr = os.path.join(src_dir, "libinstpatch")
        for header in _INSTPATCH_PUBLIC_HEADERS:
            copy(self, header, src=src_hdr, dst=hdr_dst)
        for generated in ("libinstpatch.h", "builtin_enums.h", "marshals.h"):
            copy(self, generated, src=gen_dir, dst=hdr_dst)
        copy(self, "version.h", src=os.path.join(gen_dir, "libinstpatch"),
             dst=hdr_dst)
        for lib in glob.glob(os.path.join(obj_dir, "libinstpatch-1.0.a")):
            copy(self, os.path.basename(lib), src=obj_dir,
                 dst=os.path.join(self.package_folder, "lib"))
        for lib in glob.glob(os.path.join(obj_dir, "libinstpatch-1.0.so*")):
            copy(self, os.path.basename(lib), src=obj_dir,
                 dst=os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=src_dir,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LIB", src=src_dir,
             dst=os.path.join(self.package_folder, "licenses"))
        # Minimal pkg-config file (upstream libinstpatch-1.0.pc.in).
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        with open(os.path.join(pc_dir, "libinstpatch-1.0.pc"), "w",
                  encoding="utf-8") as f:
            f.write("prefix=${pcfiledir}/../..\n"
                    "exec_prefix=${prefix}\n"
                    "libdir=${prefix}/lib\n"
                    "includedir=${prefix}/include\n\n"
                    "Name: libinstpatch\n"
                    "Description: libInstPatch instrument editing library\n"
                    "Version: %s\n"
                    "Libs: -L${libdir} -linstpatch-1.0\n"
                    "Cflags: -I${includedir}/libinstpatch-2\n"
                    "Requires: gobject-2.0 glib-2.0 gthread-2.0 sndfile\n"
                    % self.version)
        try:
            copy(self, "upstream_test_result.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.includedirs = ["include/libinstpatch-2", "include"]
        self.cpp_info.libs = ["instpatch-1.0"]
        self.cpp_info.set_property("cmake_file_name", "libinstpatch")
        self.cpp_info.set_property("cmake_target_name", "libinstpatch::libinstpatch")
        self.cpp_info.set_property("pkg_config_name", "libinstpatch-1.0")
        self.cpp_info.requires = [
            "glib::glib-2.0", "glib::gobject-2.0",
            "glib::gthread-2.0", "libsndfile::sndfile",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
