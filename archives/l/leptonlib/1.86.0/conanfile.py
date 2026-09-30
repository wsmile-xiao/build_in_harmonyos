"""Leptonica 1.86.0, packaged as leptonlib for HarmonyOS PC."""

import os
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LeptonlibConan(ConanFile):
    name = "leptonlib"
    version = "1.86.0"
    description = "Leptonica image processing and analysis library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/DanBloomberg/leptonica"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Match the already-published libtiff and gnuplot zlib ABI closure.
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("giflib/5.2.2")
        self.requires("libtiff/4.7.0")
        self.requires("libwebp/1.6.0")
        self.requires("openjpeg/2.5.4")

    def build_requirements(self):
        # The upstream reg_wrapper runs plot-dependent tests only if a real
        # gnuplot is available. Keep the full declared test denominator.
        self.tool_requires("gnuplot/6.0.3.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("LEPTONLIB_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ValueError("LEPTONLIB_SOURCE_ARCHIVE must name a regular file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        # --disable-programs leaves check_PROGRAMS and TESTS intact.
        toolchain.configure_args.append("--disable-programs")
        toolchain.generate()
        AutotoolsDeps(self).generate()
        # Published .pc files contain stale absolute build prefixes; Conan's
        # generated metadata points at the selected package binaries instead.
        PkgConfigDeps(self).generate()
        for dependency, module, library, header_dir, header in (
            ("libwebp", "libwebpmux", "webpmux", "include", "webp/mux.h"),
            ("openjpeg", "libopenjp2", "openjp2", "include/openjpeg-2.5", "openjpeg.h"),
        ):
            package = Path(self.dependencies[dependency].package_folder)
            include = package / header_dir
            if not (package / "lib" / ("lib" + library + ".so")).is_file():
                raise ConanInvalidConfiguration("missing component library: " + module)
            if not (include / header).is_file():
                raise ConanInvalidConfiguration("missing component header: " + module)
            # These two upstream pkg-config component names are absent from
            # the Conan recipes. Bind them to verified package paths, not
            # the stale prefixes in the published .pc files.
            contents = (
                f"prefix={package}\n"
                "libdir=${prefix}/lib\n"
                f"includedir={include}\n\n"
                f"Name: {module}\n"
                f"Description: {module} from the selected Conan package\n"
                f"Version: {self.dependencies[dependency].ref.version}\n"
                f"Libs: -L${{libdir}} -l{library}\n"
                "Cflags: -I${includedir}\n"
            )
            Path(self.generators_folder, module + ".pc").write_text(
                contents, encoding="utf-8"
            )

    def _run_environment(self):
        environment = Environment()
        temporary = Path(self.build_folder, "leptonica-tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment.define("TMPDIR", str(temporary))
        environment.define("HOME", str(temporary))
        gnuplot = self.dependencies.build["gnuplot"].package_folder
        gnuplot_bin = Path(gnuplot, "bin")
        if not gnuplot_bin.is_dir():
            raise ConanInvalidConfiguration("gnuplot build tool has no bin directory")
        environment.prepend_path("PATH", str(gnuplot_bin))
        environment.define("PKG_CONFIG_LIBDIR", self.generators_folder)
        environment.define("PKG_CONFIG_PATH", self.generators_folder)
        for dependency in (*self.dependencies.host.values(),
                           *self.dependencies.build.values()):
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                directory = Path(libdir)
                if not directory.is_absolute():
                    directory = Path(dependency.package_folder, libdir)
                if directory.is_dir():
                    environment.prepend_path("LD_LIBRARY_PATH", str(directory))
        return environment

    def build(self):
        args = []
        if str(self.settings.os) == "OHOS":
            # OHOS libc does not publish open_memstream's buffer/size on
            # fclose alone.  These 21 upstream serializers all append a NUL
            # and then close; flush explicitly before the size adjustment.
            marker = "    fputc('\\0', fp);\n    fclose(fp);"
            patched = 0
            for path in Path(self.source_folder, "src").glob("*.c"):
                content = path.read_text(encoding="utf-8")
                uses = content.count("fp = open_memstream((char **)pdata, psize)")
                if not uses:
                    continue
                if content.count(marker) != uses:
                    raise ConanInvalidConfiguration(
                        "unexpected memory-stream serializer shape: " + path.name
                    )
                content = content.replace(
                    marker, "    fputc('\\0', fp);\n    fflush(fp);\n    fclose(fp);"
                )
                path.write_text(content, encoding="utf-8")
                patched += uses
            if patched != 21:
                raise ConanInvalidConfiguration(
                    "unexpected memory-stream serializer count: " + str(patched)
                )
            # tmpfile() ignores TMPDIR on this libc and attempts the
            # read-only system /tmp.  Multipage TIFF needs a seekable file,
            # so create an immediately unlinked one in our private TMPDIR.
            tiff = Path(self.source_folder, "src", "tiffio.c")
            tiff_source = tiff.read_text(encoding="utf-8")
            signature = "pixaWriteMemMultipageTiff(l_uint8  **pdata,"
            start = tiff_source.find(signature)
            end = tiff_source.find("\n\n/*!", start + len(signature))
            if start < 0 or end < 0:
                raise ConanInvalidConfiguration("multipage TIFF source shape changed")
            function = tiff_source[start:end]
            declaration = "PIX         *pix1;"
            old_temp = """#else
    if ((fp = tmpfile()) == NULL)
        return ERROR_INT("tmpfile stream not opened", __func__, 1);
#endif  /* _WIN32 */"""
            new_temp = """#else
    tempdir = getenv("TMPDIR");
    if (!tempdir || tempdir[0] != '/' ||
        snprintf(tempname, sizeof(tempname), "%s/lept-mtiff-XXXXXX", tempdir) >=
            (int)sizeof(tempname))
        return ERROR_INT("invalid TMPDIR", __func__, 1);
    tempfd = mkstemp(tempname);
    if (tempfd < 0)
        return ERROR_INT("private TIFF tempfile not opened", __func__, 1);
    unlink(tempname);
    fp = fdopen(tempfd, "w+b");
    if (!fp) {
        close(tempfd);
        return ERROR_INT("private TIFF stream not opened", __func__, 1);
    }
#endif  /* _WIN32 */"""
            if function.count(declaration) != 1 or function.count(old_temp) != 1:
                raise ConanInvalidConfiguration("multipage TIFF tempfile shape changed")
            function = function.replace(
                declaration, declaration +
                "\n#ifndef _WIN32\nconst char  *tempdir;\nchar         tempname[4096];\nint          tempfd;\n#endif",
                1,
            ).replace(old_temp, new_temp, 1)
            tiff.write_text(tiff_source[:start] + function + tiff_source[end:],
                            encoding="utf-8")
            # Upstream intentionally ignores TMPDIR on Unix, but OHOS /tmp
            # is read-only. Reuse its centralized /tmp path translation for
            # both library routines and the unchanged regression test paths.
            utils = Path(self.source_folder, "src", "utils2.c")
            source = utils.read_text(encoding="utf-8")
            old_macro = "#include <string.h>\n#include <stddef.h>\n#include \"allheaders.h\"\n\n#if defined(__APPLE__) || defined(_WIN32)\n/* Rewrite paths starting with /tmp for macOS, iOS and Windows. */"
            new_macro = "#include <string.h>\n#include <stdlib.h>\n#include <stddef.h>\n#include \"allheaders.h\"\n\n#if defined(__APPLE__) || defined(_WIN32) || defined(__OHOS__)\n/* Rewrite paths starting with /tmp on platforms with private temp roots. */"
            if source.count(old_macro) != 1:
                raise ConanInvalidConfiguration("unexpected temp-path feature gate")
            source = source.replace(old_macro, new_macro, 1)
            old_branch = """#endif  /* _WIN32 */
    }

        /* Now handle %fname */"""
            new_branch = """#elif defined(__OHOS__)
        const char *temp = getenv("TMPDIR");
        size_t temp_len = temp ? strlen(temp) : 0;
        if (!temp || temp[0] != '/' || temp_len + dirlen - 4 >= size) {
            LEPT_FREE(cdir);
            LEPT_FREE(pathout);
            return (char *)ERROR_PTR("invalid OHOS TMPDIR", __func__, NULL);
        }
        stringCopy(pathout, temp, size);
        if (dirlen > 4)
            stringCat(pathout, size, cdir + 4);
#endif  /* _WIN32 */
    }

        /* Now handle %fname */"""
            if source.count(old_branch) != 1:
                raise ConanInvalidConfiguration("unexpected temp-path rewrite switch")
            source = source.replace(old_branch, new_branch, 1)
            utils.write_text(source, encoding="utf-8")
            # CI HMDFS maps 0700 mktemp directories to an owner the build
            # uid cannot traverse. Autoconf config.status creates subs1.awk
            # there; use an atomic group-accessible mkdir at creation time.
            configure = Path(self.source_folder, "configure")
            script = configure.read_text(encoding="utf-8")
            old_temp = '''{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5'''
            new_temp = '''{
  tmp=./conf$$-$RANDOM
  (umask 007 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5'''
            if script.count(old_temp) != 1:
                raise ConanInvalidConfiguration("unexpected Autoconf temp-directory logic")
            configure.write_text(script.replace(old_temp, new_temp, 1),
                                 encoding="utf-8")
            config_sub = Path(self.source_folder, "config", "config.sub")
            content = config_sub.read_text(encoding="utf-8")
            replacements = {
                "gnu* | android* | bsd* |": "gnu* | android* | ohos* | bsd* |",
                "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \\":
                    "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* | linux-ohos* \\",
            }
            for old, new in replacements.items():
                if content.count(old) != 1:
                    raise ConanInvalidConfiguration("unexpected config.sub OS table")
                content = content.replace(old, new, 1)
            config_sub.write_text(content, encoding="utf-8")

            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            compiler = executables.get("c")
            if not compiler or not Path(compiler).is_file():
                raise ConanInvalidConfiguration("missing configured C compiler")
            result = subprocess.run(
                [compiler, "-dumpmachine"], capture_output=True, text=True,
                check=True, timeout=10,
            )
            triplet = result.stdout.strip()
            if not re.fullmatch(r"[A-Za-z0-9_.+-]+", triplet):
                raise ConanInvalidConfiguration("invalid compiler target triplet")
            args = ["--build=" + triplet, "--host=" + triplet]

        with self._run_environment().vars(self).apply():
            autotools = Autotools(self)
            autotools.configure(args=args)
            config_header = Path(self.build_folder, "config_auto.h")
            if not config_header.is_file():
                raise ConanInvalidConfiguration("configure did not generate config_auto.h")
            features = config_header.read_text(encoding="utf-8")
            for feature in (
                "HAVE_LIBZ", "HAVE_LIBPNG", "HAVE_LIBJPEG", "HAVE_LIBGIF",
                "HAVE_LIBTIFF", "HAVE_LIBWEBP", "HAVE_LIBWEBP_ANIM", "HAVE_LIBJP2K",
            ):
                if not re.search(r"^#define " + feature + r" 1$", features, re.M):
                    raise ConanInvalidConfiguration("image codec not enabled: " + feature)
            autotools.make(args=["-j2"])
            if str(self.settings.os) == "OHOS":
                plotter = Path(self.dependencies.build["gnuplot"].package_folder,
                               "bin", "gnuplot")
                if plotter.is_file():
                    probe = subprocess.run(
                        [str(plotter), "-e", "set terminal png"],
                        capture_output=True, text=True, timeout=10,
                    )
                    self.output.info(
                        "GNUPLOT_PNG_PROBE rc={} output={!r}".format(
                            probe.returncode, (probe.stdout + probe.stderr)[:400]
                        )
                    )
                else:
                    self.output.info("GNUPLOT_PNG_PROBE missing executable")
                # reg_wrapper invokes Libtool shell wrappers directly. HMDFS
                # rejects that exec path even when the wrapped ELF is signed.
                wrapper = Path(self.source_folder, "prog", "reg_wrapper.sh")
                contents = wrapper.read_text(encoding="utf-8")
                old = '\\"${PWD}/\\"${TEST}'
                if contents.count(old) != 2:
                    raise ConanInvalidConfiguration("unexpected regression wrapper calls")
                contents = contents.replace(old, '/system/bin/sh ' + old)
                # The packaged gnuplot can emit benign font warnings while
                # successfully selecting PNG. Upstream treats any output as
                # missing support and incorrectly skips 25 registered tests.
                old_guard = (
                    'if [ -z "${GNUPLOT}" ] || '
                    '[ -n "$(${GNUPLOT} -e \'set terminal png\' 2>&1)" ] ; then'
                )
                new_guard = (
                    'if [ -z "${GNUPLOT}" ] || '
                    '! "${GNUPLOT}" -e \'set terminal png\' >/dev/null 2>&1 ; then'
                )
                if contents.count(old_guard) != 1:
                    raise ConanInvalidConfiguration("unexpected gnuplot test gate")
                contents = contents.replace(old_guard, new_guard, 1)
                wrapper.write_text(contents, encoding="utf-8")
            # Serialize target launches and use the system shell for Make's
            # recipe commands; do not skip or narrow upstream test entries.
            autotools.make(target="check", args=["-j1", "SHELL=/system/bin/sh"])

    def package(self):
        with self._run_environment().vars(self).apply():
            Autotools(self).install()
        copy(self, "leptonica-license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        pc = Path(self.package_folder, "lib", "pkgconfig", "lept.pc")
        if not pc.is_file():
            raise ValueError("leptonica did not install lept.pc")
        content = pc.read_text(encoding="utf-8")
        if sum(line.startswith("prefix=") for line in content.splitlines()) != 1 or \
                "Libs.private:" not in content:
            raise ValueError("unexpected upstream lept.pc fields")
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("prefix="):
                lines[index] = "prefix=${pcfiledir}/../.."
            elif line.startswith("Libs.private:"):
                lines[index] = "Libs.private: -lgif -lm"
        lines.append("Requires.private: zlib libpng libjpeg libtiff-4 libwebp libwebpmux libopenjp2")
        pc.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def package_info(self):
        self.cpp_info.libs = ["leptonica"]
        self.cpp_info.set_property("cmake_file_name", "Leptonica")
        self.cpp_info.set_property("cmake_target_name", "Leptonica::Leptonica")
        self.cpp_info.set_property("pkg_config_name", "lept")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
