# quickjs 2024-01-13 - 适配笔记

## 适配说明

QuickJS 是一个快速、小巧、可嵌入的 JavaScript 引擎。使用 Makefile 构建系统。
源码来源：bellard.org 官方发布（CI Worker 可直接访问，无需 GitCode 镜像）。

## 构建步骤

```bash
make CC="<Conan profile C compiler>" HOST_CC=gcc AR="<Conan profile archiver>" CONFIG_BIGNUM=y -j2
```

上游 `qjsc.c` 硬编码使用 `/tmp/out<pid>.c` 且不读取 `TMPDIR`。补丁将其改为优先
使用 `TMPDIR`；构建前 Conan 再将 `TMPDIR` 设置为 `<build_folder>/_tmp`，避免写入
OHOS 只读的 `/tmp`。上游 Makefile 使用普通赋值设置 `CC` 和 `AR`，会覆盖环境变量，
因此配方从 Conan profile 的 `tools.build:compiler_executables` 读取目标工具后显式传给
`make`；`HOST_CC=gcc` 编译构建期间需要运行的主机工具。

## 构建产物

- `libquickjs.a` - 静态库
- `qjs` - JavaScript 解释器 CLI
- `qjsc` - JavaScript 编译器（将 JS 编译为 C 代码）
- `*.h` - 头文件（在源码根目录，package 时复制到 include/quickjs/）

## 环境变量

- `PATH`：添加 `bin/` 目录，包含 qjs 和 qjsc
- `TMPDIR`：指向 Conan 构建目录中的可写 `_tmp` 子目录

## 测试验证

test_package 验证：
- JS_Eval 执行 JavaScript 表达式
- 静态库可链接使用
- 原生构建执行测试程序；交叉编译只验证目标程序完成编译和链接
