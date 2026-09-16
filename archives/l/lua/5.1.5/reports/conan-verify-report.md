# Lua 5.1.5 Conan 验证报告

## 环境

- 设备：HarmonyOS PC，aarch64
- 系统：HarmonyOS 6.1.0
- Conan profile：`os=OHOS`、`os.version=6.0`、`arch=armv8`
- 编译器：clang 15.0.4
- Conan：2.29.1
- 包引用：`lua/5.1.5@ohpcd/stable`

## 自动门禁

| 门禁 | 结果 | 证据 |
| --- | --- | --- |
| G0 风险查询 | 信息项 | 验证器将手写 Makefile 源清单识别为 unknown，不影响构建 |
| G1 配方完整性 | PASS | 配方、源码元数据、两份补丁和 test_package 完整 |
| G2 `conan create` | PASS | 清洁下载、补丁应用、编译、打包及 consumer 执行成功 |
| G3 系统同名库隔离 | PASS | 包内没有冲突的共享库 |
| G4 产物完整性 | PASS | 头文件、静态库、man page 和许可证齐全 |
| L2 命令 smoke | N/A | 依赖包不导出 `bin/` |
| L4 可执行文件安全扫描 | N/A | 包中只有静态归档，没有 ELF 可执行文件或共享库 |
| L5 产物基线 | 手工 PASS | 包目录、静态库大小、对象数和 SHA-256 已复核 |

验证器没有从 Conan 输出中解析出 package ID，因此自动 L2/L4/L5 查找显示跳过。实际包路径已根据 `conan create` 输出定位并人工复核；这里没有把跳过伪装成自动通过。

通用 G0 `clean-verify` 能从原始压缩包应用两份标准上下文补丁，随后因工具固定调用不存在的 `./configure` 而退出。Lua 5.1.5 是纯手写 Makefile 项目；实际清洁构建由 G2 与 W3 的 `conan create` 完成。

## W3 本地 CI 模拟

| 检查 | 结果 | 说明 |
| --- | --- | --- |
| JC | PASS | 增量检查只包含 Lua 5.1.5 配方文件 |
| L0 | PASS | 结构、元数据、补丁和测试入口门禁通过 |
| L1 | PASS | test_package 执行，破坏性反向测试确认真实依赖包产物 |
| L2 | SKIP | 静态依赖包没有 `bin/` |
| L4 | WARN | 扫描器在补丁删除行中匹配到上游旧 `strcpy`；新增实现使用有长度上限的 `snprintf` |
| L5 | PASS | `lib/` 内容存在 |

W3 结果为 1/1 包成功，日志 SHA-256 为 `1309e8be4c56465affa1f6551661b5364f6ce6af5dd4a81b0902eeb9cf2ca1c4`。日志明确记录 `make test SHELL=/bin/sh`、`src/lua test/hello.lua` 和 `Hello world, from Lua 5.1!`。L1c 的提示文字只识别 `make check/ctest`，没有识别上游目标名 `make test`；实际命令和输出均已存在。

## Conan 结果

- 完整引用：`lua/5.1.5@ohpcd/stable#f7c99e4ef0873a55826a066190db1c6f:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa#3ddf429d832992c777d92a9e98dae43d`
- Recipe revision：`f7c99e4ef0873a55826a066190db1c6f`
- Package ID：`4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`
- Package revision：`3ddf429d832992c777d92a9e98dae43d`
- 构建：PASS
- 消费者程序：PASS，8/8 行为检查通过

## 包内容

- 23 个 `.h` 文件和一个 `lua.hpp`
- `lib/liblua.a`：ar 归档，336292 bytes，29 个对象
- `liblua.a` SHA-256：`0e95971104509d32780e568383c028d38fdd151c5d5717b0d41adfb373fe9357`
- `man/man1/lua.1`、`man/man1/luac.1`
- `licenses/COPYRIGHT`
- 无 `bin/`、`.so` 或预编译产物

## 结论

目标平台的库构建、打包和消费验证通过，状态可记为 `built`。本报告只覆盖本地目标机验证，不宣称 CI upload、发布或合并完成。
