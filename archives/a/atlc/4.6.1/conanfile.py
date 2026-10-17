#!/usr/bin/env python3
"""Conan recipe — atlc 4.6.1 (transmission line calculator — pure C).

configure 的 config.status 在 OHOS 沙箱报 mktemp 权限（drwx--S--- owner
20001006——当前用户写不了——CONFIG_SHELL/umask 均无效）——改手动构建：
生成 config.h + clang 编译 atlc 主程序（atlc_SOURCES 27 个 .c）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class AtlcConan(ConanFile):
    name = "atlc"
    version = "4.6.1"
    description = "Arbitrary Transmission Line Calculator (AVR tools family)"
    license = "GPL-2.0-or-later"
    homepage = "http://atlc.sourceforge.net/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        src = os.path.join(self.source_folder, "src")
        # 生成 config.h（configure 的 config.status 在 OHOS 报 mktemp 权限——
        # 手动从 config.h.in 生成基础宏）
        with open(os.path.join(self.source_folder, "config.h"), "w") as f:
            f.write(
                "/* config.h — 手动生成（configure 在 OHOS 沙箱 config.status "
                "mktemp 权限受限——如实记录） */\n"
                "#ifndef _CONFIG_H_\n#define _CONFIG_H_\n"
                "#include <stddef.h>\n#include <stdio.h>\n#include <stdlib.h>\n"
                "#include <string.h>\n#include <math.h>\n#include <time.h>\n"
                "#include <limits.h>\n#include <errno.h>\n"
                "#define PACKAGE \"atlc\"\n#define PACKAGE_VERSION \"4.6.1\"\n"
                "#define HAVE_ERRNO_H 1\n#define HAVE_LIMITS_H 1\n"
                "#define HAVE_MATH_H 1\n#define HAVE_STDIO_H 1\n"
                "#define HAVE_STDLIB_H 1\n#define HAVE_STRING_H 1\n"
                "#define HAVE_TIME_H 1\n#define HAVE_SYS_TIME_H 1\n"
                "#endif\n"
            )
        sources = [
            "atlc.c", "read_bitmap_file_headers.c", "update_voltage_array.c",
            "check_for_boundaries.c", "memory.c", "setup_arrays.c",
            "finite_difference_single_threaded.c",
            "finite_difference_multi_threaded.c", "usage_atlc.c",
            "check_for_shorts.c", "find_energy_per_metre.c",
            "set_oddity_from_Greens_paper.c",
            "get_file_pointer_with_right_filename.c", "find_maximum_values.c",
            "calculate_colour_data.c", "find_electric_fields.c",
            "get_options.c", "exit_with_msg_and_exit_code.c",
            "do_fd_calculation.c", "swap_conductor_voltages.c",
            "print_copyright.c", "print_data_for_directional_couplers.c",
            "print_data_for_two_conductor_lines.c",
            "set_data_to_sensible_starting_values.c",
            "write_fields_for_two_conductor_lines.c",
            "write_fields_for_directional_couplers.c",
        ]
        clang = "/data/service/hnp/bin/clang"
        self.run(
            f"{clang} -fPIC -O2 -fcommon -I{src} -I{self.source_folder} "
            f"-DNEED_MPI_CODE "
            + " ".join(os.path.join(src, s) for s in sources)
            + " -lm -lpthread -o atlc",
            cwd=self.build_folder,
        )

    def package(self):
        copy(self, "atlc", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        for doc in ("COPYING", "README", "AUTHORS"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
