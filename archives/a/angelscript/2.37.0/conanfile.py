#!/usr/bin/env python3
"""Conan recipe for AngelScript 2.37.0 — game scripting engine (direct compile).

AngelCode Scripting Library core: sdk/angelscript/source/ 下 33 个通用编译单元
+ 平台专属调用约定文件。零外部依赖（仅 pthread，OHOS musl 已并入 libc）。

直编路径（不走上游 CMake）：对齐 sdk/angelscript/projects/cmake/CMakeLists.txt
的 ANGELSCRIPT_SOURCE 清单逐个编译 + llvm-ar 归档，规避 CMake 平台探测在
OHOS 上的不确定性（smaz/pqclean/abc/aklomp-base64 直编先例）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

# 上游 CMakeLists ANGELSCRIPT_SOURCE（33 个通用编译单元；x86/x64_msvc/mingw/
# mips 等平台专属文件靠 as_config.h 宏守卫在非目标平台编成空目标——上游同样全编）
_COMMON_SOURCES = [
    "as_atomic.cpp", "as_builder.cpp", "as_bytecode.cpp", "as_callfunc.cpp",
    "as_callfunc_mips.cpp", "as_callfunc_x86.cpp", "as_callfunc_x64_gcc.cpp",
    "as_callfunc_x64_msvc.cpp", "as_callfunc_x64_mingw.cpp", "as_compiler.cpp",
    "as_configgroup.cpp", "as_context.cpp", "as_datatype.cpp", "as_gc.cpp",
    "as_generic.cpp", "as_globalproperty.cpp", "as_memory.cpp", "as_module.cpp",
    "as_objecttype.cpp", "as_outputbuffer.cpp", "as_parser.cpp", "as_restore.cpp",
    "as_scriptcode.cpp", "as_scriptengine.cpp", "as_scriptfunction.cpp",
    "as_scriptnode.cpp", "as_scriptobject.cpp", "as_string.cpp",
    "as_string_util.cpp", "as_thread.cpp", "as_tokenizer.cpp", "as_typeinfo.cpp",
    "as_variablescope.cpp",
]


class AngelscriptConan(ConanFile):
    name = "angelscript"
    version = "2.37.0"
    description = "AngelCode Scripting Library: flexible cross-platform scripting engine for game applications"
    license = "Zlib"
    homepage = "https://www.angelcode.com/angelscript/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # R26: 直编归档路径只出 .a 静态库（上游 as_callfunc_arm64_gcc.S 汇编
        # 原生调用约定代码未做 PIC+动态链接验证），shared=True 无效
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "angelscript 2.37.0 recipe builds static-only (direct-compile archive)")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        data = self.conan_data["sources"][self.version]
        # 显式传 url/sha256（conandata.yml 中的 tar_format 仅供校验，
        # get() 不识别该参数，不能通过 ** 展开传入——dbus 先例）
        get(self, url=data["url"], sha256=data["sha256"], strip_root=True)

    def build(self):
        # R33: compilers from Conan conf (dict form, conan 2.29.1 兼容),
        # never bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"

        # zip 顶层是 sdk/，strip_root 后源码位于 angelscript/{source,include}
        src = os.path.join(self.source_folder, "angelscript", "source")
        inc = os.path.join(self.source_folder, "angelscript", "include")

        build_type = str(self.settings.build_type).lower()
        opt = "-O2" if build_type == "release" else "-O0 -g"
        pic = "-fPIC" if self.options.get_safe("fPIC", True) else ""

        # 架构附加文件（对齐上游 CMakeLists asm 分支：aarch64 → arm64 调用约定）
        arch = str(self.settings.arch)
        sources = list(_COMMON_SOURCES)
        asm_sources = []
        if arch.startswith("armv8") or arch in ("aarch64", "arm64"):
            sources.append("as_callfunc_arm64.cpp")
            asm_sources.append("as_callfunc_arm64_gcc.S")
        elif arch in ("armv7", "armv7hf", "arm"):
            sources.append("as_callfunc_arm.cpp")
            asm_sources.append("as_callfunc_arm_gcc.S")

        obj_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(obj_dir, exist_ok=True)
        objects = []
        # R9: 串行编译保证可复现（35 单元，本地实测 <2 分钟）
        for s in sources:
            obj = os.path.join(obj_dir, s.replace(".cpp", ".o"))
            self.run(f'"{cxx}" -c -std=c++17 {opt} {pic} '
                     f'-DANGELSCRIPT_EXPORT -D_LIB -I"{src}" -I"{inc}" '
                     f'"{os.path.join(src, s)}" -o "{obj}"')
            objects.append(obj)
        for s in asm_sources:
            obj = os.path.join(obj_dir, s.replace(".S", ".o"))
            self.run(f'"{cxx}" -c -x assembler-with-cpp -I"{src}" '
                     f'"{os.path.join(src, s)}" -o "{obj}"')
            objects.append(obj)

        libpath = os.path.join(self.build_folder, "libangelscript.a")
        self.run(f'"{ar}" rcs "{libpath}" ' +
                 " ".join(f'"{o}"' for o in objects))
        self.run(f'"{ranlib}" "{libpath}"')

    def package(self):
        inc = os.path.join(self.source_folder, "angelscript", "include")
        copy(self, "angelscript.h", src=inc,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libangelscript.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        # 上游 zip 无根级 LICENSE 文件：Zlib 风格条款内嵌每个源文件头 +
        # docs/manual/doc_license.html（许可证页）
        docs = os.path.join(self.source_folder, "docs", "manual")
        copy(self, "doc_license.html", src=docs,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 上游 CMake 导出目标名 Angelscript::angelscript，保持一致
        self.cpp_info.set_property("cmake_file_name", "Angelscript")
        self.cpp_info.set_property("cmake_target_name", "Angelscript::angelscript")
        self.cpp_info.libs = ["angelscript"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
