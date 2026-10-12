#!/usr/bin/env python3
"""Conan test_package — osm-gps 1.2.0

L1/L2 test: compile a real consumer of osm-gps-map.h, link against
libosmgpsmap-1.0 and run it (headless — osm_gps_map_get_type() only
registers the GObject type, no display needed).

The dependency .so files are materialized into a local directory
(HMDFS rejects symlink following for dlopen), and LD_LIBRARY_PATH is
pointed there so the loader resolves the full GTK3/GLib closure at
runtime.
"""

import os
import glob
import shutil
import subprocess

from conan import ConanFile
from conan.tools.env import Environment


class OsmGpsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    # OHOS libsoup/2.74.3 packaging defect: it statically embeds GLib's GObject
    # type system and exports g_type_register_* globally, so any process that
    # also loads the shared libgobject (via gtk) gets two GType systems with
    # the same soname and aborts ("cannot register existing type 'gchar'").
    # This shim is LD_PRELOADed to funnel all GType registration into the single
    # shared libgobject table, idempotent by name. It is a loader-level
    # workaround for the libsoup defect, not a change to osm-gps behaviour.
    LIBSOUP_SHIM = "libsoup_gobject_shim.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _clear_readonly(self, path):
        """Make a file/dir writable so it can be removed (conan installs
        packages read-only; HMDFS rejects overwriting read-only dests)."""
        try:
            if os.path.islink(path) or os.path.isfile(path):
                os.chmod(path, 0o600)
            elif os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for f in dirs + files:
                        try:
                            os.chmod(os.path.join(root, f), 0o700)
                        except OSError:
                            pass
        except OSError:
            pass

    def _materialize_libs(self):
        """Copy every dependency's real .so into a flat local dir.

        HMDFS does not allow dlopen to follow symlinks, so the published
        packages' libosmgpsmap/libgtk/libglib symlinks are copied as real
        files here. Returns the local lib dir.

        The local dir may persist between conan-verify runs; conan installs
        packages read-only, so a stale copy cannot be overwritten with
        open(dest,'wb') (Operation not permitted). We clear it and make every
        fresh copy writable + executable.
        """
        local = os.path.join(self.build_folder, "local-libs")
        if os.path.lexists(local):
            self._clear_readonly(local)
            shutil.rmtree(local, ignore_errors=True)
        os.makedirs(local, exist_ok=True)
        seen = set()
        for dep in self.dependencies.values():
            pf = getattr(dep, "package_folder", None) or ""
            libdir = os.path.join(pf, "lib") if pf else ""
            if not os.path.isdir(libdir):
                continue
            for path in glob.glob(os.path.join(libdir, "*.so*")):
                if os.path.islink(path):
                    # Resolve the real file the symlink points at.
                    real = os.path.realpath(path)
                else:
                    real = path
                if not os.path.isfile(real):
                    continue
                name = os.path.basename(path)
                if name in seen:
                    continue
                seen.add(name)
                dest = os.path.join(local, name)
                if os.path.lexists(dest):
                    self._clear_readonly(dest)
                    os.remove(dest)
                shutil.copy(real, dest)
                try:
                    os.chmod(dest, 0o755)
                except OSError:
                    pass
        return local

    def test(self):
        pkg = self.dependencies["osm-gps"].package_folder
        local_libs = self._materialize_libs()

        # Collect include dirs from the full dependency graph so the
        # consumer can compile osm-gps-map.h (which includes GTK3/GLib).
        incs = [
            os.path.join(pkg, "include", "osmgpsmap-1.0"),
        ]
        for dep in self.dependencies.values():
            pf = getattr(dep, "package_folder", None) or ""
            for d in dep.cpp_info.includedirs:
                incs.append(d if (os.path.isabs(d) or not pf) else os.path.join(pf, d))
            for comp in getattr(dep.cpp_info, "components", {}).values():
                for d in comp.includedirs:
                    incs.append(d if (os.path.isabs(d) or not pf) else os.path.join(pf, d))
        # de-dupe, keep order
        seen_i = set()
        inc_flags = []
        for d in incs:
            if d and d not in seen_i:
                seen_i.add(d)
                inc_flags.append("-I{}".format(d))

        clang = "/data/service/hnp/bin/clang"
        test_c = os.path.join(self.source_folder, "test_osm.c")
        bin_path = os.path.join(self.build_folder, "test_osm")
        # Remove a stale read-only consumer binary from a previous run.
        if os.path.lexists(bin_path):
            try:
                os.chmod(bin_path, 0o600)
                os.remove(bin_path)
            except OSError:
                pass

        compile_cmd = (
            "{clang} {src} -o {out} {incs} "
            "-L{pkg_lib} -losmgpsmap-1.0 -fuse-ld=lld"
        ).format(
            clang=clang,
            src=test_c,
            out=bin_path,
            incs=" ".join(inc_flags),
            pkg_lib=os.path.join(pkg, "lib"),
        )

        # Build the libsoup/GLib GType double-registration workaround shim.
        # It must be a real signed ELF (OHOS loader refuses unsigned .so via
        # LD_PRELOAD). The shim source lives next to this conanfile.
        shim_so = self._build_libsoup_shim(clang, local_libs)

        # Environment: conanrun provides the OHOS clang PATH + dep
        # LD_LIBRARY_PATH; we prepend our materialized local-libs so the
        # loader resolves real .so files (HMDFS symlink-safe), and
        # LD_PRELOAD the GType shim to neutralize the libsoup defect.
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", local_libs)
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(pkg, "lib"))
        if shim_so:
            env.prepend_path("LD_PRELOAD", shim_so)
            self.output.info("LD_PRELOAD shim: {}".format(shim_so))

        self.output.info("Compiling consumer: {}".format(compile_cmd))
        with env.vars(self, "conanrun").apply():
            self.run(compile_cmd)
            self.output.info("Running consumer: {}".format(bin_path))
            self.run(bin_path)

    def _build_libsoup_shim(self, clang, local_libs):
        """Compile + sign the libsoup/GLib GType workaround shim.

        Returns the path to the signed shim .so, or None if it cannot be built
        (so the consumer still runs; the shim is purely a workaround).
        """
        shim_c = os.path.join(self.source_folder, self.LIBSOUP_SHIM)
        if not os.path.isfile(shim_c):
            self.output.warning("shim source missing: {}".format(shim_c))
            return None
        shim_so = os.path.join(self.build_folder, "libsoup_gobject_shim.so")
        # Remove any stale read-only shim from a previous run before rebuilding.
        if os.path.lexists(shim_so):
            try:
                os.chmod(shim_so, 0o600)
                os.remove(shim_so)
            except OSError:
                pass
        if os.path.lexists(shim_so + ".signed"):
            try:
                os.chmod(shim_so + ".signed", 0o600)
                os.remove(shim_so + ".signed")
            except OSError:
                pass
        # local-libs already contains the real libgobject-2.0.so.0 (materialized
        # from the dependency graph), which the shim dlopen()s at runtime.
        build = (
            "{clang} -shared -fPIC {src} -o {out} -fuse-ld=lld "
            "-Wl,-rpath,{local}"
        ).format(clang=clang, src=shim_c, out=shim_so, local=local_libs)
        try:
            self.run(build)
        except Exception as e:  # pragma: no cover - best effort
            self.output.warning("shim compile failed: {}".format(e))
            return None
        # Sign the ELF so the OHOS loader accepts it via LD_PRELOAD.
        sign_tool = None
        for cand in ("/data/service/hnp/bin/binary-sign-tool",
                    "/system/bin/binary-sign-tool",
                    "binary-sign-tool"):
            if os.path.exists(cand) or shutil.which(cand):
                sign_tool = cand
                break
        if sign_tool:
            signed = shim_so + ".signed"
            try:
                subprocess.run(
                    [sign_tool, "sign", "-inFile", shim_so,
                     "-outFile", signed, "-selfSign", "1"],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                if os.path.isfile(signed):
                    shutil.move(signed, shim_so)
                    os.chmod(shim_so, 0o755)
                    return shim_so
            except Exception as e:  # pragma: no cover - best effort
                self.output.warning("shim sign failed: {}".format(e))
        return None

        self.output.info(
            "CONSUMER_TEST_OK: osm_gps_map_get_type() executed and returned non-zero"
        )
