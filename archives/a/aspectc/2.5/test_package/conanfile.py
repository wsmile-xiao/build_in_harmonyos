#!/usr/bin/env python3
"""test_package for aspectc 2.5: verify ac++/ag++ weave a real aspect."""

import os
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        if not can_run(self):
            return
        bindir = self.dependencies["aspectc"].package_folder
        acxx = os.path.join(bindir, "bin", "ac++")
        agxx = os.path.join(bindir, "bin", "ag++")
        # Runtime .so search path (libxml2/libz/libc++) was baked in via
        # RUNPATH at package time; just execute the tools.
        self.run(f'"{acxx}" --version | grep -q "2.5"')
        self.run(f'"{agxx}" --version | grep -q "2.5"')

        # Weave the classic helloworld aspect and run the result.
        example = Path(self.source_folder) / "helloworld"
        example.mkdir(parents=True, exist_ok=True)
        (example / "hello.h").write_text("void hello();\n", encoding="utf-8")
        (example / "hello.cc").write_text(
            '#include "hello.h"\n#include <iostream>\n'
            'void hello(){ std::cout << "Hello"; }\n',
            encoding="utf-8",
        )
        (example / "main.cc").write_text(
            '#include "hello.h"\n'
            "int main(){ hello(); return 0; }\n",
            encoding="utf-8",
        )
        (example / "world.ah").write_text(
            "#ifndef __WORLD_AH__\n#define __WORLD_AH__\n\n"
            "#include <iostream>\n\n"
            "aspect World {\n"
            "  advice execution(\"void hello()\") : after() {\n"
            '    std::cout << "World" << std::endl;\n'
            "  }\n"
            "};\n\n"
            "#endif\n",
            encoding="utf-8",
        )
        # ag++ needs a backend C++ compiler named "g++"; the package ships
        # g++/gcc shims in its bin dir, so export PATH inside the shell so
        # ag++ (and the g++ it spawns) inherit it.
        bindir2 = os.path.join(bindir, "bin")
        prog = example / "hello"
        self.run(
            f'cd "{example}" && export PATH="{bindir2}:$PATH" && '
            f'"{agxx}" -p . main.cc hello.cc -o "{prog}"',
        )
        # The woven binary is an OHOS ELF: SDK lld already drops a
        # .codesign section, so strip it before signing (matching the
        # recipe's _make_elf_tool_runnable), set RUNPATH for the runtime
        # libc++/libxml2, then self-sign.
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        self.run(f'{objcopy} --remove-section .codesign "{prog}" 2>/dev/null || :')
        libxml = "/data/service/hnp/libxml2.org/libxml2_2.11.9/lib"
        libcxx = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        self.run(f'patchelf --set-rpath "{libxml}:{libcxx}" "{prog}"')
        signer = "/data/service/hnp/bin/binary-sign-tool"
        signed = str(prog) + ".signed"
        self.run(f'{signer} sign -inFile "{prog}" -outFile "{signed}" -selfSign 1')
        if os.path.isfile(signed):
            os.replace(signed, str(prog))
        os.chmod(prog, 0o755)
        # Run it.  LD_LIBRARY_PATH must reach the OHOS runtime libs
        # (libc++/libxml2) because the app-sandbox ignores DT_RUNPATH; the
        # output is captured to a file and checked below.
        outfile = example / "hello.out"
        self.run(
            f'cd "{example}" && LD_LIBRARY_PATH="{libxml}:{libcxx}" '
            f'"{prog}" > "{outfile}" 2>&1'
        )
        output = outfile.read_text(encoding="utf-8", errors="replace") if outfile.exists() else ""
        if "Hello" not in output or "World" not in output:
            raise RuntimeError(f"helloworld output mismatch: {output!r}")
