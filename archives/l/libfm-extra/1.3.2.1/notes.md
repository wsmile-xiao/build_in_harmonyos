# libfm-extra 1.3.2.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-20
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
./configure --prefix=/usr/local --with-extra-only --disable-nls --disable-shared --enable-static --build=aarch64-linux-ohos --host=aarch64-linux-ohos
make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.sub 不识别 aarch64-linux-ohos | 上游 Autotools 脚本版本较旧 | 补丁更新 OHOS triplet 支持 |
| 2 | config.guess 不识别 aarch64-linux-ohos | 上游 Autotools 脚本版本较旧 | 补丁更新 OHOS 平台识别 |
| 3 | intltool/XML::Parser 不可用 | OHOS 环境未提供 intltool，且本模块与 i18n 无关 | build() 中 replace_in_file 修改 configure 脚本：跳过 intltool 版本/脚本/XML::Parser 检查 |
| 4 | g_libintl_* 未解析 | GLib 静态库需要 gettext 的 libintl 符号 | 声明 gettext/0.22.5，并通过 PkgConfigDeps 接入 |
| 5 | HMDFS umask 077 目录不可写 | configure 创建 0700 临时目录在 HMDFS 上无写权限 | build() 中 replace_in_file 将 umask 077 改为 022 |

## 源码修改

- `patches/0001-config.guess.patch`: 更新 config.guess 以支持 OHOS 平台识别。
- `patches/0002-config.sub.patch`: 更新 config.sub 以接受 aarch64-linux-ohos triplet。
- configure 脚本：build() 中通过 replace_in_file 跳过 intltool 检查（OHOS 未提供）并将 umask 077 改为 022（HMDFS 兼容）。

## 依赖版本

- glib/2.88.0
- gettext/0.22.5

## 验证结果

```text
configure: PASS
make -j1: PASS
make install DESTDIR=...: PASS
make check: PASS (上游无测试目标)
```

## 交付物

| 文件 | 说明 |
|------|------|
| libfm-extra.a | libfm-extra 静态库 |
| fm-extra.h / fm-xml-file.h | 公共头文件 |

## 注意事项

上游 `make check` 没有测试目标，因此 test_package 增加了调用 `fm_xml_file_new()`、`fm_xml_file_parse_data()` 和 `fm_xml_file_finish_parse()` 的实质功能测试。
---

**编译结束**: 2026-08-20 20:38
**最终状态**: built
