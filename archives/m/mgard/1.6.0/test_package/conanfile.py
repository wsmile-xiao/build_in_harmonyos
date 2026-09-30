import os

from conan import ConanFile
from conan.errors import ConanException


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        info = self.dependencies["mgard"].cpp_info
        # R34/L1e：显式校验包内产物路径存在（库 + 头），防止 CI 破坏性
        # 负测试 fallback 到系统 mgard 误判为真测试。
        libdir = info.libdirs[0] if info.libdirs else ""
        incdir = info.includedirs[0] if info.includedirs else ""
        if not libdir or not os.path.isdir(libdir):
            raise ConanException(f"mgard package lib dir missing: {libdir}")
        if not os.path.isdir(os.path.join(incdir, "mgard")):
            raise ConanException("mgard headers missing in package include/")
        libfound = any(
            os.path.isfile(os.path.join(libdir, f))
            for f in ("libmgard.so", "libmgard.a"))
        if not libfound:
            raise ConanException("libmgard missing in package lib/")

    def test(self):
        info = self.dependencies["mgard"].cpp_info
        libdir = info.libdirs[0]
        incdir = info.includedirs[0]
        cxx = os.environ.get("CXX", "clang++")
        src = os.path.join(self.source_folder, "consumer.cpp")
        out = os.path.join(self.build_folder, "consumer_mgard")
        # R34：真实编译链接调用 mgard 公开 API（compress/decompress 模板 +
        # libmgard），消费者程序在测试环境原生运行。
        # -I 除 mgard 包自身外还需传递依赖 include 路径：mgard 公开头链
        # compress.hpp → CompressedDataset.hpp → mgard/proto/mgard.pb.h
        # 包含 google/protobuf/port_def.inc（位于 protobuf 包 include/）。
        # 静态 libmgard.a 的传递依赖符号（zstd/protobuf/z）必须在
        # libmgard 之后补链（静态库归档解析顺序），-L/-l 从依赖图收集
        self.run(
            f'{cxx} -std=c++17 -O1 "{src}" ' + self._transitive_include_flags()
            + f' -I"{incdir}" -L"{libdir}" '
            + self._static_link_flags()
            + f' -o "{out}"',
            env="conanbuild")
        self.run(f'"{out}"', env="conanrun")

    def _transitive_include_flags(self):
        # 传递依赖头路径（protobuf 包的 google/protobuf/* 等）；mgard
        # 自身 include 由调用方 -I"{incdir}" 提供，此处跳过
        flags = []
        for ref, dep in self.dependencies.host.items():
            if ref.ref.name == "mgard":
                continue
            for d in dep.cpp_info.includedirs:
                flags.append('-I"{}"'.format(d))
        return " ".join(flags)

    def _static_link_flags(self):
        # -lmgard 在前，其后跟全部传递依赖（zlib/zstd/protobuf 静态库）
        flags = ["-lmgard"]
        for ref, dep in self.dependencies.host.items():
            if ref.ref.name == "mgard":
                continue
            for d in dep.cpp_info.libdirs:
                flags.append('-L"{}"'.format(d))
            for lib in dep.cpp_info.libs:
                flags.append("-l" + lib)
        return " ".join(flags)
