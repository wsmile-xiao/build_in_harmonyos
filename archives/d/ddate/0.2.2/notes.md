# ddate 0.2.2 适配笔记

## 编译环境
- 构建系统: cmake（单可执行文件 + gzip 压缩 man 页）
- 编译日期: 2026-09-10
- 编译器: clang/clang++（待 HMBS 真机预检确认版本）
- 状态: built（配方完成，待真机验证；验证通过前不标 published）
- 源码: https://github.com/bo0ts/ddate/archive/refs/tags/v0.2.2.tar.gz
- 源码 SHA256: d53c3f0af845045f39d6d633d295fd4efbe2a792fd0d04d25d44725d11c678ad（8049 字节，与 Debian ddate_0.2.2.orig.tar.gz 大小一致）

## 编译步骤

标准 CMake 流程，无特殊配置：

```bash
cmake -S . -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release
cmake --build build
cmake --install build --prefix <package>
```

conanfile.py 通过 CMakeToolchain 以 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"` 注入兼容变量，
`build()` 仅执行 configure + build（上游无测试目标，不调用 cmake.test()）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `cmake_minimum_required(VERSION 2.8)` 在 CMake 4.x 下 configure 被拒 | CMake 4 移除了对 < 3.5 的兼容 | generate() 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（知识 E187/E103，abcmidi/precomp/bambootracker 先例）；旧版 CMake 下仅为未使用变量警告，无害 |
| 2 | man 页构建需要 `gzip`（CMakeLists add_custom_command 调用 `gzip -c -9`） | 上游构建时压缩 man 页 | 暂不处理：gzip 在 Linux/OHOS 构建环境普遍可用；若真机预检报缺 gzip，再将 manpage 目标改为可选并记录 |
| 3 | 上游无测试套件 | 单文件工具，无 tests/ 目录、无 add_test、无 check 目标 | 按 no_tests 口径申报：test_package/MANIFEST.yml 含完整审计，test() 复发 HMBS_UPSTREAM_TEST_RESULT status=no_tests（sipcalc/buildtorrent 先例） |

## 源码修改

无。零补丁适配（源码仅依赖 stdlib/string/time/stdio，可移植；`__builtin_types_compatible_p` 为 clang 兼容的 GCC 扩展）。

## 依赖版本

无外部依赖（自包含）。

## 验证结果

本地 Windows 环境未执行编译与测试（按规范，真机验证由 HMBS 后台统一执行）。

test_package 设计（test_ddate.sh，6 项内容级验证，待真机实测）：

| # | 验证项 | 命令 | 断言 |
|---|--------|------|------|
| 1 | 无参输出当前日期 | `ddate` | 输出含 "Today is" 且含 "YOLD" |
| 2 | 指定日期转换 | `ddate 1 1 2026` | 输出含 "Chaos" 且含 "3192 YOLD"（2026+1166） |
| 3 | 格式化年号 | `ddate "+%Y" 1 1 2026` | 输出恰为 "3192" |
| 4 | 格式化季节 | `ddate "+%B" 1 1 2026` | 输出恰为 "Chaos" |
| 5 | 非法日期拒绝 | `ddate 99 99 2026` | 非零退出且输出 "Invalid date" |
| 6 | 错误参数用法提示 | `ddate -z` | 退出码 1 且 stderr 含 "usage:" |

## 交付物

待真机预检产生（bin/ddate + share/man/man1/ddate.1.gz）。

## 注意事项

- ddate 是命令行工具（package_type=application），软件级已声明 commands.json（R38）。
- CLI 参数顺序为 Commonwealth 格式 `day month year`（US_FORMAT 未定义），测试用例据此编写。
- `%H` 庆祝语每次随机（srandom(time)），测试不断言其内容，避免 flaky。
- 本轮未提交、未推送，待 HMBS 真机全部门禁通过后统一提交。
