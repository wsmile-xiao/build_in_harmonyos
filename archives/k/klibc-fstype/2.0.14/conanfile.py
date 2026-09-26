"""Conan recipe for the klibc fstype filesystem image detector."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KlibcFstypeConan(ConanFile):
    name = "klibc-fstype"
    version = "2.0.14"
    description = "Small filesystem image type and size detection helper from klibc"
    license = "MIT AND BSD-3-Clause AND GPL-2.0-only"
    homepage = "https://www.kernel.org/pub/linux/libs/klibc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        source = os.path.join(self.source_folder, "usr", "kinit", "fstype")
        binary = os.path.join(self.build_folder, "fstype")
        compat = os.path.join(self.build_folder, "fstype_ohos_compat.h")
        with open(compat, "w") as f:
            f.write(
                "#include <linux/types.h>\n"
                "#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__\n"
                "#define __cpu_to_le16(x) ((__le16)(x))\n"
                "#define __cpu_to_le32(x) ((__le32)(x))\n"
                "#define __le16_to_cpu(x) ((__u16)(x))\n"
                "#define __le32_to_cpu(x) ((__u32)(x))\n"
                "#define __le64_to_cpu(x) ((__u64)(x))\n"
                "#define __cpu_to_be32(x) ((__be32)__builtin_bswap32((__u32)(x)))\n"
                "#define __be32_to_cpu(x) ((__u32)__builtin_bswap32((__u32)(x)))\n"
                "#define __be64_to_cpu(x) ((__u64)__builtin_bswap64((__u64)(x)))\n"
                "#else\n"
                "#define __cpu_to_le16(x) ((__le16)__builtin_bswap16((__u16)(x)))\n"
                "#define __cpu_to_le32(x) ((__le32)__builtin_bswap32((__u32)(x)))\n"
                "#define __le16_to_cpu(x) ((__u16)__builtin_bswap16((__u16)(x)))\n"
                "#define __le32_to_cpu(x) ((__u32)__builtin_bswap32((__u32)(x)))\n"
                "#define __le64_to_cpu(x) ((__u64)__builtin_bswap64((__u64)(x)))\n"
                "#define __cpu_to_be32(x) ((__be32)(x))\n"
                "#define __be32_to_cpu(x) ((__u32)(x))\n"
                "#define __be64_to_cpu(x) ((__u64)(x))\n"
                "#endif\n"
            )
        self.run(
            f'"{cc}" -O2 -Wall -Wextra -include "{compat}" -o "{binary}" '
            f'"{source}/main.c" "{source}/fstype.c"',
            env="conanbuild",
        )
        if not os.path.isfile(binary):
            raise RuntimeError("compiler returned success without producing fstype")
        os.chmod(binary, 0o755)
        self.output.info(f"built upstream fstype helper ({os.path.getsize(binary)} bytes)")

    def package(self):
        copy(self, "fstype", self.build_folder, os.path.join(self.package_folder, "bin"))
        os.chmod(os.path.join(self.package_folder, "bin", "fstype"), 0o755)
        copy(
            self,
            "LICENSE",
            os.path.join(self.source_folder, "usr", "klibc"),
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []