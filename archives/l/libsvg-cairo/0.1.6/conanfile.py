#!/usr/bin/env python3
"""Conan recipe for libsvg-cairo 0.1.6 — cairo backend for libsvg.

Renders SVG documents parsed by libsvg onto cairo surfaces. Adapted for
HarmonyOS PC (aarch64). License: LGPL-2.0-or-later.
"""
import glob as _glob
import os
import re
import shlex
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Host loader failure signatures (musl ldso / glibc ld.so).
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


class LibsvgCairoConan(ConanFile):
    name = "libsvg-cairo"
    version = "0.1.6"
    description = "Cairo backend for libsvg: renders SVG documents onto cairo surfaces"
    license = "LGPL-2.0-or-later"
    homepage = "https://cairographics.org/"
    url = "https://cairographics.org/snapshots/"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # VirtualBuildEnv is generated explicitly in generate() so the
    # probe/recovery machinery can reason about the very same launcher.
    generators = "AutotoolsDeps", "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.in: PKG_CHECK_MODULES(LIBSVG_CAIRO, libsvg >= 0.1.2 cairo >= 0.5.0)
        # Only the public libsvg API is used (svg.h, no svgint.h).
        self.requires("libsvg/0.1.4")
        self.requires("cairo/1.18.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generate the conanbuildenv-*.sh launcher. This, composed with
        # profile buildenv and toolchain env, is the exact environment
        # autotools.configure() runs in (self.run() sources conanbuild.sh,
        # which sources conanbuildenv-*.sh), and is therefore the only
        # environment model the probes below may use.
        buildenv = VirtualBuildEnv(self)
        buildenv.generate()
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # The 2005-era configure only knows linux-gnu; supply the OHOS cross
        # target explicitly (config.guess/config.sub are patched for ohos).
        if self.settings.os == "OHOS":
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        # AC_PATH_XTRA probes for X11; svg-cairo renders onto any cairo
        # surface (image surfaces included) and needs no X11 at build or
        # run time. Silence the probe so headless builds do not pick up
        # host X11 paths.
        tc.configure_args.append("--without-x")
        tc.generate()

    # ------------------------------------------------------------------
    # Host toolchain runtime recovery. On the OHOS CI the active HNP
    # clang/ld.lld fail to even start when their own host shared
    # libraries (e.g. libxml2.so.16) cannot be resolved, which makes
    # configure abort with "C compiler cannot create executables" before
    # any recipe logic runs. The helpers below probe the exact compiler
    # configure will use; only when that probe fails on missing host
    # libraries do they search libdirs derived from the live toolchain
    # itself and re-verify with the same probe.
    # ------------------------------------------------------------------

    def _host_cc(self):
        """C compiler configure will drive, resolved through the same
        conanbuild environment (profile buildenv composes tools.build:
        compiler_executables into CC, and AutotoolsToolchain defines CC
        from that conf)."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c") or ""

    def _run_cc_probe(self, cc, extra_libdir=""):
        """Compile and link a minimal C program with the compiler that
        configure will drive, inside the exact environment configure
        will run in: the command is dispatched through self.run() with
        env="conanbuild", so profile buildenv, VirtualBuildEnv, the
        current PATH and the current LD_LIBRARY_PATH all apply exactly
        as they will for autotools.configure(). The effective PATH /
        LD_LIBRARY_PATH are captured *inside* the sourced launcher
        shell (printenv), so the log shows what the compiler really
        saw, not what the outer Python process happens to export.
        A recovery libdir is injected by sourcing a generated env script
        *after* conanbuild.sh (self.run accepts an ordered env list),
        never by mutating os.environ. musl wrappers can mask loader
        failures with a zero exit status, so success requires all of:
        exit code 0, a real ELF on disk, and no loader error on
        stderr."""
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
            self.run(
                command,
                env=env_files,
                stdout=subprocess.DEVNULL if hasattr(subprocess, "DEVNULL") else None,
                ignore_errors=True,
                quiet=True,
            )
            returncode = 0
        except ConanException as error:
            # ConanFile.run raises ConanException("Error %d while
            # executing") on non-zero exit; parse the code back out.
            match = re.search(r"Error (\d+) while executing", str(error))
            returncode = int(match.group(1)) if match else -1
        except (OSError, subprocess.SubprocessError) as error:
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

    def _run_query(self, args, env_files=None):
        """Run a compiler query (e.g. -print-prog-name, -print-resource-dir)
        inside the conanbuild environment via self.run(); returns stdout
        text or "" on failure. Querying the compiler here is safe: these
        flags make the driver print and exit before linking anything, so
        a broken host loader runtime is not exercised by them."""
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
        except (OSError, subprocess.SubprocessError):
            return ""
        try:
            with open(stdout_path, "r", encoding="utf-8", errors="replace") as handle:
                return handle.read().strip()
        except OSError:
            return ""

    def _linker_path(self, cc):
        """Absolute path of the linker the driver would use, or ""."""
        lld = self._run_query([cc, "-print-prog-name=ld.lld"])
        if not lld or lld == "ld.lld":  # clang echoes the name when unresolved
            return ""
        if not os.path.isabs(lld):
            beside = os.path.join(os.path.dirname(os.path.realpath(cc)), lld)
            lld = beside if os.path.isfile(beside) else ""
        return os.path.realpath(lld) if lld else ""

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
        — the exact same launcher path autotools.configure() takes
        (ConanFile.run wraps the command with `. conanbuild.sh`, which
        sources conanbuildenv-*.sh and the toolchain env scripts). This
        is what makes the probe verdict valid for configure: identical
        PATH (profile buildenv placeholders expand in the sourced
        shell), identical LD_LIBRARY_PATH, identical CC.

        Deliberately NOT VirtualBuildEnv(...).vars().apply(): apply()
        writes profile values into os.environ verbatim, and a profile
        that uses ${PATH} placeholders (like this CI's) then poisons the
        process PATH with the literal string — the very failure mode of
        CI #39358. The sourced-launcher path expands such placeholders
        correctly, so only that path is used."""
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
            # Not a missing-host-library failure; configure's own error
            # is authoritative for every other cause.
            self.output.warning(
                "Host compiler probe failed for a non-library reason; leaving "
                f"the diagnosis to configure: {stderr.strip()!r}"
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
        config_log = os.path.join(self.build_folder, "config.log")
        if os.path.isfile(config_log):
            try:
                with open(config_log, "r", encoding="utf-8", errors="replace") as handle:
                    tail = handle.readlines()[-40:]
            except OSError:
                tail = []
            if tail:
                details.append("  config.log tail:")
                details.extend(f"    {line.rstrip()}" for line in tail)
        raise ConanException("\n".join(details))

    def _build_environment(self):
        """Scoped environment for configure/build/package, replacing direct
        os.environ mutation. configure locates libsvg/cairo through
        pkg-config, so point it at the PkgConfigDeps .pc files in the
        generators folder. Shared dependencies (cairo and its transitive
        freetype/pixman/fontconfig/...) must resolve from the Conan cache
        when configure runs its test programs; a test binary's DT_RUNPATH
        is not inherited by indirect NEEDED entries, so rpath on the
        direct link line is not enough and LD_LIBRARY_PATH covers the
        whole chain. When the host toolchain needed recovery, its libdir
        comes first so the ABI-matched host libraries win over anything
        the shell may already export."""
        environment = Environment()
        environment.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        libdirs = []
        for _, dep in self.dependencies.items():
            if dep.options.get_safe("shared"):
                libdirs.extend(dep.cpp_info.aggregated_components().libdirs)
        runtime = self._host_toolchain_libdir()
        ordered = ([runtime] if runtime else []) + libdirs
        if ordered:
            environment.prepend_path(
                "LD_LIBRARY_PATH", os.pathsep.join(dict.fromkeys(ordered))
            )
        return environment

    def build(self):
        apply_conandata_patches(self)
        # The probes (already done via self.run(env="conanbuild")) and
        # configure/make share one environment model: ConanFile.run
        # sources conanbuild.sh, which expands profile placeholders
        # correctly and inherits the process LD_LIBRARY_PATH. The
        # scoped Environment below only adds LD_LIBRARY_PATH entries
        # (recovery libdir first, then shared dependency libdirs) — it
        # never touches PATH, so the ${PATH} placeholders of the profile
        # stay valid for the sourced launcher.
        environment = self._build_environment()
        with environment.vars(self, scope="build").apply():
            autotools = Autotools(self)
            self._configure_and_log(autotools)
            autotools.make(args=["-j2"])

    def _configure_and_log(self, autotools):
        """Run autotools.configure(); on failure dump the tail of
        config.log (failed compile command, loader errors, exit code)
        and re-raise the original exception."""
        try:
            autotools.configure()
        except ConanException:
            config_log = os.path.join(self.build_folder, "config.log")
            self.output.error("configure() failed; tail of config.log follows")
            try:
                with open(config_log, "r", encoding="utf-8", errors="replace") as handle:
                    self.output.info(handle.read()[-8000:])
            except OSError as read_error:
                self.output.error(f"could not read config.log: {read_error}")
            raise

    def package(self):
        # Same environment model as build(): probe cache decides the
        # recovery libdir, and install runs in the identical scope.
        environment = self._build_environment()
        with environment.vars(self, scope="build").apply():
            autotools = Autotools(self)
            autotools.install()
        # Conan 2 copy() has no delete= argument; remove libtool *.la wrappers manually.
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["svg-cairo"]
        self.cpp_info.set_property("pkg_config_name", "libsvg-cairo")
        self.cpp_info.set_property("cmake_target_name", "libsvg-cairo::libsvg-cairo")
        # svg-cairo.h includes svg.h and cairo.h directly, so consumers
        # need the include dirs of both public dependencies to compile
        # against this package.
        self.cpp_info.requires = ["libsvg::libsvg", "cairo::cairo"]
