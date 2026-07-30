#!/usr/bin/env python3
"""Conan recipe for iozone 3.51 — Filesystem Benchmark Tool.

iozone is a filesystem benchmark tool that measures file I/O performance
for various operations (read, write, random, fread/fwrite, etc.).

Platform adaptations for OHOS:
  1. Missing <time.h>: added #include <time.h> for ctime()/time() prototypes
     (implicit int return truncates 64-bit ARM64 pointers → SIGSEGV)
  2. extern int errno → #include <errno.h> for musl libc thread-local errno
  3. PAGE_SIZE defined manually (-DPAGE_SIZE=4096 -DGOT_PAGESIZE) to bypass
     missing Linux kernel header <asm/page.h>
  4. ASYNC_IO/HAVE_PREAD disabled: OHOS musl lacks POSIX AIO (aio_* symbols)
  5. NO_THREADS enabled: avoids -lpthread link dependency; iozone runs
     single-process for basic benchmark scenarios
  6. /tmp read-only: test_package uses $TMPDIR or fallback writable directory
     (E002 knowledge entry)
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, save
from conan.tools.layout import basic_layout
from conan.tools.build import cross_building


class IozoneConan(ConanFile):
    name = "iozone"
    version = "3.51"
    description = "Filesystem Benchmark Tool"
    license = "custom"  # Iozone License: free use/distribute, copyright must remain intact
    homepage = "https://www.iozone.org/"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler"

    def export_sources(self):
        export_conandata_patches(self)
        # Also export the patches directory
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)
        # Apply the patch from export_sources_folder to source_folder
        # Use patch command directly since apply_conandata_patches in build()
        # operates on source_folder but build compiles from a separate copy.
        patch_file = os.path.join(self.export_sources_folder, "patches", "0001-fix-missing-includes.patch")
        if os.path.isfile(patch_file):
            self.run(f'patch -p0 < "{patch_file}"', cwd=self.source_folder)
            # Verify patch was applied
            src_file = os.path.join(self.source_folder, "src", "current", "iozone.c")
            if os.path.isfile(src_file):
                with open(src_file) as f:
                    content = f.read()
                if "#include <time.h>" not in content:
                    raise ConanException("PATCH FAILED: iozone.c missing #include <time.h>")
                if "#include <asm/page.h>" in content:
                    raise ConanException("PATCH FAILED: iozone.c still has #include <asm/page.h>")
                self.output.info("Patch applied and verified successfully")
        else:
            self.output.warning(f"Patch file not found: {patch_file}")

    def build(self):

        src_dir = os.path.join(self.source_folder, "src", "current")
        build_dir = self.build_folder

        # Determine the target: use linux for all POSIX OHOS targets
        target = "linux"

        # Compile flags for OHOS:
        # - Default linux target does not use HAVE_PREAD or ASYNC_IO
        # - NO_THREADS avoids -lpthread link dependency
        # - PAGE_SIZE=4096 and GOT_PAGESIZE bypass missing <asm/page.h>
        # - LARGEFILE64_SOURCE for 64-bit file support
        cflags = "-O3 -Dunix -DHAVE_ANSIC_C -DSHARED_MEM -Dlinux " \
                 "-D_LARGEFILE64_SOURCE -DNO_THREADS " \
                 "-DPAGE_SIZE=4096 -DGOT_PAGESIZE"

        # Build step: compile iozone.c and libbif.c, no libasync (no ASYNC_IO)
        cc = "clang"
        self.run(
            f'cd "{src_dir}" && '
            f'{cc} {cflags} -c iozone.c -o iozone.o && '
            f'{cc} {cflags} -c libbif.c -o libbif.o && '
            f'{cc} {cflags} iozone.o libbif.o -o iozone',
            env="conanbuild"
        )

    def package(self):
        src_dir = self.source_folder
        # Binary is built in source_folder/src/current (build copies sources from source_folder)
        build_bin = os.path.join(src_dir, "src", "current")
        copy(self, "iozone", src=build_bin, dst=os.path.join(self.package_folder, "bin"))
        # Also include docs and license from source_folder
        copy(self, "docs/*", src=src_dir, dst=os.path.join(self.package_folder, "licenses"))
        # Include the license text as a file
        license_text = """Copyright 1991, 1992, 1994, 1998, 1999, 2002 William D. Norcott

License to freely use and distribute this software is hereby granted
by the author, subject to the condition that this copyright notice
remains intact. The author retains the exclusive right to publish
derivative works based on this work, including, but not limited to,
revised versions of this work.

THIS SOFTWARE IS PROVIDED BY DON CAPPS AND THE IOZONE CREW "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED.

IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE.
"""
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), license_text)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
