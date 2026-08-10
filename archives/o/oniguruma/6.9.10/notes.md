# oniguruma 6.9.10 适配笔记

## 编译环境
- 构建系统: cmake（autotools 失败，临时文件创建权限问题）
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码：from GitHub releases v6.9.10
2. 应用 autotools 补丁：patch-autotools-ohos.pl（config.guess/config.sub）
3. 尝试 autotools configure：失败（config.status 无法创建临时文件）
4. 切换到 CMake：
   ```bash
   cmake -B build -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release
   make -j$(nproc)
   make install DESTDIR=/storage/Users/currentUser/tmp/test-install-oniguruma-6.9.10
   ```
5. 运行测试：test_utf8, testc, test_syntax 全部通过（SUCC: 221, FAIL: 0, ERROR: 0）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 缺少 HarmonyOS 检测分支 | 应用 patch-autotools-ohos.pl |
| 2 | config.sub 不认识 linux-ohos | 缺少 ohos 三元组定义 | 手动修复 config.sub（重复行 + linux-ohos 验证） |
| 3 | autotools configure 失败：临时文件创建权限拒绝 | HMDFS 文件系统限制：mktemp 创建目录但无法在其中创建文件 | 切换到 CMake 编译 |
| 4 | CMAKE_INSTALL_PREFIX 使用绝对路径导致 DESTDIR 路径异常 | CMake 绝对路径特性 | 后续打包时处理 |

## 源码修改

**config.guess**（补丁脚本应用后手动修复）：
- 第 140 行：添加 HarmonyOS 到 LIBC 检测分支（`Linux|GNU|GNU/*|HarmonyOS)`）
- 第 178 行后：添加输出语句（`echo "$GUESS"; exit 0`）

**config.sub**（补丁脚本应用后手动修复）：
- 第 145-150 行：修复重复的 basic_machine/basic_os 定义
- 第 1746 行：添加 linux-ohos 到内核组合验证

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- make: 4.4.1

## 验证结果

```bash
# 测试程序运行结果
test_utf8: SUCC: 221, FAIL: 0, ERROR: 0
testc: PASS
test_syntax: SUCC: 221, FAIL: 0, ERROR: 0

# Staging 产物完整性
libonig.so: 686KB（动态库）
oniguruma.h: 49KB（头文件）
oniggnu.h: 3KB（GNU扩展头文件）
onig-config: 1KB（配置脚本）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libonig.so | 686KB | 动态库 |
| oniguruma.h | 49KB | 主头文件 |
| oniggnu.h | 3KB | GNU 扩展头文件 |
| onig-config | 1KB | 配置脚本 |

## 注意事项

- autotools 编译失败，使用 CMake 替代
- CMake 配置时 HarmonyOS 系统类型未知，但不影响编译
- 需后续处理 DESTDIR 路径异常问题
---

**编译结束**: 2026-08-07 06:31
**最终状态**: built
