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

## 测试结果
- ✅ 编译成功
- ✅ 可执行文件可运行
- ⚠️ 无标准版本输出（luau --help 可用）

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
