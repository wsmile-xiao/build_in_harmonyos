# paperjam

## 简介

PaperJam 是 Martin Mares 编写的 PDF 处理工具：页面重排、缩放旋转、多页拼版（n-up）、裁切标记等。
上游：<https://mj.ucw.cz/sw/paperjam/>，许可证 GPL-2.0-or-later。

## OHOS 适配要点

1. **纯手写 Makefile**：无 configure，默认 `all` 还会构建需 `a2x`/asciidoc 的手册页；配方只构建 `make paperjam` 二进制目标。
2. **依赖收敛**：上游需 libqpdf + libpaper 头库。`qpdf/12.3.2` 有本仓 Conan 配方；`libpaper/1.1.28`
   在本仓仅为 legacy 归档（manifest + patches，无 conanfile，不可被 `conan download` 安装），不能作为
   Conan 依赖。paperjam 仅用三个 libpaper 符号（`paperinfo`/`paperpswidth`/`paperpsheight`），故在
   `vendored/paper.h` + `vendored/paper.c` 内置 ISO/US 纸张表（PS 点值与 libpaper 一致），构建时编成
   `libpaper.a` 供 `-lpaper` 链接，无需改动上游源码。
3. **上游无测试**：1.2.2 发布包无 tests 目录、无 check/test 目标（审计见 `test_package/MANIFEST.yml`
   `upstream_test_audit`），`HMBS_UPSTREAM_TEST_RESULT` 为 `no_tests`。
4. **test_package**：`test.sh` 对安装后的 `bin/paperjam` 做 5 项真实调用验证（--version/--help/
   未知纸张拒绝/null 往返/a4 命名纸张），计数输出 `HMBS_TEST_PACKAGE_RESULT`。

## 依赖关系

- **编译依赖**：qpdf/12.3.2（经 Conan；其传递依赖 zlib/libjpeg-turbo 由 qpdf 配方处理）
- **运行依赖**：无（单二进制；libqpdf 动态链接由 Conan runenv 提供）
