# fribidi 1.0.16 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-07-13
- 编译器: clang/clang++
- 状态: built (conan-verify 通过, W3 本地 CI 通过)

## 源码信息
- URL: https://github.com/fribidi/fribidi/releases/download/v1.0.16/fribidi-1.0.16.tar.xz
- SHA256: 1b1cde5b235d40479e91be2f0e88a309e3214c8ab470ec8a2744d82a5a9ea05c
- 格式: tar.xz

## 编译步骤
1. 下载源码 tarball
2. 打补丁:
   - 0002-config.guess.patch: HarmonyOS 系统识别
   - 0003-config.sub.patch: OHOS 平台支持 (ohos-linux triplet, ohos* OS, linux-ohos* kernel-OS 组合)
3. `./configure --prefix=$DEFAULT_PREFIX`
4. `make -j1`
5. `make install DESTDIR=$TEST_PREFIX`
6. `make check` — 全部通过 (1 PASS, 0 FAIL)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 OHOS | E007: GNU config.guess 无 HarmonyOS 检测分支 | patch-autotools-ohos.pl 打补丁 + 补充 linux-ohos* kernel-OS 组合 |
| 2 | config.sub 报 "Kernel linux not known to work with OS ohos" | config.sub 的 kernel-OS 验证缺少 linux-ohos* 组合 | 在 kernel-OS case 添加 `linux-ohos*` |
| 3 | config.status "can't create confXXXXXX/subs1.awk: Permission denied" | E110: HMDFS 限制 umask 077 创建的临时目录(700权限), 非目录所有者无法写入 | conanfile.py build() 中 replace_in_file 修改 umask 077→002 |
| 4 | configure shebang `#!/bin/sh` 在 OHOS 不存在 | E165: OHOS 无 /bin/sh, 需 /system/bin/sh | conanfile.py build() 中 replace_in_file 修改 shebang |
| 5 | make -j2 报 "mkfifo: Operation not permitted" | HMDFS 不支持 mkfifo (FIFO 创建) | 使用 make -j1 |
| 6 | make 触发 aclocal-1.16 重新生成 | configure 修改导致时间戳更新 | touch 所有 .in 文件和 aclocal.m4 使时间戳最新 |

## 依赖版本
无外部依赖

## 产物
- lib/libfribidi.so.0.4.0 (共享库)
- bin/fribidi (命令行工具)
- include/fribidi/*.h (头文件)
- lib/pkgconfig/fribidi.pc

## 验证结果
- conan-verify: G1-G4 + L2/L4/L5 全部通过 ✅
- W3 本地 CI 模拟: 通过 ✅
- test_package: test_fribidi 链接 fribidi 库, 验证 version_info + charset_to_unicode + log2vis ✅

## 注意事项
- fribidi 同时提供 autotools 和 meson 两种构建系统, 此处使用 autotools (meson 未安装)
- 构建产物包含可执行文件 fribidi, 已创建 commands.json (R38)
- 默认构建共享库 (非系统同名库, 无需 R26 静态配置)
- shebang 和 umask 修复在 conanfile.py build() 方法中处理, 不依赖补丁文件

---

**编译结束**: 2026-07-13 08:35
**最终状态**: built
