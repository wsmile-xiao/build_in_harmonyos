#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for mailto 1.3.2 — Apache 的 WWW Mail Gateway CGI。

mailto 是 Apache 软件基金会 1999 年发布的 CGI 程序：解析 HTTP 表单（或
URL 参数），把收到的字段拼装成一封 MIME 邮件，然后调用本机 sendmail
投递。1999 年的设计背景是"WWW 上匿名发信不可取"，因此它支持一个访问
控制文件（mailto.conf），规定哪些人可以通过网关发信、哪些不行。

命令行接口（getopt，选项串 "Dvh?"）：
  -D <domain>  为发信人补全 @domain 后缀
  -v           打印版本历史（大段 HTML 注释块，以 "** Version 1.3.2" 开头）
  -h / -?      打印用法
它没有别的选项，也不接受位置参数；正常运行时会从环境变量读取
QUERY_STRING / CONTENT_LENGTH / REMOTE_USER 等 CGI 变量。

OHOS aarch64 适配要点：
- 上游 Makefile 只有 `all/install/clean/dist/check/depend`，`all` 就是
  `$(CC) $(CFLAGS) $(OBJECTS) -o $@`，没有自动依赖探测、没有配置步骤，
  因此直接驱动 clang 编译 mailto.c + util.c 即可，不必也不宜在交叉环境
  调用上游 make（其 `install` 目标写死 BSD 的 bsdinst 与 /usr/machine/etc/httpd
  路径，与 OHOS 无关）。
- **唯一适配点**：util.c 定义的 `getline(char*, int, FILE*)` 与
  POSIX.1-2008 / OHOS sysroot 的 `getline(3)` 符号冲突（conflicting types）。
  通过 patch 0001 将其重命名为 `mailto_getline`，不改动函数体与行为。
  上游未提供 util.h，mailto.c 未调用该函数，故无其他调用点需要同步。
- 产出 bin/mailto（可执行文件）与 share/doc/mailto/{README,ChangeLog,INSTALL}
  文档；不安装 sendmail（OHOS 无此程序），发信路径由使用者自行接管。
- 产物是纯用户态 CGI 二进制，不含平台专有系统调用，aarch64 行为与上游一致。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get


class MailtoConan(ConanFile):
    name = "mailto"
    version = "1.3.2"
    description = (
        "Apache's WWW Mail Gateway CGI: turns an HTTP form submission into a "
        "MIME mail and hands it to the local MTA (1999 vintage)"
    )
    license = "Apache-2.0"
    homepage = "https://www.apache.org/distware/mailto/"
    topics = ("cgi", "http", "mail", "form", "sendmail", "gateway", "apache")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml", "patches/*"

    def package_id(self):
        # 纯 C 用户态程序，不随 build_type / 编译优化变化
        self.info.settings.build_type = "Any"
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("arch")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # conandata.yml 的 patches 必须用**列表**格式（含 patch_file /
        # patch_description / patch_type）。Conan 2.x 按 self.version 查找，
        # 误写成 dict-by-filename 会取到空列表并**静默跳过补丁**，且被 CI
        # 门禁 L0f 拦截（bad_patch_format）。详见 notes.md「坑 1」。
        apply_conandata_patches(self)

    def build(self):
        # 交叉编译器由 profile 的 [buildenv] CC 提供（与本仓库其它配方一致）
        cc = os.environ.get("CC") or "clang"
        # 上游是 1999 年的 gnu89 代码：format 串风格、赋值当条件、块注释嵌套
        # 等告警均为历史遗留且不影响正确性，统一用 -w 静默，避免 CI 日志噪声。
        cflags = "-O2 -fPIC -std=gnu99 -w"
        for src in ("mailto.c", "util.c"):
            self.run(f"{cc} -c {src} {cflags} -o {src[:-2]}.o")
        self.run(f"{cc} mailto.o util.o -o mailto")

    def package(self):
        copy(self, "mailto", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        for doc in ("README", "ChangeLog", "INSTALL"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "doc", "mailto"),
                 keep_path=False)
        copy(self, "mailto.conf", src=self.source_folder,
             dst=os.path.join(self.package_folder, "etc"), keep_path=False)

    def package_info(self):
        # 只有一个可执行文件，没有库也没有公开头文件
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
