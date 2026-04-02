# dos2unix 7.5.4 测试报告

## 测试环境

- **平台**: HarmonyOS aarch64
- **编译器**: clang 15.0.4
- **测试命令**: `make -j1 test`
- **测试框架**: prove (TAP)

## 测试结果汇总

| 测试文件 | 通过 | 失败 | 总数 | 结果 |
|---------|------|------|------|------|
| ascii.t | 18 | 12 | 30 | ⚠️ 部分通过 |
| iso.t | 14 | 0 | 14 | ✅ 全部通过 |
| misc.t | 17 | 0 | 17 | ✅ 全部通过 |
| bom.t | 8 | 0 | 8 | ✅ 全部通过 |
| noeol.t | 13 | 12 | 25 | ⚠️ 部分通过 |
| stdio.t | 7 | 0 | 7 | ✅ 全部通过 |
| symlink.t | 6 | 8 | 14 | ❌ 失败 |
| **合计** | **83** | **32** | **115** | **72% 通过** |

## 失败分析

### 1. mac2unix/unix2mac 不可执行 (24 个失败)

**测试**: ascii.t (12), noeol.t (12)
**原因**: mac2unix 和 unix2mac 是指向 dos2unix/unix2dos 的软链接。在构建目录 ($HOME/tmp/builds/) 中，HarmonyOS SELinux 限制导致 `ln -s` 创建的软链接无法执行。测试脚本尝试执行 `../mac2unix` 得到 "Permission denied"。
**影响**: 不影响实际安装后的功能（$HOME/usr/local/bin/ 中的软链接可正常工作）。

### 2. 软链接测试失败 (8 个失败)

**测试**: symlink.t (8)
**原因**: HarmonyOS HMDFS/SELinux 限制在 $HOME/tmp/ 目录中创建软链接，导致测试无法建立测试用的软链接文件。
**影响**: dos2unix/unix2dos 的软链接跳过功能在受限目录无法验证，核心转换功能不受影响。

## 核心功能验证

| 功能 | 状态 | 验证方法 |
|------|------|---------|
| dos2unix: CRLF → LF | ✅ | 实际文件转换 + xxd 验证 |
| unix2dos: LF → CRLF | ✅ | 实际文件转换 + xxd 验证 |
| Unicode UTF-16 转换 | ✅ | iso.t, misc.t 测试通过 |
| UTF-8 BOM 处理 | ✅ | bom.t 测试通过 |
| 二进制文件跳过 | ✅ | misc.t 测试通过 |
| stdin/stdout 管道 | ✅ | stdio.t 测试通过 |

## 结论

**兼容性评级: 高**

dos2unix/unix2dos 核心功能完全可用。所有失败均为 HarmonyOS 平台环境限制，非功能性问题。
