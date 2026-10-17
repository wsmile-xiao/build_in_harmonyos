import os
import re
import shlex
import struct

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv

# Host loader failure signatures, matching the main recipe. test_package
# drives the same C compiler through CMake's compiler check, and uses the
# same environment model as the main recipe: probes are dispatched
# through self.run(..., env="conanbuild") — the same sourced launcher
# path cmake.configure() takes — so profile buildenv, VirtualBuildEnv,
# PATH and LD_LIBRARY_PATH are exactly what CMake's compiler check and
# cmake.configure() will see (musl ldso / glibc ld.so formats).
_MISSING_LIB_PATTERNS = (
    # musl ldso: "Error loading shared library libxml2.so.16: ..."
    re.compile(r"Error loading shared library ([\w.\-+]+):"),
    # glibc ld.so: "libxml2.so.16: cannot open shared object file"
    re.compile(r"([\w.\-+]+\.so[\w.\-]*): cannot open shared object file"),
    # musl ldso relocation failure when a SONAME resolves to a wrong-ABI
    # file (e.g. the OHOS libxml2.so.16 picked up ahead of the host one):
    # "Error relocating /path/to/ld.lld: symbol not found". The library
    # to recover is the one whose name appears in the message path.
    re.compile(r"Error relocating [\w./\-+]*/([\w.\-+]+\.so[\w.\-]*):"),
)


def _parse_needed(elf_path):
    """Direct ELF DT_NEEDED parser (no external ldd): read the dynamic
    table of an ELF and return its DT_NEEDED SONAMEs. Used when the
    loader reports a relocation failure against a binary — the message
    names the binary, not the offending library, so its NEEDED list
    identifies which host library the recovery dir must supply.
    d_val of DT_NEEDED is an index into DT_STRTAB (itself a vaddr),
    translated to a file offset via the PT_LOAD segments."""
    needed = []
    try:
        with open(elf_path, "rb") as handle:
            data = handle.read()
    except OSError:
        return needed
    if data[:4] != b"\x7fELF" or len(data) < 64:
        return needed
    is_64 = data[4] == 2
    if data[5] != 1:  # little endian only
        return needed
    if is_64:
        e_phoff, e_shoff = struct.unpack_from("<QQ", data, 0x20)
        e_phentsize, e_phnum = struct.unpack_from("<HH", data, 0x36)
        e_shentsize, e_shnum = struct.unpack_from("<HH", data, 0x3A)
    else:
        e_phoff, e_shoff = struct.unpack_from("<II", data, 0x1C)
        e_phentsize, e_phnum = struct.unpack_from("<HH", data, 0x2A)
        e_shentsize, e_shnum = struct.unpack_from("<HH", data, 0x2E)

    def vaddr_to_off(vaddr):
        for index in range(e_phnum):
            offset = e_phoff + index * e_phentsize
            if is_64:
                p_type, _p_flags, p_offset, p_vaddr, _pa, p_filesz = (
                    struct.unpack_from("<IIQQQQ", data, offset)
                )
            else:
                p_type, p_offset, p_vaddr, p_filesz = struct.unpack_from(
                    "<IIII", data, offset
                )
            if p_type == 1 and p_vaddr <= vaddr < p_vaddr + p_filesz:
                return vaddr - p_vaddr + p_offset
        return None

    # SHT_DYNAMIC == 6
    for index in range(e_shnum):
        offset = e_shoff + index * e_shentsize
        sh_type = struct.unpack_from(
            "<I", data, offset + 4
        )[0]
        if sh_type != 6:
            continue
        if is_64:
            sh_offset, sh_size = struct.unpack_from("<QQ", data, offset + 0x18)
        else:
            sh_offset, sh_size = struct.unpack_from("<II", data, offset + 0x14)
        strtab = None
        needed_idx = []
        stride = 16 if is_64 else 8
        for pos in range(sh_offset, sh_offset + sh_size, stride):
            if is_64:
                tag, value = struct.unpack_from("<qQ", data, pos)
            else:
                tag, value = struct.unpack_from("<iI", data, pos)
            if tag == 0:
                break
            if tag == 5:
                strtab = value
            elif tag == 1:
                needed_idx.append(value)
        if strtab is None:
            return needed
        strtab_off = vaddr_to_off(strtab)
        if strtab_off is None:
            return needed
        for name_idx in needed_idx:
            file_off = strtab_off + name_idx
            try:
                name_end = data.index(b"\x00", file_off)
                name = data[file_off:name_end].decode("utf-8", "replace")
                if name:
                    needed.append(name)
            except (ValueError, UnicodeDecodeError):
                pass
        break
    return needed


def _missing_host_libraries(stderr):
    found = []
    for pattern in _MISSING_LIB_PATTERNS:
        found.extend(pattern.findall(stderr or ""))
    # musl relocation failures name the binary, not the library: resolve
    # each named binary to its DT_NEEDED and report those as the missing
    # host libraries the recovery directory must provide.
    reloc_binaries = re.findall(r"Error relocating ([\w./\-+]+):", stderr or "")
    for binary in reloc_binaries:
        if os.path.isfile(binary):
            found.extend(_parse_needed(binary))
    return list(dict.fromkeys(found))


def _shell_quote(value):
    return shlex.quote(value)


class LibsvgCairoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # svg-cairo.h includes svg.h and cairo.h directly, so the test
        # also requires both public dependencies of libsvg-cairo.
        self.requires("libsvg/0.1.4")
        self.requires("cairo/1.18.4")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    # ------------------------------------------------------------------
    # Host toolchain runtime recovery (same E429 failure class and the
    # same environment model as the main recipe): CMake's "compiler is
    # able to compile a simple test program" check compiles and links
    # with the same clang/ld.lld whose host shared libraries may not
    # resolve. Probe first — inside the conanbuild environment; recover
    # only from libdirs derived from the live toolchain; verify with the
    # same probe; fail closed otherwise.
    # ------------------------------------------------------------------

    def _host_cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c") or ""

    def _run_query(self, args, env_files=None):
        """Run a compiler query (e.g. -print-prog-name, -print-resource-dir)
        inside the conanbuild environment via self.run(); returns stdout
        text or "" on failure. These driver flags print and exit before
        linking anything, so a broken host loader runtime is not
        exercised by them."""
        probe_dir = os.path.join(self.build_folder, ".cc-probe")
        os.makedirs(probe_dir, exist_ok=True)
        stdout_path = os.path.join(probe_dir, "query.out")
        stderr_path = os.path.join(probe_dir, "query.stderr")
        for path in (stdout_path, stderr_path):
            if os.path.isfile(path):
                os.remove(path)
        command = "{} >{} 2>{}".format(
            " ".join(_shell_quote(a) for a in args),
            _shell_quote(stdout_path),
            _shell_quote(stderr_path),
        )
        try:
            self.run(
                command,
                env=env_files or "conanbuild",
                quiet=True,
                ignore_errors=True,
            )
        except ConanException:
            return ""
        except (OSError, Exception):
            return ""
        try:
            with open(stdout_path, "r", encoding="utf-8", errors="replace") as handle:
                return handle.read().strip()
        except OSError:
            return ""

    def _run_cc_probe(self, cc, extra_libdir=""):
        """Compile and link a minimal C program with the compiler CMake
        will drive, inside the exact environment CMake will run in: the
        command is dispatched through self.run() with env="conanbuild",
        so profile buildenv, VirtualBuildEnv, the current PATH and the
        current LD_LIBRARY_PATH all apply exactly as they will for
        cmake.configure(). The effective PATH / LD_LIBRARY_PATH are
        captured *inside* the sourced launcher shell (printenv), so the
        log shows what the compiler really saw. A recovery libdir is
        injected by sourcing a generated env script *after*
        conanbuild.sh (self.run accepts an ordered env list), never by
        mutating os.environ. musl wrappers can mask loader failures
        with a zero exit status, so success requires all of: exit code
        0, a real ELF on disk, and no loader error on stderr."""
        probe_dir = os.path.join(self.build_folder, ".cc-probe")
        os.makedirs(probe_dir, exist_ok=True)
        source = os.path.join(probe_dir, "probe.c")
        output = os.path.join(probe_dir, "probe.out")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write("int main(void) { return 0; }\n")
        if os.path.isfile(output):
            os.remove(output)
        env_files = ["conanbuild"]
        if extra_libdir:
            # Scoped recovery env: sourced after conanbuild.sh so its
            # LD_LIBRARY_PATH prepend wins, without touching the outer
            # process environment.
            recovery_sh = os.path.join(probe_dir, "hostrecovery.sh")
            with open(recovery_sh, "w", encoding="utf-8") as handle:
                handle.write(
                    'export LD_LIBRARY_PATH="{}{}$LD_LIBRARY_PATH"\n'.format(
                        extra_libdir, os.pathsep
                    )
                )
            env_files.append(recovery_sh)
            self.output.info(
                f"Host compiler probe: recovery LD_LIBRARY_PATH prepend={extra_libdir}"
            )

        stdout_path = os.path.join(probe_dir, "probe.stdout")
        stderr_path = os.path.join(probe_dir, "probe.stderr")
        for path in (stdout_path, stderr_path):
            if os.path.isfile(path):
                os.remove(path)
        command = (
            "printenv PATH > {stdout} 2>{stderr}; "
            "printenv LD_LIBRARY_PATH >> {stdout} 2>/dev/null; "
            "{cc} {src} -o {out} 2>> {stderr}"
        ).format(
            stdout=_shell_quote(stdout_path),
            stderr=_shell_quote(stderr_path),
            cc=_shell_quote(cc),
            src=_shell_quote(source),
            out=_shell_quote(output),
        )
        try:
            self.run(command, env=env_files, ignore_errors=True, quiet=True)
            returncode = 0
        except ConanException as error:
            # ConanFile.run raises ConanException("Error %d while
            # executing") on non-zero exit; parse the code back out.
            match = re.search(r"Error (\d+) while executing", str(error))
            returncode = int(match.group(1)) if match else -1
        except (OSError, Exception) as error:
            return -1, str(error), False, "", ""

        stderr = ""
        try:
            with open(stderr_path, "r", encoding="utf-8", errors="replace") as handle:
                stderr = handle.read()
        except OSError:
            pass
        effective_path, effective_ldlp = "", ""
        try:
            with open(stdout_path, "r", encoding="utf-8", errors="replace") as handle:
                captured = handle.read().splitlines()
            if captured:
                effective_path = captured[0]
            if len(captured) > 1:
                effective_ldlp = captured[1]
        except OSError:
            pass
        self.output.info(f"Host compiler probe: CC={cc}")
        self.output.info(f"Host compiler probe: PATH={effective_path or '<unset>'}")
        self.output.info(
            f"Host compiler probe: LD_LIBRARY_PATH={effective_ldlp or '<unset>'}"
        )
        is_elf = False
        try:
            with open(output, "rb") as handle:
                is_elf = handle.read(4) == b"\x7fELF"
        except OSError:
            pass
        return returncode, stderr, is_elf, effective_path, effective_ldlp

    def _linker_path(self, cc):
        """Absolute path of the linker the driver would use, or ""."""
        lld = self._run_query([cc, "-print-prog-name=ld.lld"])
        if not lld or lld == "ld.lld":  # clang echoes the name when unresolved
            return ""
        if not os.path.isabs(lld):
            beside = os.path.join(os.path.dirname(os.path.realpath(cc)), lld)
            lld = beside if os.path.isfile(beside) else ""
        return os.path.realpath(lld) if lld else ""

    def _archiver_path(self, cc):
        """Absolute path of the archiver (llvm-ar) the driver would use,
        or "". Same -print-prog-name query model as _linker_path: the
        driver prints and exits, so a broken host loader runtime is not
        exercised."""
        ar = self._run_query([cc, "-print-prog-name=llvm-ar"])
        if not ar or ar == "llvm-ar":  # clang echoes the name when unresolved
            return ""
        if not os.path.isabs(ar):
            beside = os.path.join(os.path.dirname(os.path.realpath(cc)), ar)
            ar = beside if os.path.isfile(beside) else ""
        elif not os.path.isfile(ar):
            return ""
        return os.path.realpath(ar) if ar else ""

    def _tool_path(self, cc, name, alternatives=()):
        """Absolute path of a binutils-style tool the compiler toolchain
        ships (readelf, llvm-readelf, ...), or "". Same query model as
        _archiver_path: -print-prog-name prints and exits before any
        linking. The driver only resolves tools it actually drives — a
        plain binutils name can come back unresolved (echoed as given or
        with a non-absolute path), so every candidate is additionally
        looked up beside the compiler. No hardcoded install paths."""
        queried = self._run_query([cc, f"-print-prog-name={name}"])
        for candidate in (queried, *alternatives):
            if not candidate:
                continue
            resolved = candidate
            if not os.path.isabs(resolved):
                beside = os.path.join(
                    os.path.dirname(os.path.realpath(cc)), resolved
                )
                resolved = beside if os.path.isfile(beside) else ""
            if resolved and os.path.isfile(resolved):
                return os.path.realpath(resolved)
        return ""

    def _candidate_libdirs(self, cc):
        """Host libdirs derived from the live toolchain layout only."""
        cc_bin = os.path.dirname(os.path.realpath(cc))
        cc_root = os.path.dirname(cc_bin)
        dirs = [cc_bin, os.path.join(cc_root, "lib")]
        resource_dir = self._run_query([cc, "-print-resource-dir"])
        # <toolchain>/lib/clang/<version> -> <toolchain>/lib
        if resource_dir:
            dirs.append(os.path.dirname(os.path.dirname(resource_dir)))
        linker = self._linker_path(cc)
        if linker:
            linker_bin = os.path.dirname(linker)
            dirs.append(linker_bin)
            dirs.append(os.path.join(os.path.dirname(linker_bin), "lib"))
        unique = []
        for entry in dirs:
            resolved = os.path.realpath(entry)
            if os.path.isdir(resolved) and resolved not in unique:
                unique.append(resolved)
        return unique

    def _host_toolchain_libdir(self):
        """Libdir that restores the host toolchain runtime, "" when the
        compiler already links fine, or fail closed with
        ConanInvalidConfiguration when the compiler is broken by host
        libraries no toolchain libdir provides.

        The probes are dispatched through self.run(..., env="conanbuild")
        — the exact same launcher path cmake.configure() takes, so the
        probe verdict holds for CMake's compiler check. Deliberately NOT
        VirtualBuildEnv(...).vars().apply(): apply() writes profile
        values into os.environ verbatim, and a profile that uses ${PATH}
        placeholders then poisons the process PATH with the literal
        string — the failure mode this recovery exists to fix."""
        if str(self.settings.os) != "OHOS":
            return ""
        cached = getattr(self, "_recovered_host_libdir", None)
        if cached is not None:
            return cached

        cc = self._host_cc()
        if not cc:
            self.output.info(
                "tools.build:compiler_executables defines no C compiler; "
                "skipping host toolchain probe"
            )
            self._recovered_host_libdir = ""
            return ""

        self.output.info("Host compiler probe: first probe in conanbuild environment")
        returncode, stderr, is_elf, _, _ = self._run_cc_probe(cc)
        missing = _missing_host_libraries(stderr)
        self.output.info(
            "Host compiler probe: exitcode={} elf={} missing={}".format(
                returncode, is_elf, missing or "<none>"
            )
        )
        if returncode == 0 and is_elf and not missing:
            self._recovered_host_libdir = ""
            return ""
        if not missing:
            # Not a missing-host-library failure; CMake's own error
            # is authoritative for every other cause.
            self.output.warning(
                "Host compiler probe failed for a non-library reason; leaving "
                f"the diagnosis to CMake: {stderr.strip()!r}"
            )
            self._recovered_host_libdir = ""
            return ""

        candidates = self._candidate_libdirs(cc)
        for libdir in candidates:
            provides = [lib for lib in missing if os.path.isfile(os.path.join(libdir, lib))]
            if not provides:
                continue
            self.output.info(
                f"Host compiler probe: recovery candidate {libdir} provides {', '.join(provides)}"
            )
            returncode, stderr, is_elf, _, _ = self._run_cc_probe(
                cc, extra_libdir=libdir
            )
            self.output.info(
                "Host compiler probe: recovery exitcode={} elf={}".format(
                    returncode, is_elf
                )
            )
            if returncode == 0 and is_elf and not _missing_host_libraries(stderr):
                self.output.info(
                    f"Recovered host toolchain runtime (missing: {', '.join(missing)}) from {libdir}"
                )
                self._recovered_host_libdir = libdir
                return libdir
            self.output.info(
                f"Host compiler probe: candidate {libdir} did not fix the probe; trying next"
            )

        self._fail_closed_host_probe(cc, missing, candidates, stderr)

    def _host_tool_runtime_ld_library_path(self):
        """LD_LIBRARY_PATH the HOST toolchain binaries (clang / ld.lld /
        llvm-ar / readelf driven by test_ohos.sh) need to run — and ONLY
        that, never the target dependency libdirs.

        test_ohos.sh is dispatched with env="conanrun", whose
        LD_LIBRARY_PATH prepends the TARGET dependency package lib dirs.
        On a worker where those precede the toolchain's own runtime, the
        host lld loads the target libxml2.so.16 and dies on relocation
        (CI #42924). The fix is an environment split: the host tools get
        their runtime via the dedicated OHOS_TOOL_LD_LIBRARY_PATH
        variable, while target dependency resolution stays on -L flags /
        absolute paths, and LD_LIBRARY_PATH is only exported when
        actually RUNNING the target consumer.

        Sources, in order (no hardcoded SDK / conan-cache / machine
        paths):
        1. the E429-style recovery libdir probed from the live toolchain
           (the same libdir build() already prepends for CMake);
        2. the conanbuild environment's own LD_LIBRARY_PATH, composed via
           VirtualBuildEnv — exactly what conanbuild.sh sources, so
           profile [buildenv] entries like the OHOS SDK llvm/lib dir are
           included (a bare Environment() would see none of them).
        Target dependency libdirs are filtered out defensively, so the
        split holds even if a dependency leaks its libdir into the
        build environment. Deduplicated, order-preserving. Empty string
        when the host tools need nothing extra (script then runs them
        with an empty LD_LIBRARY_PATH, which is also correct)."""
        entries = []
        libdir = self._host_toolchain_libdir()
        if libdir:
            entries.append(libdir)
        target_dirs = set()
        for dep in self.dependencies.host.values():
            for d in dep.cpp_info.aggregated_components().libdirs:
                target_dirs.add(os.path.realpath(d))
        build_ldlp = (
            VirtualBuildEnv(self).vars().get("LD_LIBRARY_PATH") or ""
        )
        for entry in build_ldlp.split(os.pathsep):
            if not entry or entry in entries:
                continue
            if os.path.realpath(entry) in target_dirs:
                self.output.warning(
                    "Host tool runtime: excluding target dependency "
                    f"libdir {entry} from OHOS_TOOL_LD_LIBRARY_PATH"
                )
                continue
            entries.append(entry)
        return os.pathsep.join(entries)

    def _fail_closed_host_probe(self, cc, missing, candidates, stderr):
        details = [
            "Host toolchain probe failed and could not be recovered:",
            f"  compiler: {cc} (realpath: {os.path.realpath(cc)})",
            f"  linker: {self._linker_path(cc) or '<unresolved>'}",
            f"  missing host libraries: {', '.join(missing)}",
            f"  candidate libdirs: {candidates or '<none>'}",
            "  probe stderr:",
        ]
        details.extend(f"    {line}" for line in (stderr or "<empty>").splitlines())
        # CMake's counterpart of config.log, present when an earlier
        # configure already ran in this build folder.
        for relative in (
            os.path.join("CMakeFiles", "CMakeError.log"),
            os.path.join("CMakeFiles", "CMakeConfigureLog.yaml"),
        ):
            log = os.path.join(self.build_folder, relative)
            if os.path.isfile(log):
                try:
                    with open(log, "r", encoding="utf-8", errors="replace") as handle:
                        tail = handle.readlines()[-40:]
                except OSError:
                    tail = []
                if tail:
                    details.append(f"  {relative} tail:")
                    details.extend(f"    {line.rstrip()}" for line in tail)
                break
        raise ConanInvalidConfiguration("\n".join(details))

    def _build_environment(self):
        """Scoped environment for CMake configure/build. Only the host
        toolchain recovery libdir is added: dependency resolution goes
        through CMakeDeps -L/-I flags at link time and through conanrun
        (VirtualRunEnv) at run time, neither of which needs this."""
        environment = Environment()
        libdir = self._host_toolchain_libdir()
        if libdir:
            environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def build(self):
        # Same environment model as the main recipe: probes already ran
        # through self.run(env="conanbuild"); cmake.configure()/build()
        # take the same launcher path. The scoped Environment below only
        # adds the recovery LD_LIBRARY_PATH (never PATH), which the
        # sourced conanbuild.sh inherits from the process.
        environment = self._build_environment()
        with environment.vars(self, scope="build").apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        # TAP-style runner: prints "1..N" and exits non-zero on failure.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"), env="conanrun")
        # OHOS-specific test (rule12): takes the FINAL package artifact
        # (the static archive libsvg-cairo.a from the conan cache
        # package_folder) as input, verifies the archive members'
        # architecture directly (ar archive + ELF64 LE AArch64 REL
        # members), then links consumer ELF artifacts from it (a derived
        # shared library and an executable) and runs the OHOS property
        # and runtime checks on those consumer artifacts (SONAME on the
        # derived .so; INTERP / .code_signature / host-path-free NEEDED
        # and the real SVG parse+render flow on the executable).
        # The static archive itself has no SONAME/INTERP/code_signature.
        # Fails closed on any assertion (no skip, no silent pass).
        # Locate the tested package folder (VirtualRunEnv does not export
        # CONAN_LIB_DIRS_* variables, same pattern as bambootracker 0.6.5).
        pkg = self.dependencies[self.tested_reference_str]
        pkg_lib = os.path.join(pkg.package_folder, *pkg.cpp_info.libdirs)
        pkg_inc = os.path.join(pkg.package_folder, *pkg.cpp_info.includedirs)
        dep_libs = ":".join(
            os.path.join(d.package_folder, *d.cpp_info.libdirs)
            for d in self.dependencies.host.values()
        )
        dep_incs = ":".join(
            os.path.join(d.package_folder, *d.cpp_info.includedirs)
            for d in self.dependencies.host.values()
        )
        # The bash that runs test_ohos.sh: prefer the profile buildenv
        # CONFIG_SHELL (the OHOS bash); a plain "bash" from PATH is the
        # universal fallback, so no install location is hardcoded.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        if not (bash != "bash" and os.path.exists(bash)):
            bash = "bash"  # resolve through PATH (conanrun preserves it)
        # Archiver and readelf for test_ohos.sh, both asked from the OHOS
        # clang driver (-print-prog-name prints and exits, no linking).
        # Empty results let the script fall back (AR env / PATH / tools
        # beside the compiler).
        ohos_ar = ""
        ohos_readelf = ""
        cc = self._host_cc()
        if cc:
            ohos_ar = self._archiver_path(cc)
            ohos_readelf = self._tool_path(cc, "readelf", ("llvm-readelf",))
        # Host-tool runtime, kept separate from the conanrun (target)
        # LD_LIBRARY_PATH: test_ohos.sh sources it into OHOS_TOOL_LD_
        # LIBRARY_PATH and only applies it to clang/lld/llvm-ar/readelf
        # invocations, so the target dependency dirs in conanrun can
        # never leak into the host loader path again (CI #42924).
        tool_ldlp = self._host_tool_runtime_ld_library_path()
        # The compiler itself is passed explicitly too (OHOS_CC): the
        # profile's tools.build:compiler_executables is the only source
        # of truth, and conanrun does not export CC. The script resolves
        # readelf from OHOS_READELF / PATH / the compiler's own bin dir.
        self.run(
            f"env OHOS_PKG_LIBDIR={_shell_quote(pkg_lib)}"
            f" OHOS_PKG_INCDIR={_shell_quote(pkg_inc)}"
            f" OHOS_DEP_LIBS={_shell_quote(dep_libs)}"
            f" OHOS_DEP_INCS={_shell_quote(dep_incs)}"
            f" OHOS_CC={_shell_quote(cc)}"
            f" OHOS_AR={_shell_quote(ohos_ar)}"
            f" OHOS_READELF={_shell_quote(ohos_readelf)}"
            f" OHOS_TOOL_LD_LIBRARY_PATH={_shell_quote(tool_ldlp)}"
            f" {bash} {os.path.join(self.source_folder, 'test_ohos.sh')}",
            env="conanrun")
