# DRAFT-makefile-no-lib-target-explicit-static — 上游 Makefile 无库/install 目标：配方显式编译静态库

> **Contributor**: pc7-1 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium | **Category**: build / makefile / conan / static-lib
> **Audience**: 适配纯 Makefile 小型 C 库（单文件/函数级实现，Makefile 只提供 test 目标）

## 问题（真实首错）

上游 `jwerle/asprintf.c` v0.0.3 的 `Makefile` 只有 3 个目标：

```make
SRC = asprintf.c
all: clean test      # 只跑测试, 不产出库
test:                # 编译 test.c + asprintf.c → ./test, 执行
install: $(BIN)      # $(BIN) 从未定义 → 无可安装目标
```

- 没有任何 `libasprintf.a`/`.so` 库目标；
- `install: $(BIN)` 依赖的 `$(BIN)` 变量未定义，`make install` 实际是空操作；
- 官方发布形式是 `asprintf.c` + `asprintf.h` 两个源码文件，无构建产物。

若 Conan 配方只执行 `make install` 或等待 Makefile 产出库文件，`package()` 将
拿不到任何产物 → G4 产物完整性失败，消费者链接失败。

## 根因

上游将库的"构建"定义为编译期直接包含源码（header-only 风格的单文件实现），
Makefile 仅服务测试，未提供库/安装目标。Conan 配方必须承担库产物的构建职责，
而不是假设上游构建系统产出 `.a`。

## 解决方案

在配方的 `build()` 内用 R33 合规方式（从 Conan conf 取编译器，不用裸 shell 变量）
显式编译静态库并运行上游官方测试入口：

1. **上游测试入口**：`self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} CFLAGS=... test")`
   —— 编译并执行 test.c（3 组断言），满足 L1 与双口径测试台账的上游用例。
2. **显式静态库**：
   ```python
   self.run(f"{cc} {cflags} -c asprintf.c -o libasprintf.a.tmp.o && "
            f"{ar} rcs libasprintf.a libasprintf.a.tmp.o && {ranlib} libasprintf.a")
   ```
3. **package()**：只安装公开头文件 `asprintf.h` 到 `include/`、`libasprintf.a` 到 `lib/`。
4. **package_info()**：`self.cpp_info.libs = ["asprintf"]`、libdirs/includedirs 指向包内目录。

编译器和归档工具取自 `self.conf.get("tools.build:compiler_executables", default={})`
（OHOS 上为 clang/llvm-ar/llvm-ranlib），不得使用 `${CC}`/`${AR}` 裸 shell 变量（R33）。

## 验证

- G2 conan-verify：`conan create` 干净构建通过，包内含 `include/asprintf.h` +
  `lib/libasprintf.a`（L5 产物基线通过）。
- L1：`make test` 上游用例真实运行（日志含 `make test` + 3 组断言），test_package
  消费者 `test_consume` 编译链接运行通过（`1/1 Test #1: test_consume ... Passed`）。
- 消费者链接：test_package/CMakeLists.txt 通过 `asprintf.c::asprintf.c` target 链接
  包内 libasprintf.a，运行输出 4 组真实结果。

## 适用边界

- ✅ 适用：上游是纯 Makefile、无库/install 目标、官方发布为单文件实现的
  C 库（asprintf、snprintf、strsep、ringbuffer 等函数级库）。
- ❌ 不适用：上游已有 `make install` 且产出库文件的库——应按常规 make/install
  流程走；也不适用于 configure/cmake/meson 构建的库。
- ⚠️ 与 `E097`（bearssl 自定义 Makefile 手工 install）不重复：E097 是"无 configure、
  用 SingleUnix.mk/conf/ 自定义构建+手工 install 路径"；本条是"Makefile 根本没有
  库/install 目标，必须由配方承担库产物编译"，根因与修复动作不同。

## 禁止

- ❌ 把测试可执行文件 `test` 误当库产物拷贝进 package（`test` 是测试主程序，不是库）。
- ❌ 在 package() 里 `copy("asprintf.c")` 源码冒充库产物（消费者需要链接产物，
  不是再编译源码）。
- ❌ 用 `${CC}`/`${AR}` 裸变量（R33），应走 `self.conf.get("tools.build:compiler_executables")`。

## Source

- 库/事件：asprintf.c 0.0.3 OHOS 适配（task asprintf.c-0.0.3-r01-pc7-1-20260920T123513Z），
  G2 干净构建 + L1 通过，包产物 include/asprintf.h + lib/libasprintf.a。
- 证据：`archives/a/asprintf.c/0.0.3/conanfile.py`、`reports/conan-create.log`
  （make test + ar rcs + 消费者运行）、`reports/conan-verify-report.md`。
