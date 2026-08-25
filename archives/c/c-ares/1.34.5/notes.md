# c-ares 1.34.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-22
- 编译器: clang 15.0.4 (OHOS aarch64)
- 链接器: ld.lld
- 状态: built (真机验证通过)

## 适配策略
基于已验证的 1.34.6 配方，复用全部 3 个平台适配补丁，额外修复链接器和补丁行号问题。

## 补丁兼容性验证
| 补丁 | 目标文件 | 应用结果 |
|------|----------|----------|
| 0001-config-config.guess.patch | config/config.guess | ✅ 直接应用 |
| 0002-config-config.sub.patch | config/config.sub | ✅ 直接应用 |
| 0003-configure.patch | configure | ✅ 行号修正为 1.34.5 |

## 编译步骤
1. 下载源码 c-ares-1.34.5.tar.gz (SHA256: 7d9357...)
2. 应用补丁: config.guess, config.sub, configure (umask fix)
3. ./configure --enable-static --disable-shared LD=ld.lld
4. make -j1
5. make install

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: error: could not setup config files machinery | E129: HMDFS umask 077 blocks temp dir creation | 补丁 0003-configure.patch: umask 077→022 |
| 2 | platform not recognized (aarch64-unknown-linux-ohos) | E007: config.guess/sub 缺少 HarmonyOS 检测 | 补丁 0001/0002: 添加 ohos 平台识别 |
| 3 | 0003-configure.patch 应用失败 (premature end of source file) | patch 行号基于 1.34.6，1.34.5 configure 行数不同 | 修正 patch hunk 行号为 1.34.5 的实际行号 |
| 4 | configure: error: no acceptable ld found in $PATH | OHOS 无 GNU ld，只有 ld.lld | conanfile.py: configure(args=["LD=ld.lld"]) + LDFLAGS=-fuse-ld=lld |

## 验证结果
- conan create: PASS ✅
- test_package 编译+链接: PASS ✅
- test_package 执行: PASS ✅ (1/1 tests passed, 0.03 sec)
- 产物: libcares.a (static), ares.h + 5 headers, libcares.pc

## 与 1.34.6 的差异
- 版本号不同
- configure 中 patch hunk 行号不同（已修正）
- 需要显式指定 LD=ld.lld（1.34.6 可能也有此问题，待确认）

---

**适配完成**: 2026-08-22
**最终状态**: 真机验证通过
