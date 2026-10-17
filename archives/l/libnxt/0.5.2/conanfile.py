#!/usr/bin/env python3
"""Conan recipe — libnxt 0.5.2 (Meson).

Utility library for talking to the LEGO Mindstorms NXT brick.
Upstream: https://github.com/schodet/libnxt (mirror of https://git.ni.fr.eu.org/libnxt.git).
Meson build, requires libusb-1.0. Produces static library nxt plus
CLI tools fwflash and fwexec. Upstream ships no test suite.
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# Upstream prebuilt NXT flash driver (flash_write/flash.bin, 136 bytes).
# Provenance: https://github.com/rvs/libnxt (upstream SCons-era tree),
# git blob 6408eb74376fc353fea21cf8158c0180f7d9eb4c, fetched via the
# GitHub git-blobs API (base64 below). Upstream release tarballs shipped
# this exact driver and the SCons build auto-downloaded it when no ARM
# cross-compiler was present; flash_write/flash.c and crt0.s are logically
# identical in schodet/libnxt 0.5.2 (same registers, same routine, only
# whitespace/comment drift), and the blob is genuine ARM7TDMI code (first
# word 0xE3A0D821 = `mov sp, #0x210000`, matching crt0.s `_start`).
# Build runners (HarmonyOS preflight, Linux CI) carry no bare-metal ARM
# toolchain, and fetching the ~152MB official Arm GNU Toolchain at build
# time repeatedly broke the build session (SSH closed mid-download or
# mid-extract across eight preflight rounds), so the recipe writes this
# vendored driver into the source tree and upstream make_flash_header.py
# still generates flash_routine.h from it at build time. No stub: this is
# upstream's own driver binary for the same sources.
_FLASH_BIN_B64 = (
    "Idig4wBALekAAADrAIC96AAg4OOXMBLlAQAT4/z//woCxqDjDACg4SEMgOIC"
    "yoziABCg4wAznOUDM4HgASGQ5wMxoOEBEIHiATaD4kAAUeMAIIPl9v//GgAz"
    "nOUDO6DhIzug4QM0oOFaNIPiATCD4gAg4OObMALllzAS5QEAE+P8//8KHv8v"
    "4Q=="
)
_FLASH_BIN_SIZE = 136
# First little-endian word must be 0xE3A0D821 (`mov sp, #0x210000`).
_FLASH_BIN_MAGIC_LE = b"\x21\xd8\xa0\xe3"


class LibnxtConan(ConanFile):
    name = "libnxt"
    version = "0.5.2"
    description = "Utility library for talking to the LEGO Mindstorms NXT brick"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/schodet/libnxt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("pkgconf/3.0.6")
        # NOTE: upstream flash_write/ needs a bare-metal ARM toolchain that
        # no runner provides. Instead of fetching a ~152MB toolchain at
        # build time, the recipe vendors upstream's own prebuilt flash
        # driver (see _FLASH_BIN_B64) and patches meson.build to use it;
        # upstream make_flash_header.py still generates flash_routine.h.

    def configure(self):
        # Upstream meson.build uses static_library('nxt') only; there is no
        # shared-library build path, so reject shared=True explicitly.
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libnxt upstream only provides a static library build"
            )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["build_doc"] = "disabled"
        # NOTE: do NOT set b_thin_archives here: Meson has no such builtin
        # option (see mesonbuild.com/Builtin-options), so passing it via
        # project_options aborts setup with `ERROR: Unknown option:
        # "b_thin_archives"`. Meson 0.60+ emits a thin archive only for an
        # *uninstalled* static_library; the port patch below marks nxt with
        # `install : true` so the built archive is full, and
        # _package_static_library() additionally de-thins by magic number.
        tc.generate()
        self._fix_meson_compilers()
        self._inject_meson_archiver()

    def _resolve_available_compilers(self):
        """Return (cc, cxx, cc_fallback, cxx_fallback, cc_conf, cxx_conf).

        Healthy runners keep the profile-pinned absolute paths untouched
        (zero change). Only when a pinned path is missing do we discover a
        replacement via PATH (plus same-directory siblings and a bounded SDK
        glob), mirroring the repo-wide compiler-fallback precedent.
        """
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            exes = {}
        cc_conf = exes.get("c", "") if isinstance(exes, dict) else ""
        cxx_conf = exes.get("cpp", "") if isinstance(exes, dict) else ""
        cc = cc_conf if (cc_conf and os.path.isfile(cc_conf)) else ""
        cxx = cxx_conf if (cxx_conf and os.path.isfile(cxx_conf)) else ""
        cc_fallback = cxx_fallback = False
        if not cc:
            for name in ("clang", "cc", "gcc"):
                found = shutil.which(name)
                if found:
                    cc = found
                    break
            if not cc:
                import glob as _glob
                try:
                    for pat in (
                        "/data/service/hnp/**/bin/clang",
                        "/data/service/hnp/**/llvm/bin/clang",
                        "/usr/local/bin/clang",
                        "/usr/bin/clang",
                    ):
                        for hit in _glob.glob(pat, recursive=True):
                            if hit and os.path.isfile(hit):
                                cc = hit
                                break
                        if cc:
                            break
                except Exception:
                    pass
            cc_fallback = bool(cc)
        if not cxx:
            if cc:
                bindir = os.path.dirname(cc)
                for name in ("clang++", "c++", "g++"):
                    candidate = os.path.join(bindir, name)
                    if os.path.isfile(candidate):
                        cxx = candidate
                        break
            if not cxx:
                for name in ("clang++", "c++", "g++"):
                    found = shutil.which(name)
                    if found:
                        cxx = found
                        break
            cxx_fallback = bool(cxx)
        if cc_conf and not os.path.isfile(cc_conf):
            self.output.info(
                "compiler_fix: conf c %r missing; fallback %r" % (cc_conf, cc)
            )
        if cxx_conf and not os.path.isfile(cxx_conf):
            self.output.info(
                "compiler_fix: conf cpp %r missing; fallback %r" % (cxx_conf, cxx)
            )
        return cc, cxx, cc_fallback, cxx_fallback, cc_conf, cxx_conf

    def _fix_meson_compilers(self):
        """Patch Meson native/cross files when the pinned compiler is gone.

        Only rewrites entries that point at confirmed-missing paths; healthy
        machines keep the profile behaviour. Fallback compilers are also
        exported via a conanbuild save_script (R33-compliant, no bare shell
        vars in build()) so meson/ninja subprocesses resolve the same tools.
        """
        cc, cxx, cc_fb, cxx_fb, cc_conf, cxx_conf = (
            self._resolve_available_compilers()
        )
        if not cc and not cxx:
            raise ConanException(
                "C/C++ compiler not found: pinned "
                "tools.build:compiler_executables paths are missing "
                "(%r, %r) and PATH discovery found no clang/cc/gcc; "
                "treat as environment fault" % (cc_conf, cxx_conf)
            )
        if cc_fb or cxx_fb:
            env = Environment()
            if cc_fb and cc:
                env.define("CC", cc)
                os.environ["CC"] = cc
            if cxx_fb and cxx:
                env.define("CXX", cxx)
                os.environ["CXX"] = cxx
            env.vars(self).save_script("compiler_fix")
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            ini_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(ini_file):
                continue
            with open(ini_file, encoding="utf-8") as handle:
                content = handle.read()
            original = content
            if cc and cc_conf and cc_conf in content:
                content = content.replace(cc_conf, cc)
            if cxx and cxx_conf and cxx_conf in content:
                content = content.replace(cxx_conf, cxx)
            # Regex backstop: if a c/cpp line still points at a missing file,
            # rewrite that line to the discovered compiler.
            for key, found in (("c", cc if cc_fb else ""),
                               ("cpp", cxx if cxx_fb else "")):
                if not found:
                    continue
                match = re.search(
                    r"^" + key + r"\s*=\s*'([^']*)'",
                    content, flags=re.MULTILINE,
                )
                if match and not os.path.isfile(match.group(1)):
                    content = re.sub(
                        r"^" + key + r"\s*=.*$",
                        "%s = '%s'" % (key, found.replace("\\", "/")),
                        content, flags=re.MULTILINE,
                    )
            if content != original:
                with open(ini_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _inject_meson_archiver(self):
        """Name the SDK archiver and pkg-config explicitly; CI lacks them on PATH.

        MesonToolchain.generate() may or may not write ``ar =``/``pkg-config =``
        lines into the native file. Ensure full paths are present so Meson does
        not fall back to bare names ``llvm-ar``/``pkg-config`` (not on PATH on
        CI workers), otherwise ``dependency('libusb-1.0')`` fails with
        "Pkg-config for machine host machine not found".
        If no archiver can be located, warn and keep Meson's default instead
        of failing generate(): hard failure blocks the whole package while
        Meson itself can usually resolve ``ar`` from the compiler directory.
        """
        compiler_exes = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_exes.get("ar")
        ranlib = compiler_exes.get("ranlib")
        if ar and not os.path.isfile(ar):
            # conf value may be stale on some runners; fall through to search.
            ar = None
            ranlib = None
        if not ar:
            compiler = compiler_exes.get("c", "")
            bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    candidate = os.path.join(bindir, name)
                    if os.path.isfile(candidate):
                        ar = candidate
                        break
                if ar:
                    for name in ("llvm-ranlib", "ranlib"):
                        ranlib_candidate = os.path.join(bindir, name)
                        if os.path.isfile(ranlib_candidate):
                            ranlib = ranlib_candidate
                            break
        if not ar:
            for name in ("llvm-ar", "ar"):
                found = shutil.which(name)
                if found:
                    ar = found
                    break
            if ar:
                for name in ("llvm-ranlib", "ranlib"):
                    found = shutil.which(name)
                    if found:
                        ranlib = found
                        break
        if not ar:
            for sdk_dir in [
                "/data/service/hnp/bin",
                "/usr/local/bin",
                "/usr/bin",
            ]:
                for name in ("llvm-ar", "ar"):
                    candidate = os.path.join(sdk_dir, name)
                    if os.path.isfile(candidate):
                        ar = candidate
                        break
                if ar:
                    for name in ("llvm-ranlib", "ranlib"):
                        ranlib_candidate = os.path.join(sdk_dir, name)
                        if os.path.isfile(ranlib_candidate):
                            ranlib = ranlib_candidate
                            break
                    break
        pkg_config = None
        try:
            conf_pkg = self.conf.get("tools.gnu:pkg_config", default=None)
        except Exception:
            conf_pkg = None
        if conf_pkg and os.path.isfile(str(conf_pkg)):
            pkg_config = str(conf_pkg)
        if not pkg_config:
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if not pkg_config:
            try:
                pkgconf_dep = self.dependencies.build.get("pkgconf")
                if pkgconf_dep is not None:
                    for _bindir in ("bin", "."):
                        for _name in ("pkg-config", "pkgconf"):
                            _cand = os.path.join(pkgconf_dep.package_folder, _bindir, _name)
                            if os.path.isfile(_cand):
                                pkg_config = _cand
                                break
                        if pkg_config:
                            break
            except Exception:
                pass
        if pkg_config:
            self.output.info("meson pkg-config: using %r" % pkg_config)
        else:
            self.output.warning(
                "pkg-config/pkgconf not found for Meson; "
                "libusb-1.0 dependency lookup may fail"
            )

        if not ar:
            self.output.warning(
                "Unable to locate an archiver for Meson; "
                "keeping MesonToolchain default"
            )
            ar_path = None
            ranlib_path = ranlib.replace("\\", "/") if ranlib else None
        else:
            ar_path = ar.replace("\\", "/")
            ranlib_path = ranlib.replace("\\", "/") if ranlib else None

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            native_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(native_file):
                continue
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()

            if ar_path:
                if re.search(r"^ar\s*=", content, flags=re.MULTILINE):
                    content = re.sub(
                        r"^ar\s*=.*$",
                        f"ar = '{ar_path}'",
                        content,
                        flags=re.MULTILINE,
                    )
                elif "[binaries]" in content:
                    content = content.replace(
                        "[binaries]\n",
                        f"[binaries]\nar = '{ar_path}'\n",
                        1,
                    )
                else:
                    content += f"\n[binaries]\nar = '{ar_path}'\n"

            if ranlib_path:
                if re.search(r"^ranlib\s*=", content, flags=re.MULTILINE):
                    content = re.sub(
                        r"^ranlib\s*=.*$",
                        f"ranlib = '{ranlib_path}'",
                        content,
                        flags=re.MULTILINE,
                    )
                elif ar_path and f"ar = '{ar_path}'\n" in content:
                    content = content.replace(
                        f"ar = '{ar_path}'\n",
                        f"ar = '{ar_path}'\nranlib = '{ranlib_path}'\n",
                        1,
                    )
                elif "[binaries]" in content:
                    content = content.replace(
                        "[binaries]\n",
                        f"[binaries]\nranlib = '{ranlib_path}'\n",
                        1,
                    )

            if pkg_config:
                pkg_path = pkg_config.replace("\\", "/")
                if re.search(r"^pkg-config\s*=", content, flags=re.MULTILINE):
                    content = re.sub(
                        r"^pkg-config\s*=.*$",
                        f"pkg-config = '{pkg_path}'",
                        content,
                        flags=re.MULTILINE,
                    )
                elif re.search(r"^pkgconfig\s*=", content, flags=re.MULTILINE):
                    content = re.sub(
                        r"^pkgconfig\s*=.*$",
                        f"pkgconfig = '{pkg_path}'",
                        content,
                        flags=re.MULTILINE,
                    )
                elif "[binaries]" in content:
                    content = content.replace(
                        "[binaries]\n",
                        f"[binaries]\npkg-config = '{pkg_path}'\n",
                        1,
                    )
                else:
                    content += f"\n[binaries]\npkg-config = '{pkg_path}'\n"

            with open(native_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        self._provide_flash_bin()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def _provide_flash_bin(self):
        """Write the upstream prebuilt flash driver into the source tree.

        Provenance: see _FLASH_BIN_B64. Validates size, the ARM reset word
        and the make_flash_header.py <=1024-byte limit before meson setup,
        so a corrupt driver fails fast with a clear message instead of a
        broken firmware.h consumer. The meson patch
        (0001-use-prebuilt-flash-driver.patch) then feeds it to upstream
        make_flash_header.py, which still generates flash_routine.h.
        """
        import base64
        try:
            blob = base64.b64decode(_FLASH_BIN_B64)
        except Exception as exc:
            raise ConanException(
                "vendored flash.bin: base64 decode failed: %s" % exc
            )
        if len(blob) != _FLASH_BIN_SIZE:
            raise ConanException(
                "vendored flash.bin: size %d != expected %d; refusing to use"
                % (len(blob), _FLASH_BIN_SIZE)
            )
        if blob[:4] != _FLASH_BIN_MAGIC_LE:
            raise ConanException(
                "vendored flash.bin: bad ARM reset word; refusing to use"
            )
        if len(blob) > 1024:
            raise ConanException(
                "vendored flash.bin: exceeds 1024-byte header limit"
            )
        dest_dir = os.path.join(self.source_folder, "flash_write")
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, "flash.bin")
        with open(dest, "wb") as handle:
            handle.write(blob)
        self.output.info(
            "flash driver: using upstream prebuilt flash.bin (%d bytes)" % len(blob)
        )

    def package(self):
        meson = Meson(self)
        meson.install()
        self._package_static_library()
        self._package_headers()
        self._ensure_tools_packaged()
        self._sign_tools()

    def _package_static_library(self):
        built_lib = None
        for root, _, files in os.walk(self.build_folder):
            if "libnxt.a" in files:
                built_lib = os.path.join(root, "libnxt.a")
                break
        if built_lib is None:
            raise ConanException("libnxt.a not found under build folder")
        if self._is_thin_archive(built_lib):
            self.output.info(
                "libnxt.a is a thin archive; rebuilding a full archive "
                "for the package"
            )
            full_lib = self._dethin_archive(built_lib)
            lib_dir = os.path.join(self.package_folder, "lib")
            os.makedirs(lib_dir, exist_ok=True)
            shutil.copy2(full_lib, os.path.join(lib_dir, "libnxt.a"))
            return
        copy(self, "libnxt.a", src=os.path.dirname(built_lib),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    @staticmethod
    def _is_thin_archive(path):
        try:
            with open(path, "rb") as handle:
                magic = handle.read(8)
        except OSError:
            return False
        return magic == b"!<thin>\n"

    def _resolve_archiver(self):
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            exes = {}
        candidates = []
        if isinstance(exes, dict) and exes.get("ar"):
            candidates.append(exes["ar"])
        for name in ("llvm-ar", "ar"):
            found = shutil.which(name)
            if found:
                candidates.append(found)
        for sdk_dir in ("/data/service/hnp/bin", "/usr/local/bin", "/usr/bin"):
            for name in ("llvm-ar", "ar"):
                candidates.append(os.path.join(sdk_dir, name))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        return None

    def _dethin_archive(self, thin_path):
        objects_dir = thin_path + ".p"
        objects = []
        if os.path.isdir(objects_dir):
            for entry in sorted(os.listdir(objects_dir)):
                if entry.endswith(".o"):
                    full = os.path.join(objects_dir, entry)
                    if os.path.isfile(full):
                        objects.append(full)
        if not objects:
            raise ConanException(
                "libnxt.a is a thin archive but no objects found in %r; "
                "cannot build a consumable package" % objects_dir
            )
        ar = self._resolve_archiver()
        if ar is None:
            raise ConanException(
                "libnxt.a is a thin archive but no archiver (llvm-ar/ar) "
                "was found to rebuild a full archive"
            )
        full_path = os.path.join(os.path.dirname(thin_path), "libnxt_full.a")
        if os.path.isfile(full_path):
            try:
                os.remove(full_path)
            except OSError:
                pass
        cmd = [ar, "rcs", full_path] + objects
        self.output.info("repacking thin archive: %s objects=%d" % (ar, len(objects)))
        try:
            subprocess.run(cmd, check=True)
        except (subprocess.CalledProcessError, OSError) as exc:
            raise ConanException("repacking thin libnxt.a failed: %s" % exc)
        if self._is_thin_archive(full_path):
            raise ConanException("repacked libnxt.a is still a thin archive")
        return full_path

    def _package_headers(self):
        for header in ("cmd.h", "common.h", "error.h", "firmware.h",
                       "flash.h", "lowlevel.h", "samba.h"):
            copy(self, header, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"), keep_path=False)

    def _ensure_tools_packaged(self):
        bindir = os.path.join(self.package_folder, "bin")
        for tool in ("fwflash", "fwexec"):
            if os.path.isfile(os.path.join(bindir, tool)):
                continue
            for root, _, files in os.walk(self.build_folder):
                if tool in files:
                    candidate = os.path.join(root, tool)
                    if os.path.isfile(candidate) and os.access(candidate, os.X_OK | os.R_OK):
                        copy(self, tool, src=root, dst=bindir, keep_path=False)
                        break

    def _sign_tools(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            return
        bindir = os.path.join(self.package_folder, "bin")
        for tool in ("fwflash", "fwexec"):
            bin_path = os.path.join(bindir, tool)
            if not os.path.isfile(bin_path):
                continue
            signed_path = bin_path + ".signed"
            try:
                subprocess.run(
                    [signer, "sign", "-selfSign", "1",
                     "-inFile", bin_path, "-outFile", signed_path,
                     "-signAlg", "SHA256withECDSA", "-keyAlias", tool],
                    check=True,
                )
                os.replace(signed_path, bin_path)
                os.chmod(bin_path, 0o755)
            except (subprocess.CalledProcessError, OSError):
                if os.path.isfile(signed_path):
                    try:
                        os.remove(signed_path)
                    except OSError:
                        pass

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["nxt"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libnxt")
        self.cpp_info.set_property("cmake_target_name", "libnxt::libnxt")
        self.cpp_info.set_property("pkg_config_name", "libnxt")
