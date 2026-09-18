#!/usr/bin/env python3
"""Conan recipe — libmediainfo 25.07 (MediaInfoLib, MediaArea).

MediaInfoLib is the core library of MediaInfo: convenient unified display
of the most relevant technical and tag data for video and audio files
(containers: MKV/MP4/AVI/OGG/MPEG-PS/TS/FLV/MXF..., streams: AVC/HEVC/
AV1/Vorbis/Opus/FLAC/AAC...).

OHOS adaptation notes:
  - ZenLib is a hard requirement of MediaInfoLib's CMake
    (find_package(ZenLib REQUIRED) when BUILD_ZENLIB=OFF).  libzen/0.4.41
    is NOT published in the OHOS conan registry (W0 preflight download
    verified not-found), so we vendor ZenLib 0.4.41 source as a sibling
    directory and enable the upstream-supported BUILD_ZENLIB=ON bundled
    build (same approach as glib2/2.88.0's libffi_subproject and
    MediaArea-family avimetaedit/1.0.2).
  - ZenLib Thread.cpp calls pthread_cancel() which does not exist on
    HarmonyOS musl -> patch 0001 guards it with __OHOS__ (mirrors the
    already-merged archives/l/libzen/0.4.41 patch).
  - zlib comes from the conan registry (zlib/1.3.1).
  - tinyxml2 / curl are optional in upstream CMake: tinyxml2 falls back
    to the bundled ThirdParty/tinyxml2 source; curl is disabled via
    MEDIAINFO_LIBCURL_NO when CURL is not found, so no registry deps.
  - Static build only (BUILD_SHARED_LIBS=OFF): the shared build embeds a
    "ZenLib/libzen.so" SONAME prefix from the add_subdirectory layout
    which breaks dynamic loading on OHOS.
  - CMake < 3.5 compatibility removed in CMake 4.x: pass
    CMAKE_POLICY_VERSION_MINIMUM=3.5 (ZenLib's 3.1.0 minimum).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, export_conandata_patches, get, rmdir


class LibmediainfoConan(ConanFile):
    name = "libmediainfo"
    version = "25.07"
    description = "MediaInfoLib - convenient unified display of the most relevant technical and tag data for video and audio files"
    license = ("BSD-2-Clause", "Apache-2.0", "LGPL-2.1-or-later", "GPL-2.0-or-later", "MPL-2.0")
    homepage = "https://mediaarea.net/en/MediaInfo"
    url = ""
    package_type = "library"
    topics = ("video", "audio", "metadata", "tag", "media")

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Shared build is not supported on OHOS (see module docstring).
        if self.settings.os == "OHOS" and self.options.shared:
            raise Exception(
                "libmediainfo on OHOS supports static builds only: the "
                "upstream add_subdirectory layout links libmediainfo.so "
                "against a 'ZenLib/libzen.so' SONAME prefix that the OHOS "
                "dynamic loader cannot resolve")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib/1.3.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendor ZenLib 0.4.41 as a sibling of the MediaInfoLib source dir
        # (upstream CMake expects ../../../ZenLib from Project/CMake).
        # The GitHub tag tarball root is "ZenLib-0.4.41"; extract into the
        # src parent and normalise the directory name to "ZenLib".
        parent = os.path.dirname(self.source_folder)
        zen = self.conan_data["libzen_subproject"]["source"]
        zen_dst = os.path.join(parent, "ZenLib")
        if not os.path.isdir(zen_dst):
            get(self, url=zen["url"], sha256=zen["sha256"],
                destination=parent, strip_root=False)
            for cand in ("ZenLib-0.4.41", "ZenLib"):
                extracted = os.path.join(parent, cand)
                if os.path.isdir(extracted) and cand != "ZenLib":
                    os.rename(extracted, zen_dst)
                    break
        # The conandata patch targets the vendored ZenLib tree (path prefix
        # ZenLib/Source/ZenLib/Thread.cpp, CRLF to match upstream file).
        # OHOS /bin/patch lacks GNU options (--forward/--silent), so the
        # patch is applied with a minimal in-python unified-diff applier
        # that tolerates CRLF and is idempotent.
        parent = os.path.dirname(self.source_folder)
        for p in self.conan_data.get("patches", []):
            rel = p["patch_file"]
            # The patch is exported by export_conandata_patches() into the
            # package cache (s/patches/) next to src/; the recipe folder
            # (e/) does NOT carry it.  Probe the known cache layouts.
            cands = [os.path.join(self.recipe_folder, rel),
                     os.path.join(parent, rel),
                     os.path.join(self.source_folder, rel)]
            pf = next((c for c in cands if os.path.isfile(c)), None)
            if pf is None:
                raise Exception(f"patch file not found: {rel} (tried {cands})")
            _apply_patch_crlf(pf, parent)

    def _probe_pthread_cancel(self):
        """Build-time capability probe (R8): compile+link a tiny program
        that references pthread_cancel with the profile toolchain.  On
        musl-based targets (e.g. HarmonyOS) the symbol is absent, and the
        vendored ZenLib then compiles with ZENLIB_NO_PTHREAD_CANCEL
        instead of pthread_cancel().  This is a capability probe, not a
        platform-name conditional."""
        import tempfile
        import subprocess
        src = "#include <pthread.h>\nint main(void){ pthread_cancel(0); return 0; }\n"
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR") or tempfile.gettempdir()) as td:
            c = os.path.join(td, "probe.c")
            with open(c, "w") as f:
                f.write(src)
            comp = (self.conf.get("tools.build:compiler_executables") or {}).get("c", "clang")
            out = os.path.join(td, "probe.out")
            r = subprocess.run([comp, c, "-o", out, "-lpthread"],
                               capture_output=True)
            return r.returncode == 0 and os.path.isfile(out)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_ZENLIB"] = True
        tc.variables["BUILD_ZLIB"] = False
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["ENABLE_UNICODE"] = True
        # Capability probe (R8): only compile pthread_cancel into the
        # vendored ZenLib when the target toolchain actually provides it.
        if not self._probe_pthread_cancel():
            self.output.info("pthread_cancel not linkable on this target: "
                             "enabling ZENLIB_NO_PTHREAD_CANCEL")
            tc.extra_cflags.append("-DZENLIB_NO_PTHREAD_CANCEL")
            tc.extra_cxxflags.append("-DZENLIB_NO_PTHREAD_CANCEL")
        # CMake >= 4 removed compatibility with CMake < 3.5 (ZenLib asks
        # for 3.1.0); keep the policy floor at 3.5.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Do not let CMake pick up system CURL/TinyXML (registry deps):
        # TinyXML falls back to the bundled ThirdParty/tinyxml2 and CURL
        # compiles MEDIAINFO_LIBCURL_NO (Reader_libcurl is not built).
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join("Project", "CMake"))
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "License.html", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "MediaInfoLib")
        self.cpp_info.set_property("cmake_target_name", "mediainfo")
        self.cpp_info.set_property("pkg_config_name", "libmediainfo")
        # Static link of the vendored ZenLib into libmediainfo.a is NOT
        # performed by upstream CMake (they stay separate objects merged
        # only in the shared lib); the installed archives are:
        self.cpp_info.libs = ["mediainfo", "zen"]
        self.cpp_info.includedirs = [os.path.join("include")]
        if self.settings.os in ["Linux", "FreeBSD", "OHOS"]:
            self.cpp_info.system_libs.extend(["dl", "m", "pthread"])


def _apply_patch_crlf(patch_file, target_root):
    """Minimal unified-diff applier (CRLF tolerant, idempotent).

    OHOS /bin/patch is busybox-flavoured (no --forward/--silent), and the
    vendored ZenLib sources are CRLF while conanfile.py-written patches
    keep the upstream CRLF line endings.  This helper parses the classic
    @@ hunks of a unified diff and applies the replacements line by line,
    normalising line endings on comparison.
    """
    with open(patch_file, "rb") as f:
        raw = f.read().decode("utf-8", "replace").replace("\r\n", "\n")

    # parse hunks: --- a/path +++ b/path @@ -s,c +s,c @@ context
    hunks = []          # (target_path, [(old_lines, new_lines)])
    lines = raw.split("\n")
    i = 0
    target = None
    while i < len(lines):
        if lines[i].startswith("--- a/"):
            target = lines[i][6:].strip()
            # skip the +++ line
            i += 2
            while i < len(lines) and lines[i].startswith("@@"):
                # parse hunk body
                old_block, new_block = [], []
                j = i + 1
                while j < len(lines) and not lines[j].startswith("@@") \
                        and not lines[j].startswith("--- ") \
                        and (lines[j].startswith((" ", "-", "+")) or lines[j] == ""):
                    l = lines[j]
                    if l.startswith("---") and not l.startswith("--- a/"):
                        break
                    if l.startswith("+"):
                        new_block.append(l[1:])
                    elif l.startswith("-"):
                        old_block.append(l[1:])
                    else:
                        old_block.append(l[1:] if l else "")
                        new_block.append(l[1:] if l else "")
                    j += 1
                hunks.append((target, old_block, new_block))
                i = j
            continue
        i += 1

    for target, old_block, new_block in hunks:
        path = os.path.join(target_root, target)
        with open(path, "rb") as f:
            content = f.read().decode("utf-8", "replace")
        crlf = "\r\n" in content
        norm = content.replace("\r\n", "\n")
        if "\n".join(new_block) in norm:
            continue  # already patched (idempotent)
        old_txt = "\n".join(old_block)
        new_txt = "\n".join(new_block)
        if old_txt not in norm:
            raise Exception(f"patch hunk not found in {path}")
        norm = norm.replace(old_txt, new_txt, 1)
        if crlf:
            norm = norm.replace("\n", "\r\n")
        with open(path, "wb") as f:
            f.write(norm.encode())
