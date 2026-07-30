# luau 0.689-r0 编译笔记

## 编译信息
- 时间: 2026-05-26
- 编译器: clang++ 15.0.4
- 目标平台: aarch64-unknown-linux-ohos
- 构建系统: CMake

## 构建步骤

### 1. 源码下载
```bash
wget https://github.com/luau-lang/luau/archive/refs/tags/0.689.tar.gz
```

### 2. 配置
```bash
cmake -DCMAKE_CXX_COMPILER=clang++ \
      -DCMAKE_C_COMPILER=clang \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
      -DLUAU_BUILD_TESTS=OFF \
      ../source
```

### 3. 编译
```bash
make -j$(nproc)
```

### 4. 安装
手动安装（项目无 install 目标）：
- 二进制文件: luau, luau-analyze, luau-ast, luau-bytecode, luau-compile, luau-reduce
- 静态库: libLuau*.a
- 头文件: Luau/, lua.h, luaconf.h, lualib.h, luacode.h, luacodegen.h

## 问题与解决

### CMake 平台识别
CMake 输出警告 "System is unknown to cmake, create: Platform/HarmonyOS"，但不影响编译。

### 无 install 目标
项目未提供标准 install 目标，需要手动复制文件到安装目录。

## 上游测试

上游使用 doctest，`luau-tests` 目标覆盖 `Luau.UnitTest` 和
`Luau.Conformance`。测试用例数通过以下命令从 0.689 官方源码统计：

```bash
make -j4 luau-tests
./luau-tests --list-test-cases
./luau-tests
```

官方源码的本机基线验证结果为：

```text
test cases: 4426 | 4426 passed | 0 failed | 0 skipped
assertions: 34266 | 34266 passed | 0 failed
```

- 上游测试用例数：4426
- 上游测试用例通过率：4426/4426（100%）
- 上游测试用例修改：无

Conan 配方在 `can_run(self)` 为真时启用 `LUAU_BUILD_TESTS`，并依次执行
`Luau.UnitTest`、`Luau.Conformance` 和 `Luau.CLI.Test`。交叉编译且目标
程序不能在构建机运行时，配方关闭上游测试目标，`test_package` 也跳过
运行时测试，避免直接执行不兼容架构的二进制文件。HarmonyOS 消费者验证
实质调用 Luau C API，并检查 `luau --help`。

## 测试结果

- 编译成功
- 上游测试：4426/4426（100%）
- 上游断言：34266/34266（100%）
- 消费者测试：2/2（100%），包括 C++ API CTest 和 `luau --help`
- 无标准版本输出（`luau --help` 可用）

本地 CI 模拟使用仓库 `ci/conan/build_and_test.sh` 和本机原生 Conan
profile 完成。L0、L1、L2、L4、L5 均通过；`luau-reduce` 不支持标准
`--help`/`--version` 探测，CI 将其记录为非阻塞提示，其他 5 个正式 CLI
探测均通过。HarmonyOS 专用 profile 依赖 CI 环境中的 `/data/service/hnp`
工具链，因此本机预审不冒充 HarmonyOS 目标机执行结果。

## 产物清单

### 可执行文件
- luau (1.5M) - REPL/解释器
- luau-analyze (5.4M) - 静态分析工具
- luau-ast (5.4M) - AST 工具
- luau-bytecode (1.0M) - 字节码工具
- luau-compile (1.3M) - 编译器
- luau-reduce (435K) - 简化工具

### 静态库
- libLuau.Analysis.a
- libLuau.Ast.a
- libLuau.CLI.lib.a
- libLuau.CodeGen.a
- libLuau.Compiler.a
- libLuau.Config.a
- libLuau.EqSat.a
- libLuau.Require.a
- libLuau.RequireNavigator.a
- libLuau.VM.a

## 知识提取
无新错误模式。编译流程顺畅，仅需注意手动安装步骤。
---

**编译结束**: 2026-05-26 19:33
**最终状态**: built
