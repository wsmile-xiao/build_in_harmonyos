#!/usr/bin/env python3
"""Conan recipe — avr-evtd 1.7.7 (AVR event daemon — pure C, Makefile build)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class AvrEvtdConan(ConanFile):
    name = "avr-evtd"
    version = "1.7.7"
    description = "AVR Event Daemon (PPC-EVTD—monitors AVR controller events via serial)"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/avr-evtd/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 C——Makefile 构建（CC=cc——OHOS 无 cc 用 clang——产出 avr-evtd）
        self.run("make CC=clang CFLAGS=-Wall\\ -Wextra\\ -Os\\ -DUBOOT",
                 cwd=self.source_folder)

    def package(self):
        # make install 到 PREFIX（sbin/avr-evtd）——或手动 copy
        self.run(f"make install PREFIX=/usr DESTDIR={self.package_folder}",
                 cwd=self.source_folder, ignore_errors=True)
        copy(self, "avr-evtd", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        for doc in ("COPYING", "README1st.txt"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
