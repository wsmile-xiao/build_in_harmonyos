# xcb-util-keysyms 0.4.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4 (OHOS SDK)
- 状态: published

## 编译步骤

使用 x.org 官方 release tarball（包含预生成 configure 和 Makefile.in），通过 Conan 配方完成：
1. 下载 release tarball 并解压（sha256 已核验）
2. conan create（-pr=ohos-aarch64，--build=missing）
3. configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --enable-shared --disable-static
4. make && make check（上游无测试程序，check 为 automake 空目标 no-op）
5. make install → test_package 编译运行（keysym 分类 API smoke test 通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | xcbproto_version 变量缺失 | Conan PkgConfigDeps 生成的 xcb.pc 缺少 XCB_UTIL_COMMON 宏查询的自定义变量 | generate() 中向 conan/xcb.pc 追加 `xcbproto_version=1.17.0` |
| 2 | libxcb 的 .la 文件链接失败 | Conan 生成的 .la 引用其他包 .la 绝对路径（libXau.la 等）在 Conan 布局中不存在 | 构建共享库时删除 libxcb 包 lib/ 下 .la 文件，libtool 回退 pkg-config -l 标志 |
| 3 | config.guess 无法识别鸿蒙 | release tarball 内置 config.guess 过旧 | 显式传 --build/--host=aarch64-unknown-linux-gnu triplet |
| 4 | configure shebang/umask 问题 | OHOS 无 /bin/sh、umask 077 导致 temp 目录不可执行 | build() 中 replace_in_file umask 077→022，shebang 替换为 /data/service/hnp/bin/bash |

## 依赖版本
- libxcb/1.17.0（依赖 libxau/1.0.11、libxdmcp/1.1.5、xtrans/1.4.0）
- xorgproto/2025.1（提供 xproto.pc）
- xcb-proto/1.17.0（libxcb 编译期依赖，已发布）

## 验证结果

```bash
$ conan create archives/x/xcb-util-keysyms/0.4.1 -pr=ohos-aarch64 --build=missing
# exit=0，G0-G4/L2/L4/L5 全部 PASS
# test_package: xcb-util-keysyms api smoke ok
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools，shared 动态库） |
| conandata.yml | 官方源 URL + sha256 |
| test_package/ | test.c（keysym 分类 API smoke test）+ CMake + conanfile |
| reports/conan-verify-report.md | 8 道门禁验证报告 |

## 注意事项
- R38 判断：纯库包（仅 libxcb-keysyms.so.1.0.0、头文件、pc 文件），无可执行文件，不需要 commands.json
- 上游无测试目录（keysyms/ 仅库源码），make check 为空目标，见 test_package/MANIFEST.yml 清点证据
---

**编译结束**: 2026-09-24 01:00
**最终状态**: published
