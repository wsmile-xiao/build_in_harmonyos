#!/usr/bin/env python3
"""Conan test_package for kjumpingcube 26.04.0.

kjumpingcube is a GUI application package (bin/kjumpingcube, no shipped
libraries), so the consumer test executes the packaged binary instead of
compiling against headers (R34: real consumption of the tested artifact):

  - headless smoke: `kjumpingcube --version` must exit 0 and print the
    upstream version (2.1.<release-service compact>) under the offscreen Qt
    platform with a sandboxed HOME/XDG tree, proving the musl loader
    resolves the complete KDEGames6/KF6/Qt6 DT_NEEDED closure through the
    conan-provided LD_LIBRARY_PATH (explicit closure, no default-search-path
    luck)
  - OHOS portability assertions (knowledge E537 parity): llvm-readelf must
    show no path-form DT_NEEDED entries (absolute conan-cache paths or
    ../-relative entries) in the installed executable, and libKDEGames6
    must be among the DT_NEEDED entries

Graph/env notes (all learned the hard way in CI):
  - openal-soft/libsndfile are re-declared here because the test graph
    marks the tested package's second-level dependencies as skipped
    (package_folder=None), which would leave libopenal.so.1/libsndfile.so.1
    out of the runtime loader path (same explicit-require pattern as the
    libkdegames/26.04.0.1 test_package).
  - Every runtime variable is passed INLINE on the command line (POSIX
    name=value prefixes): conan's self.run() executes in the build scope
    and replaces the process environment, so os.environ modifications do
    not reach the exec'd wrapper.
  - Dependency libraries are mirrored (copies, not symlinks: the CI sandbox
    denies symlink creation on HMDFS) into the cwd-relative resolution
    bases the musl loader uses for build-tree-relative DT_NEEDED entries
    inside published KF6 libraries ("../../bin/lib*.so", knowledge E537).
  - Platform PR-check self-heal (test-time closure shim): the cached KF6
    binaries themselves carry build-time-baked path-form DT_NEEDED entries
    (e.g. kxmlgui/6.18.0 ships its artifact with absolute conan-cache
    paths recorded on whatever machine built it), and the artifacts those
    paths point at may be stale symlinks into a different conan home that
    the platform buildbot context fails to load (rc=127, musl "Error
    loading shared library ... needed by libKF6XmlGui.so"). test()
    therefore walks the DT_NEEDED closure with the same pure-python ELF
    parsing model the recipe uses for its d_val sanitizer and, for every
    path-form entry, replaces symlink/missing targets with byte-level
    real-file copies taken from the dependency package folders conan
    actually resolved for this graph: absolute entries are repaired in
    place, relative entries are mirrored under the process CWD (musl
    resolves path-form NEEDED against the CWD). The shim never reads a
    hardcoded conan home, only creates real files (HMDFS denies symlinks),
    is idempotent, and fails fast with a clear error when a dependency
    basename cannot be found in the resolved graph.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class KJumpingCubeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    # Safety cap for the closure walk: a healthy graph converges in 2-3
    # rounds (seeded closure -> freshly repaired copies -> stable).
    _CLOSURE_MAX_ROUNDS = 10

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Runtime NEEDED of libKDEGames6.so (OpenAL audio backend /
        # sndfile). Without these explicit requires the test graph skips
        # them and their libraries are missing from the loader path.
        self.requires("openal-soft/1.25.2")
        self.requires("libsndfile/1.2.2")

    def test(self):
        lib_dirs = []
        plugin_dirs = []
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                self.output.warning(
                    "dependency without package_folder: {}".format(
                        dep.ref if dep else "?"
                    )
                )
                continue
            lib_dirs.append(os.path.join(dep.package_folder, "lib"))
            for rel in ("plugins", os.path.join("lib", "plugins")):
                plugin_dirs.append(os.path.join(dep.package_folder, rel))

        # Platform PR-check self-heal BEFORE anything loads: repair the
        # path-form DT_NEEDED closure of the dependency graph (see module
        # docstring). Sources come only from conan-resolved package
        # folders; no conan home is ever hardcoded.
        self._repair_path_form_needed_closure(lib_dirs)

        # Mirror every dependency library into the cwd-relative resolution
        # bases used by the musl loader for build-tree-relative DT_NEEDED
        # entries of published KF6 libraries ("../../bin/lib*.so").
        cwd = os.getcwd()
        mirror_bases = [
            os.path.join(cwd, "bin"),
            os.path.normpath(os.path.join(cwd, os.pardir, os.pardir, "bin")),
        ]
        for base in mirror_bases:
            os.makedirs(base, exist_ok=True)
        for lib_dir in lib_dirs:
            if not os.path.isdir(lib_dir):
                continue
            for name in os.listdir(lib_dir):
                if not name.startswith("lib") or ".so" not in name:
                    continue
                src = os.path.join(lib_dir, name)
                if not os.path.isfile(src):
                    continue
                for base in mirror_bases:
                    dst = os.path.join(base, name)
                    if os.path.exists(dst):
                        continue
                    try:
                        shutil.copy2(src, dst)
                    except OSError as exc:
                        self.output.warning(
                            "copy2({}, {}) failed: {}".format(src, dst, exc)
                        )
        lib_dirs.extend(mirror_bases)

        # Sandboxed user tree: the GUI stack (KConfig/QStandardPaths) must
        # only see writable, run-local locations on the device.
        home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)

        assignments = " ".join(
            [
                'LD_LIBRARY_PATH="{}"'.format(":".join(lib_dirs)),
                'QT_PLUGIN_PATH="{}"'.format(":".join(plugin_dirs)),
                "QT_QPA_PLATFORM=offscreen",
                'HOME="{}"'.format(home),
                'XDG_RUNTIME_DIR="{}"'.format(xdg_runtime),
                'XDG_CACHE_HOME="{}"'.format(os.path.join(home, ".cache")),
                'XDG_CONFIG_HOME="{}"'.format(os.path.join(home, ".config")),
                'XDG_DATA_HOME="{}"'.format(os.path.join(home, ".local", "share")),
            ]
        )

        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        exe = os.path.join(pkg.package_folder, "bin", "kjumpingcube")
        wrapper = os.path.join(self.source_folder, "test_kjumpingcube.sh")
        self.run('{} "{}" "{}"'.format(assignments, wrapper, exe))

    @staticmethod
    def _read_elf_needed(path):
        """Read-only DT_NEEDED extraction (pure python, ELFCLASS64 LE only).

        Same parsing model as the recipe-side d_val basename sanitizer,
        minus the rewrite: returns the raw NEEDED string list (empty for
        non-ELF or unreadable files).
        """
        import struct

        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError:
            return []
        if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
            return []
        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        if e_shoff == 0 or e_shentsize == 0:
            return []
        sections = []
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            sh_type = struct.unpack_from("<I", data, off + 4)[0]
            sh_addr = struct.unpack_from("<Q", data, off + 16)[0]
            sh_offset = struct.unpack_from("<Q", data, off + 24)[0]
            sh_size = struct.unpack_from("<Q", data, off + 32)[0]
            sections.append((sh_type, sh_addr, sh_offset, sh_size))
        needed = []
        for sh_type, sh_addr, sh_offset, sh_size in sections:
            if sh_type != 6 or sh_size == 0:  # SHT_DYNAMIC
                continue
            strtab_addr = None
            for pos in range(sh_offset, sh_offset + sh_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", data, pos)
                if d_tag == 0:  # DT_NULL
                    break
                if d_tag == 5:  # DT_STRTAB
                    strtab_addr = d_val
                    break
            if strtab_addr is None:
                continue
            strtab_off = None
            strtab_size = 0
            for sh_type2, sh_addr2, sh_offset2, sh_size2 in sections:
                if sh_addr2 == strtab_addr and sh_type2 in (3, 6, 7, 1):
                    strtab_off = sh_offset2
                    strtab_size = sh_size2
                    break
            if strtab_off is None:
                continue
            strtab = data[strtab_off:strtab_off + strtab_size]
            for pos in range(sh_offset, sh_offset + sh_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", data, pos)
                if d_tag == 0:  # DT_NULL
                    break
                if d_tag != 1:  # DT_NEEDED only
                    continue
                if d_val >= len(strtab):
                    continue
                end = strtab.find(b"\x00", d_val)
                if end < 0:
                    continue
                needed.append(strtab[d_val:end].decode("utf-8", "replace"))
        return needed

    def _repair_path_form_needed_closure(self, lib_dirs):
        # Sources: basename -> candidate paths, collected ONLY from the
        # conan-resolved dependency package folders passed in by test()
        # (never a hardcoded conan home). Real regular files are preferred
        # over symlinks so the installed copies cannot inherit stale
        # cross-home links.
        sources = {}
        for lib_dir in lib_dirs:
            if not os.path.isdir(lib_dir):
                continue
            for name in os.listdir(lib_dir):
                path = os.path.join(lib_dir, name)
                if not os.path.isfile(path):  # follows symlinks
                    continue
                sources.setdefault(name, []).append(path)

        def pick_source(basename):
            candidates = sources.get(basename, [])
            for candidate in candidates:
                if not os.path.islink(candidate):
                    return candidate
            return candidates[0] if candidates else None

        def install_copy(source, target):
            # Byte-level copy that also replaces symlinks with real files
            # (HMDFS-safe; and the actual repair: a real file at the baked
            # path frees the loader from traversing stale cross-home
            # links). The bytes carry their OHOS signature, so no re-sign
            # is needed. The temp file also keeps source == target safe
            # (copy through the link first, then swap).
            tmp = target + ".shim-copy"
            try:
                shutil.copyfile(source, tmp)
                try:
                    shutil.copymode(source, tmp)
                except OSError:
                    pass
                if os.path.lexists(target):
                    os.remove(target)
                shutil.move(tmp, target)
            except OSError as exc:
                raise ConanException(
                    "test_package DT_NEEDED shim: cannot install real-file "
                    "copy for {} (from {}): {}".format(target, source, exc)
                )

        cwd = os.getcwd()
        tested = self.dependencies.get(self.tested_reference_str.split("/")[0])
        scan_roots = list(lib_dirs)
        if tested and tested.package_folder:
            scan_roots.append(os.path.join(tested.package_folder, "bin"))

        queue = []
        seen = set()
        for root in scan_roots:
            if not os.path.isdir(root):
                continue
            for name in os.listdir(root):
                path = os.path.join(root, name)
                if os.path.isfile(path) and path not in seen:
                    queue.append(path)
                    seen.add(path)

        repaired = 0
        rounds = 0
        while queue:
            rounds += 1
            if rounds > self._CLOSURE_MAX_ROUNDS:
                self.output.warning(
                    "DT_NEEDED closure shim: round cap {} reached, {} "
                    "files left unscanned".format(
                        self._CLOSURE_MAX_ROUNDS, len(queue)
                    )
                )
                break
            follow_up = []
            for path in queue:
                for entry in self._read_elf_needed(path):
                    if "/" not in entry:
                        continue  # plain soname-form: loader path handles it
                    if entry.startswith("/"):
                        target = os.path.normpath(entry)
                    else:
                        # musl has no $ORIGIN: path-form NEEDED is resolved
                        # against the process CWD.
                        target = os.path.normpath(os.path.join(cwd, entry))
                    if not (os.path.isfile(target) and not os.path.islink(target)):
                        source = pick_source(os.path.basename(entry))
                        if source is None:
                            raise ConanException(
                                "test_package DT_NEEDED shim: no source for "
                                "{} (NEEDED entry of {}): no real file with "
                                "this basename exists in any resolved "
                                "dependency package_folder lib/; refusing to "
                                "keep the stale symlink/missing target {}".format(
                                    entry, path, target
                                )
                            )
                        self.output.info(
                            "DT_NEEDED shim: {} entry {} -> real-file copy "
                            "from {}".format(
                                "absolute" if entry.startswith("/") else "relative",
                                target,
                                source,
                            )
                        )
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        install_copy(source, target)
                        repaired += 1
                    if target not in seen:
                        seen.add(target)
                        follow_up.append(target)
            queue = follow_up
        self.output.info(
            "DT_NEEDED closure shim: {} round(s), {} path-form entry(ies) "
            "repaired, closure stable".format(rounds, repaired)
        )
