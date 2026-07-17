# pcre 8.45 适配笔记

**日期**: 2026-07-15
**状态**: ✅ 适配完成（published: conan-verify 全部通过）

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|-------|
| Step 1 init-build | ✅ | 源码下载、解压、环境检查 |
| Step 2 configure | ✅ | 应用 autotools-ohos 补丁 + umask 修复 |
| Step 3 make | ✅ | 编译成功 |
| Step 4 install DESTDIR | ✅ | staging 安装成功 |
| Step 5 make check | ✅ | 5/5 测试全部通过 |
| Step 6 conan-init | ✅ | 生成 conanfile.py + conandata.yml + test_package/ |
| Step 7 conan-verify | ✅ | G0-G4 + L2/L4/L5 全部通过 |
| Step 8 finish (W3) | ✅ | 本地 CI 模拟通过 |

## 发现与知识

### 1. E011: HMDFS umask 权限问题
**问题**: configure 和 config.guess 创建临时目录时 umask 077 导致 Permission denied
**根因**: HMDFS 的 UID 映射机制导致 umask 077 创建的目录无法被当前进程写入
**解决**: 在 conanfile.py build() 方法中使用 replace_in_file 将 umask 077 改为 022

### 2. E007: config.guess 无法识别 HarmonyOS
**问题**: config.guess 没有 HarmonyOS 检测分支，返回 "unable to guess system type"
**根因**: 使用 patch-autotools-ohos.pl 脚本添加 HarmonyOS 检测，但原脚本生成的 HarmonyOS case 缺少 `echo "$GUESS"; exit` 语句，导致 GUESS 被设置但未输出
**解决**: 在 config.guess 的 HarmonyOS case 中添加 `echo "$GUESS"; exit`，同时修复 umask 077 -> 022
**补丁**: 0002-config.guess.patch

### 3. E007 补充: config.sub kernel-os 验证
**问题**: config.sub 报 "Kernel `linux' not known to work with OS `ohos'"
**根因**: config.sub 的 kernel-os 组合验证缺少 linux-ohos*
**解决**: 在 config.sub 的 kernel-os 验证列表中添加 `| linux-ohos*`，同时在 OS 列表添加 ohos*
**补丁**: 0003-config.sub.patch

### 4. CMake 最小版本
**问题**: CMakeLists.txt 要求最小版本 2.8.5，CMP0026 策略在新版 CMake 中已移除
**解决**: 将最小版本提升到 3.10，注释掉 CMP0026 策略
**补丁**: 0001-CMakeLists.txt.patch

## 测试结果

| 测试 | 状态 | 备注 |
|------|------|------|
| pcrecpp_unittest | PASS | C++ wrapper unit tests |
| pcre_scanner_unittest | PASS | Scanner unit tests |
| pcre_stringpiece_unittest | PASS | StringPiece unit tests |
| RunTest | PASS | Main PCRE library test suite |
| RunGrepTest | PASS | pcregrep test suite |

**Total: 5/5 PASS**

---

**适配完成**: 2026-07-15
**最终状态**: built
