# ru-tts 6.2.3 适配笔记

## 编译环境

- 目标系统：HarmonyOS PC（OHOS 6.0，AArch64）
- 构建系统：Conan 2 + custom Clang build
- 编译器：OpenHarmony Clang 15
- 编译日期：2026-09-29
- 状态：built

## 编译步骤

Conan 从上游官方标签源码下载并校验归档，应用 AArch64 参数解析补丁，随后使用配置文件选定的 OHOS Clang 和上游所需的 GNU C11 语言模式编译 `librutts` 与 `ru_tts`。配方保留上游 SONAME `librutts.so.7`、符号版本脚本、`ru_speak` 包装脚本及手册页，并通过 `test_package` 验证真实消费者链接和命令行合成。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | AArch64 上 `ru_tts -v` 打印版本后继续进入错误分支，合成也无法正常结束 | 上游用 `char` 保存 `getopt()` 的返回值；OHOS AArch64 的普通 `char` 为无符号类型，无法表示结束标志 `-1` | 将选项返回值变量改为 `int`，保持 POSIX `getopt()` 接口语义 |
| 2 | 上游 Autotools 探测逻辑陈旧，交叉环境下会引入与产物无关的宿主探测 | 项目构建规则只需编译固定 C 源文件、链接版本脚本和系统库 | 配方使用 Conan 选定的 Clang/LLVM 工具直接构建，不修改公开 ABI |

## 源码修改

- `0001-src-ru_tts.c.patch`：使用 `int` 接收 `getopt()` 结果，修复 OHOS AArch64 无符号 `char` 环境下的 CLI 终止条件。

## 依赖版本

- 无必需第三方依赖；使用 OHOS 系统的 libc、libm 和 libdl。
- RuLex 发音词典保持上游的运行时可选加载行为。

## 验证结果

上游测试基数通过官方 `v6.2.3` 归档复核：检查完整目录树以及 `Makefile.am`、`src/Makefile.am`、`configure.ac` 中的 `TESTS`、`check_PROGRAMS`、`make check` 入口，均未发现测试目录、测试目标或测试框架。复核命令与源码 SHA-256 已记录在 `test_package/MANIFEST.yml`。

```text
上游测试清点：0（v6.2.3 未提供测试目录、测试目标或测试框架）
新增通用 API/消费者断言：12/12 通过
新增 HarmonyOS/AArch64 专有断言：6/6 通过
打包 CLI 场景：4/4 通过
总计：22/22 通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| `include/ru_tts.h` | C/C++ 公共 API |
| `lib/librutts.so*` 或 `lib/librutts.a` | 共享库或静态库 |
| `bin/ru_tts` | KOI8-R 文本合成命令行工具 |
| `bin/ru_speak` | 上游播放包装脚本 |
| `share/man` | 上游手册页 |

## 注意事项

输入文本须遵循上游约定使用 KOI8-R 编码；未提供 RuLex 数据库时仍可正常合成，只是不执行词典查询。
