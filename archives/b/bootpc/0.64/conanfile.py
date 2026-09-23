"""Conan recipe — bootpc 0.64 (BOOTP client)"""
from conan import ConanFile
from conan.tools.files import get, copy
import os


class BootpcConan(ConanFile):
    name = "bootpc"
    version = "0.64"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    license = "GPL-2.0"
    description = "BOOTP protocol client"
    url = "https://packages.debian.org/bootpc"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_execs.get("c", "cc")
        # bootpc uses 'log' as a variable name — conflicts with C23 math.h builtin.
        # Also needs <string.h> and stderr-as-initializer fix for modern clang/OHOS.
        import re as _re
        for fname in ["log.h", "bootpc.h", "bootpc.c", "main.c", "bptypes.h"]:
            fpath = os.path.join(self.source_folder, fname)
            if not os.path.exists(fpath):
                continue
            with open(fpath, "r") as f:
                src = f.read()
            # rename 'log' variable to avoid C23 builtin conflict
            src = src.replace("extern FILE * log;", "extern FILE * bootpc_log;")
            src = src.replace(" logfd;", " bootpc_logfd;")
            # fix: FILE * logfile = stderr ;  →  FILE * logfile ;
            src = src.replace("FILE * logfile = stderr ;", "FILE * logfile ;")
            # add #include <string.h> after first #include <stdio.h>
            src = src.replace("#include <stdio.h>", "#include <stdio.h>\n#include <string.h>", 1)
            # insert 'logfile = stderr ;' after 'int main(' line
            src = _re.sub(r"(int main\([^)]*\)\s*\{)", r"\1\n\tlogfile = stderr ;", src)
            with open(fpath, "w") as f:
                f.write(src)
        cflags = "-O2 -fcommon -Wno-error=implicit-function-declaration -Wno-error=implicit-int -Wno-error=int-conversion -Wno-error=deprecated-non-prototype -Wno-error=return-type -Wno-error=incompatible-function-pointer-types -Wno-pointer-sign"
        self.run(f"make CC={cc} CFLAGS=\"{cflags}\" all", cwd=self.source_folder)

    def package(self):
        copy(self, "bootpc", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        # E212: HMDFS blocks dlopen/exec of unsigned ELF binaries.
        # Re-sign the binary after Conan copy (which invalidates the signature).
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        bindir = os.path.join(self.package_folder, "bin")
        self.run(
            f'for f in {bindir}/*; do '
            f'chmod 755 "$f" && '
            f'{objcopy} --remove-section .codesign "$f" 2>/dev/null; '
            f'{signer} sign -inFile "$f" -outFile "$f.signed" -selfSign 1 && '
            f'mv -f "$f.signed" "$f" && chmod 755 "$f"; '
            f'done'
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
