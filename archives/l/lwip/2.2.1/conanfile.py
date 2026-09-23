#!/usr/bin/env python3
"""Conan recipe for lwip 2.2.1.

lwIP is an embedded TCP/IP stack distributed as source that the integrator
assembles into its own targets (src/Filelists.cmake).  There is no upstream
configure/make library target, so this recipe builds a static library from
the official source files directly (core + api + netif + apps), excluding
makefsdata which is a standalone host tool with its own main().

Platform notes (OHOS):
  - lwipopts.h is required by opt.h; we install a minimal default
    (src/include/lwip/lwipopts.h is NOT part of the upstream zip, so we ship
    an empty-ish override header in package).
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class LwipConan(ConanFile):
    name = "lwip"
    version = "2.2.1"
    description = "lwip 2.2.1 - A Lightweight TCP/IP stack"
    license = "BSD-3-Clause"
    homepage = "https://savannah.nongnu.org/projects/lwip/"
    url = "https://download.savannah.nongnu.org/releases/lwip/lwip-2.2.1.zip"  # 官方源

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # lwip has no configure; AutotoolsToolchain is not used.
        pass

    def _toolchain(self):
        """Resolve the OHOS toolchain from Conan conf/settings (R33).

        Never fall back to bare shell env vars: on release workers the env is
        empty and the build would silently use the host toolchain.  The OHOS
        profile provides tools.build:compiler_executables; ar/ranlib live in
        the same toolchain bin directory.
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        cc_dir = os.path.dirname(cc)
        ar = compilers.get("ar") or (os.path.join(cc_dir, "llvm-ar") if cc_dir else "llvm-ar")
        ranlib = compilers.get("ranlib") or (os.path.join(cc_dir, "llvm-ranlib") if cc_dir else "llvm-ranlib")
        opt = "-O2" if self.settings.build_type == "Release" else "-O0 -g"
        return cc, ar, ranlib, [opt, "-fPIC"]

    def _src_files(self):
        """Collect the lwIP library sources for NO_SYS mode.

        NO_SYS (default lwipopts) uses only the raw callback API:
        src/core + src/netif.  src/api (netconn/socket) requires an OS and
        must not be built; apps/ are optional add-ons assembled by consumers.
        """
        src_dir = os.path.join(self.source_folder, "src")
        files = []
        for root, _dirs, names in os.walk(src_dir):
            if root.endswith(("src/api",)) or "/api/" in root:
                continue  # netconn API needs an OS (NO_SYS mode)
            for n in sorted(names):
                if n.endswith(".c"):
                    files.append(os.path.join(root, n))
        # makefsdata is a standalone host tool with its own main()
        files = [f for f in files if "makefsdata" not in f]
        return sorted(files)

    def _default_lwipopts(self):
        """Return a minimal default lwipopts.h (opt.h unconditionally includes it).

        NO_SYS mode: lwIP as a self-contained library without an RTOS, so
        no sys_arch implementation is required by consumers.
        """
        return ("/* default lwipopts.h for OHOS packaging */\n"
                "#define NO_SYS 1\n"
                "#define NO_SYS_NO_TIMERS 0\n"
                "#define LWIP_TIMERS 1\n"
                "#define LWIP_ERRNO_INCLUDE <errno.h>\n"
                "#define LWIP_NETCONN 0\n"
                "#define LWIP_SOCKET 0\n"
                "#define LWIP_NETIF_API 0\n")

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        cc, ar, ranlib, cflags = self._toolchain()
        inc = [
            os.path.join(src_dir, "src", "include"),
            os.path.join(src_dir, "contrib", "ports", "unix", "port", "include"),
        ]
        # provide a default lwipopts.h in the build include dir (opt.h needs it)
        gen_inc = os.path.join(self.build_folder, "include")
        os.makedirs(gen_inc, exist_ok=True)
        opts = os.path.join(gen_inc, "lwipopts.h")
        if not os.path.exists(opts):
            with open(opts, "w") as fh:
                fh.write(self._default_lwipopts())
        inc.append(gen_inc)
        inc_args = []
        for d in inc:
            inc_args += ["-I", d]
        obj_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(obj_dir, exist_ok=True)
        objs = []
        for f in self._src_files():
            base = os.path.basename(f).replace(".c", "") + "_" + \
                str(abs(hash(f)) % 100000) + ".o"
            out = os.path.join(obj_dir, base)
            cmd = [cc] + cflags + ["-c", f, "-o", out] + inc_args
            self.run(" ".join(cmd))
            objs.append(out)
        # lwip_port_rand/sys_now/sys_arch_protect are referenced in NO_SYS mode.
        port_rand = os.path.join(self.build_folder, "port_shim.c")
        if not os.path.exists(port_rand):
            with open(port_rand, "w") as fh:
                fh.write('#include "lwip/opt.h"\n'
                         '#include "lwip/sys.h"\n'
                         '#include <stdlib.h>\n'
                         '#include <time.h>\n'
                         'unsigned int lwip_port_rand(void)\n'
                         '{\n  return (unsigned int)rand();\n}\n'
                         'u32_t sys_now(void)\n'
                         '{\n'
                         '  struct timespec ts;\n'
                         '  clock_gettime(CLOCK_MONOTONIC, &ts);\n'
                         '  return (u32_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);\n'
                         '}\n'
                         'sys_prot_t sys_arch_protect(void)\n'
                         '{\n  return 0;\n}\n'
                         'void sys_arch_unprotect(sys_prot_t p)\n'
                         '{\n  (void)p;\n}\n')
        out = os.path.join(obj_dir, "port_rand.o")
        cmd = [cc] + cflags + ["-c", port_rand, "-o", out] + inc_args
        self.run(" ".join(cmd))
        objs.append(out)
        lib_dir = os.path.join(self.build_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        lib = os.path.join(lib_dir, "liblwip.a")
        self.run(f"{ar} rcs {lib} " + " ".join(objs))
        self.run(f"{ranlib} {lib}")

    def package(self):
        src_dir = self.source_folder
        copy(self, "liblwip.a",
             src=os.path.join(self.build_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h",
             src=os.path.join(src_dir, "src", "include"),
             dst=os.path.join(self.package_folder, "include"))
        # arch/cc.h + arch/perf.h are part of the public header set (unix port)
        copy(self, "*.h",
             src=os.path.join(src_dir, "contrib", "ports", "unix", "port", "include"),
             dst=os.path.join(self.package_folder, "include"))
        # ship a minimal default lwipopts.h (upstream zip has none at top level)
        opts = os.path.join(self.package_folder, "include", "lwip", "lwipopts.h")
        os.makedirs(os.path.dirname(opts), exist_ok=True)
        if not os.path.exists(opts):
            with open(opts, "w") as fh:
                fh.write(self._default_lwipopts())

    def package_info(self):
        self.cpp_info.libs = ["lwip"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "lwip")
        self.cpp_info.set_property("cmake_target_name", "lwip::lwip")
