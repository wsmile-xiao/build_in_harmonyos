#!/usr/bin/env python3
"""Conan recipe for khronos-api 4.6-git20220505 — Khronos API headers (OpenGL 4.6 / GLES).

纯头文件包（header-library，无编译）。Khronos 头文件官方随 Debian 包 khronos-api
分发：上游源码包以 genheaders.py 从 XML 注册表生成 api/ 头文件，该脚本依赖 lxml
模块（鸿蒙 Python 无可用 lxml：pip 无鸿蒙 wheel、源码编译不可行，实测安装失败），
故直接使用 Debian 官方二进制包内容（usr/include/khronos-api 头文件 +
usr/share/khronos-api XML 注册表，与上游发布物一致，sha256 固定校验）。
deb（ar 格式）在 source() 中用纯标准库（python tarfile）解析提取 data.tar.xz，
不依赖外部 ar 工具。头文件布局保持 Debian 原样（include/khronos-api/GL/...），
消费方以 #include <khronos-api/GL/glcorearb.h> 引用。
"""
import os
import shutil
import tarfile

from conan import ConanFile
from conan.tools.files import check_sha256, copy
from conan.tools.layout import basic_layout


class KhronosApiConan(ConanFile):
    name = "khronos-api"
    version = "4.6-git20220505"
    description = "Khronos API specifications and headers (OpenGL 4.6 / GLES) — Debian khronos-api packaging"
    license = "Apache-2.0"
    homepage = "https://www.khronos.org/registry/"
    url = "https://www.khronos.org/registry/"
    topics = ("khronos", "opengl", "gles", "headers", "registry")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def _extract_deb_data(self, deb_path, dest):
        """从 ar 格式 deb 中提取 data.tar.xz 并安全解压到 dest（纯标准库实现）。"""
        with open(deb_path, "rb") as f:
            if f.read(8) != b"!<arch>\n":
                raise RuntimeError(f"invalid deb (ar) file: {deb_path}")
            while True:
                header = f.read(60)
                if len(header) < 60:
                    break
                name = header[:16].decode("ascii", "replace").strip()
                size = int(header[48:58].decode("ascii", "replace").strip() or "0")
                data = f.read(size)
                if size % 2 and name != "/":
                    f.read(1)  # ar 对齐填充
                if name == "data.tar.xz":
                    import io
                    dest_abs = os.path.abspath(dest)
                    with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as tf:
                        for member in tf.getmembers():
                            target = os.path.abspath(os.path.join(dest_abs, member.name))
                            if target != dest_abs and not target.startswith(dest_abs + os.sep):
                                raise RuntimeError(f"unsafe tar member: {member.name}")
                        tf.extractall(dest_abs)
                    return
        raise RuntimeError("data.tar.xz not found in deb")

    def source(self):
        url = self.conan_data["sources"]["url"]
        sha256 = self.conan_data["sources"]["sha256"]
        deb_path = os.path.join(self.source_folder, "khronos-api.deb")
        self.run(f'curl -L -k -o "{deb_path}" "{url}"', cwd=self.source_folder)
        check_sha256(self, deb_path, sha256)
        extracted = os.path.join(self.source_folder, "_extracted")
        os.makedirs(extracted, exist_ok=True)
        self._extract_deb_data(deb_path, extracted)
        # usr/include/khronos-api → include/；usr/share/khronos-api → share/
        usr = os.path.join(extracted, "usr")
        for sub in ("include", "share"):
            src = os.path.join(usr, sub)
            if os.path.isdir(src):
                shutil.move(src, os.path.join(self.source_folder, sub))
        shutil.rmtree(extracted)
        os.remove(deb_path)

    def package(self):
        copy(self, "*", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        if os.path.isdir(os.path.join(self.source_folder, "share")):
            copy(self, "*", src=os.path.join(self.source_folder, "share"),
                 dst=os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "khronos-api")
        self.cpp_info.set_property("cmake_target_name", "khronos-api::khronos-api")
