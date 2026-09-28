#!/usr/bin/env python3
"""Conan test_package for libgsystemservice 0.3.0 — consumer-side check.

Compiles test.c against the *installed* libgsystemservice and runs it on the
OHOS aarch64 target.

Three OHOS specifics are handled here:
  * the test needs a GResource containing the default configuration, so
    ``glib-compile-resources`` (shipped by the glib package) turns
    ``config.gresource.xml`` into a C source file that is linked in;
  * that tool is an ELF shipped without a ``.codesign`` section, which HMFS
    refuses to execve (EPERM → shell "Operation not permitted", exit 126), so
    a copy is staged into the test build dir and re-signed — the same shape the
    main recipe applies to its own build-time glib tools via
    ``_prepare_glib_build_tools`` (that staging lives in the *recipe's* build
    folder and is not on this consumer's path, hence the repetition here);
  * at run time the test binary pulls in ``libpolkit-gobject-1.so.0`` as a
    transitive NEEDED, which the conan cache ships as a **symlink** onto a
    versioned file with a stale ``.codesign`` → empty strerror load failure.
    ``_stage_resigned_sonames()`` materialises + re-signs it into the test build
    dir (again mirroring the main recipe, whose staging is likewise not on this
    process's search path); ``/system/lib64`` is appended for ``libz.so``;
  * glib is packaged together with its ``proxy-libintl`` subproject and does
    not declare ``intl`` as a system lib, so ``-lintl`` is added by hand;
  * the OHOS musl loader resolves neither DT_RUNPATH reliably nor
    LD_LIBRARY_PATH for the conan cache, so DT_RPATH entries are baked into the
    test binary with ``--disable-new-dtags``, and ``/system/bin/sh`` (mksh)
    cannot exec an ELF, hence the bash wrapper.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building

TEST_PROGRAM = "test_libgsystemservice"
RESOURCE_SOURCE = "config_resources.c"

HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")


class LibgsystemserviceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libgsystemservice declares systemd and polkit as *private*
        # (``visible=False``) requirements, so they do not propagate into a
        # consumer's dependency graph.  The consumer therefore never sees their
        # ``lib`` dirs, and dlopening the tested library dies before ``main()``:
        #
        #     Error loading shared library libsystemd.so.0:
        #         (needed by .../lib/libgsystemservice-0.so.0)
        #     Error loading shared library libpolkit-gobject-1.so.0: (needed by ...)
        #     Error relocating .../libgsystemservice-0.so.0: sd_notify: symbol not found
        #     Error relocating .../libgsystemservice-0.so.0: polkit_authority_get_sync: ...
        #     ConanException: Error 127 while executing
        #
        # (CI #62628).  Requiring them explicitly here re-admits their binaries to
        # this graph -- pinned to the very versions the recipe pins, so
        # ``libgsystemservice`` itself is not rebuilt -- which is what puts their
        # ``lib`` dirs on LD_LIBRARY_PATH and lets ``_stage_resigned_sonames()``
        # materialise + re-sign the symlinked SONAMEs they contribute (E073),
        # exactly as the main recipe's own test run already does.
        #
        # They must be re-declared ``visible=False``, mirroring the recipe.  A
        # *visible* re-declaration drags systemd's and polkit's own subgraphs
        # into this consumer's resolution, and Conan 2 then refuses the graph
        # outright:
        #
        #     ERROR: Version conflict: Conflict between zlib/1.3.1 and
        #     zlib/1.3.1.1 in the graph.  Conflict originates from systemd/261
        #
        # (CI #62656; polkit's glib/2.84.0 against the recipe's glib/2.84.0.1 is
        # the very next conflict in line, so pinning zlib with an override only
        # moves the error one step along rather than removing it).  With
        # ``visible=False`` the graph resolves exactly as the recipe's own does
        # -- zlib/1.3.1 and zlib/1.3.1.1 and zlib/1.3.2 coexisting -- while the
        # requirements still belong to *this* node, so ``self.dependencies.host``
        # keeps exposing their ``lib`` dirs; that is the same mechanism the
        # recipe's own staging uses to reach libsystemd.so.0 and
        # libpolkit-gobject-1.so.0.
        self.requires("systemd/261", visible=False)
        self.requires("polkit/127", visible=False)

    def _collect(self):
        """Include dirs / lib dirs / libs / system libs of every host dep."""
        incs, libdirs, libs, syslibs = [], [], [], []
        for dependency in self.dependencies.host.values():
            agg = dependency.cpp_info.aggregated_components()
            base = dependency.package_folder or ""
            for path in agg.includedirs:
                if not os.path.isabs(path):
                    path = os.path.join(base, path)
                if os.path.isdir(path) and path not in incs:
                    incs.append(path)
            for path in agg.libdirs:
                if not os.path.isabs(path):
                    path = os.path.join(base, path)
                if os.path.isdir(path) and path not in libdirs:
                    libdirs.append(path)
            for name in agg.libs:
                if name not in libs:
                    libs.append(name)
            for name in agg.system_libs:
                if name not in syslibs:
                    syslibs.append(name)
        return incs, libdirs, libs, syslibs

    def _find_host_tool(self, tool_name):
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin", tool_name)
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(tool_name)

    def _sign_elf(self, binary):
        """HMFS 执行限制规避：去掉 .codesign 段后 selfSign 重签。"""
        if os.path.isfile(OBJCOPY):
            self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                     f"{shlex.quote(binary)} 2>/dev/null || true")
        if os.path.isfile(SIGN_TOOL):
            self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", binary,
                                 "-outFile", binary, "-selfSign", "1"]))

    def _staged_tool(self, tool_name):
        """Resolve a glib build tool, re-signing a staged copy on OHOS.

        The glib package's ``bin/glib-compile-resources`` carries no valid
        ``.codesign`` section, so HMFS execve fails with EPERM (shell reports
        "Operation not permitted", exit code 126).  The conan cache stays
        read-only: a copy is staged into the test build dir and re-signed,
        mirroring the main recipe's ``_prepare_glib_build_tools``.
        """
        source = self._find_host_tool(tool_name)
        if not source:
            raise ConanException(
                f"{tool_name} not found in any dependency bin/ dir")
        if self.settings.os != "OHOS":
            return source
        staged_dir = os.path.join(self.build_folder, "conan-native-tools")
        os.makedirs(staged_dir, exist_ok=True)
        target = os.path.join(staged_dir, tool_name)
        if not os.path.isfile(target):
            shutil.copyfile(source, target)
            os.chmod(target, 0o755)
            self._sign_elf(target)
        return target

    def _ld_library_path(self):
        """LD_LIBRARY_PATH for running anything against this graph.

        Staged re-signed SONAMEs first, then every dependency libdir, then
        ``/system/lib64``.  The staging is not optional: the glib package's
        ``libglib-2.0.so.0`` is a **symlink** onto ``libglib-2.0.so.0.8400.x``
        and HMFS cannot dlopen symlinked SONAMEs (E073), so the loader skips
        the conan copy and falls through to ``/system/lib64``'s much older
        GLib -- which then fails every relocation for symbols added since:

            Error relocating .../glib-compile-resources:
                g_mapped_file_new: symbol not found
            ...
            ConanException: Error 127 while executing

        (this is how the *build tool* died on CI #62609, after the tool itself
        had already been staged + re-signed; the tool's own NEEDED libs need
        the same treatment as the test binary's).
        """
        dirs = []
        staged = self._stage_resigned_sonames()
        if staged:
            dirs.append(staged)
        dirs.extend(self._dependency_libdirs())
        dirs.append("/system/lib64")
        return os.pathsep.join(dirs)

    def _compile_resources(self):
        """Turn config.gresource.xml into a linkable C source file."""
        compiler = self._staged_tool("glib-compile-resources")
        self.run(f'export LD_LIBRARY_PATH="{self._ld_library_path()}"; '
                 f'"{compiler}" '
                 f'"{os.path.join(self.source_folder, "config.gresource.xml")}" '
                 f'--generate-source --c-name=consumer_resources '
                 f'--target="{os.path.join(self.build_folder, RESOURCE_SOURCE)}"')
        return os.path.join(self.build_folder, RESOURCE_SOURCE)

    def build(self):
        incs, libdirs, libs, syslibs = self._collect()
        self.output.info(f"includes: {incs}")
        self.output.info(f"libdirs: {libdirs}")
        self.output.info(f"libs: {libs} + system {syslibs}")

        resources = self._compile_resources()

        flags = []
        flags += ["-I" + p for p in incs]
        flags += ["-L" + p for p in libdirs]
        flags += ["-l" + l for l in libs]
        flags += ["-l" + l for l in syslibs]
        # glib's proxy-libintl: g_libintl_* must be linked explicitly.
        if self.settings.os == "OHOS":
            flags += ["-lintl"]
            flags += ["-Wl,--disable-new-dtags"]
            flags += ["-Wl,-rpath," + p for p in libdirs]

        cc = os.environ.get("CC", "clang")
        self.run(f'{cc} -std=gnu11 -O1 -Wall '
                 f'-o {TEST_PROGRAM} test.c "{resources}" ' + " ".join(flags))

    def _dependency_libdirs(self):
        """Existing ``lib`` directories of every host dependency, deduplicated."""
        libdirs = []
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir) and libdir not in libdirs:
                    libdirs.append(libdir)
        return libdirs

    def _stage_resigned_sonames(self):
        """Materialise + re-sign symlinked dependency SONAMEs for the OHOS loader.

        ``libpolkit-gobject-1.so.0`` (a NEEDED of ``libgsystemservice-0.so.0``)
        is a **symlink** onto ``libpolkit-gobject-1.so.0.0.0``, which carries a
        stale ``.codesign`` section; the OHOS kernel refuses to mmap it and the
        musl loader surfaces that as

            Error loading shared library libpolkit-gobject-1.so.0:
                (needed by .../libgsystemservice-0.so.0)

        with an **empty** strerror (区别于真缺失时的 ``No such file or
        directory`` 与未签名 ELF 的 ``Permission denied``).

        Materialising alone is NOT enough — the same PR's A/B on 2026-09-27
        showed libratbag/0.18 going FAIL with a plain copy and PASS once the
        copy was re-signed.  The conan cache stays read-only: the real file is
        copied into the test build dir, the stale signature dropped with
        ``llvm-objcopy`` and re-created with ``binary-sign-tool -selfSign 1``.
        The caller prepends that directory to ``LD_LIBRARY_PATH``.
        """
        staged = os.path.join(self.build_folder, "conan-staged-soname-libs")
        materialised = []
        for libdir in self._dependency_libdirs():
            for name in sorted(os.listdir(libdir)):
                if not name.endswith(".so") and ".so." not in name:
                    continue
                source = os.path.join(libdir, name)
                if not os.path.islink(source):
                    continue
                target = os.path.join(staged, name)
                if os.path.exists(target):
                    continue
                real = os.path.realpath(source)
                if not os.path.isfile(real):
                    continue
                os.makedirs(staged, exist_ok=True)
                shutil.copy2(real, target)  # copy2 follows the link → payload
                os.chmod(target, 0o755)
                self._sign_elf(target)
                materialised.append(name)
        # The staging directory is a session-level artefact: ``build()`` reaches
        # it through ``_compile_resources()`` and ``test()`` reaches it again
        # through ``_ld_library_path()``.  It must therefore be returned
        # whenever it *exists*, not only when *this* call happened to
        # materialise something -- on the second call every target is already
        # present, ``materialised`` stays empty, and returning None here drops
        # the staged copies from ``LD_LIBRARY_PATH``.  The loader then falls
        # back to the symlinked conan SONAMEs, which is the very failure this
        # staging exists to avoid (CI #62669: the compile step got the staged
        # dir but the run step did not, so
        #
        #     Error loading shared library libpolkit-gobject-1.so.0:
        #         (needed by .../lib/libgsystemservice-0.so.0)
        #     Error relocating .../libgsystemservice-0.so.0:
        #         polkit_authority_get_sync: symbol not found
        #     ConanException: Error 127 while executing
        #
        # even though all ten re-signed copies were sitting on disk).
        if not os.path.isdir(staged):
            return None
        if materialised:
            self.output.info(
                "E073: materialised + re-signed %d symlinked SONAMEs into %s (%s)"
                % (len(materialised), staged, ", ".join(materialised)))
        else:
            self.output.info(
                "E073: reusing SONAMEs already staged in %s" % staged)
        return staged

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verifying compile+link")
            return
        _, libdirs, _, _ = self._collect()
        # polkit's libpolkit-gobject-1.so.0 has libz.so as its only external
        # DT_NEEDED, and the conan zlib package ships a static libz.a only, so
        # libz.so can only come from /system/lib64.  Append (not prepend) so a
        # system glib/expat cannot shadow the conan ones -- _ld_library_path()
        # already does exactly that (staged SONAMEs, dep libdirs, /system/lib64).
        ldpath = self._ld_library_path()
        # /tmp is not writable on the target and the test creates a temporary
        # directory, so hand it one inside the build tree.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        self.run(
            f'{bash} -c \'export LD_LIBRARY_PATH="{ldpath}'
            f'${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; '
            f'export TMPDIR="{tmpdir}"; '
            f'"./{TEST_PROGRAM}"\'',
            env="conanrun")
