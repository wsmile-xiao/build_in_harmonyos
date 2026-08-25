# msgpack 7.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-24
- 编译器: clang/clang++ (OHOS aarch64 profile)
- 状态: built

## 上游确认

- 官方仓库: https://github.com/msgpack/msgpack-c
- 7.0.1 tag: `c-7.0.1`（msgpack-c 发布的 C 版本）
- 源码下载: https://github.com/msgpack/msgpack-c/releases/download/c-7.0.1/msgpack-c-7.0.1.tar.gz
- sha256: `2d80f190ab89b73b513025d8aef09b144e5c07b3734dfe99dd0137725d355504`
- License: BSL-1.0 (Boost Software License)

## 包类型确认

msgpack-c 7.0.1 **是真实编译的 C 库**（非 header-only）。上游 CMakeLists.txt:

- 从 `src/objectc.c src/unpack.c src/version.c src/vrefbuffer.c src/zone.c` 编译出 `libmsgpack-c`
- 安装 `include/msgpack.h` + `include/msgpack/*.h`（含 configure 生成的 `pack_template.h`、`sysdep.h`）
- 安装 `msgpack-c.pc`（pkg-config name = `msgpack-c`）和 CMake config `lib/cmake/msgpack-c/msgpack-c-config.cmake`
- target 名为 `msgpack-c`，SOVERSION 2

> 注意：msgpack 项目另有 C++ header-only 变体（`msgpack-cpp`），不在本配方范围内。

## CMake 配置

优先使用上游 CMake。从 7.0.1 `CMakeLists.txt` 实际确认的 option：

| Option | 说明 | 设定 |
|--------|------|------|
| MSGPACK_BUILD_TESTS | 上游单元测试（需 GTest+ZLIB） | OFF |
| MSGPACK_BUILD_EXAMPLES | 示例程序 | OFF |
| MSGPACK_GEN_COVERAGE | gcov 覆盖率 | OFF |
| MSGPACK_ENABLE_SHARED | 构建动态库 | 跟随 options.shared |
| MSGPACK_ENABLE_STATIC | 构建静态库 | 跟随 options.shared（默认 static）|
| MSGPACK_32BIT | 32 位编译 | 未设 |
| MSGPACK_CHAR_SIGN | char 符号 | 未设 |

默认 `shared=False`（R26：系统同名库默认静态），产出 `libmsgpack-c.a`。

## 实际依赖

无运行时依赖，仅需 C 标准库。上游测试依赖 GTest/ZLIB/Threads，但测试已关闭，不影响库本身。

## 编译步骤

```
conan create archives/m/msgpack/7.0.1 \
    -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --build=msgpack/*
```

## 源码修改

无补丁。上游 7.0.1 在 OHOS aarch64 下直接用 CMake 构建成功。

## 验证结果

`ci/conan/build_and_test.sh archives/m/msgpack/7.0.1` 本地执行,关键阶段全部通过:

- JC/KC 质量门: `JC_ERRORS=0`, `KC_ERRORS=0`(junk/commit 规范全过)
- `conan create`: 产出 `libmsgpack-c.a`,打包 `include/msgpack*` + `msgpack-c.pc` + cmake config
- test_package 编译链接: `Built target test_msgpack`(链接 `msgpack-c::msgpack-c`)
- test() 执行: 所有断言通过,末尾输出 `all msgpack round-trip assertions passed`
- `[ok] msgpack/7.0.1 — conan create passed`
- L1a/L1b: test_package 已由 conan create 执行,日志含测试证据
- L5: `lib/` 含库产物(library package)

> 注:本地环境内存紧张(31G/30G used),脚本在 L5 之后的收尾统计阶段被 SIGTERM 终止,
> 属环境性问题,非配方缺陷。核心构建+测试阶段均已完成并通过。

## 上游测试实际验证

上游 msgpack-c 7.0.1 `test/` 目录有 **5 个 .cpp 源文件**，对应 **5 个 executable / 5 个 CTest target**，
共 **103 个 GTest TEST case**（统计自源码 `grep -E 'TEST(|TEST_F('`）：

| 源文件 | GTest case 数 | 可执行程序 |
|--------|--------------|-----------|
| test/buffer_c.cpp | 4 | buffer_c |
| test/fixint_c.cpp | 1 | fixint_c |
| test/msgpack_c.cpp | 92 | msgpack_c |
| test/pack_unpack_c.cpp | 4 | pack_unpack_c |
| test/streaming_c.cpp | 2 | streaming_c |
| **合计** | **103** | **5** |

上游测试依赖 `GTest + ZLIB + Threads`（MSGPACK_BUILD_TESTS=ON 时启用）。为了不把这些测试依赖
错误地加入 msgpack-c 本体运行时依赖，**配方中 MSGPACK_BUILD_TESTS 仍保持 OFF**（库本身零运行时依赖），
上游测试在**独立 CMake 项目**中用 Conan 包依赖编译运行：

- `gtest/1.17.0`（仓库 archives/g/gtest/1.17.0，本机已 conan create 通过）
- `zlib/1.3.1.1`（仓库 archives/z/zlib/1.3.1.1，conan cache 已有 OHOS aarch64 二进制）
- `msgpack/7.0.1`（本配方产物，链接 `msgpack-c::msgpack-c`）

### 编译结果

5/5 executable 全部编译链接成功（链接 `msgpack-c::msgpack-c + gtest + gtest_main + ZLIB + Threads`）。

### 运行结果（OHOS aarch64）

| 可执行程序 | GTest case | 结果 |
|-----------|-----------|------|
| fixint_c | 1 | ✅ 1/1 PASSED |
| msgpack_c | 92 | ✅ 92/92 PASSED |
| pack_unpack_c | 4 | ✅ 4/4 PASSED |
| streaming_c | 2 | ✅ 2/2 PASSED |
| buffer_c | 4 | ❌ 2 passed, 2 failed |
| **合计** | **103** | **101 passed, 2 failed, 0 skipped** |

### 失败 case 真实原因（平台限制，非库缺陷）

**buffer.fbuffer_c** (exit -6 / SIGABRT):
- 上游测试调用 `tmpfile()` 创建临时 `FILE*`（buffer_c.cpp:42 `FILE* file = tmpfile();`）
- `tmpfile()` 返回 NULL，后续对 NULL `FILE*` 操作触发 SIGABRT

**buffer.vrefbuffer_c** (exit 1):
- 同样依赖 `tmpfile()`（buffer_c.cpp:125/130 断言行）
- `tmpfile()` 返回 NULL 导致 `EXPECT_TRUE(file != NULL)` 断言失败

### tmpfile() 专项验证（纯 libc probe，未修改任何上游测试）

编写最小 C probe `FILE *f = tmpfile()`，输出返回值/errno/strerror，
在 5 种环境变量组合下分别运行：

| 环境 | tmpfile() 返回 | errno | strerror |
|------|---------------|-------|----------|
| 默认 (TMPDIR/TMP/TEMP 全 unset) | NULL | 13 | Permission denied |
| TMPDIR → 可写工作目录 | NULL | 13 | Permission denied |
| TMP → 可写工作目录 | NULL | 13 | Permission denied |
| TEMP → 可写工作目录 | NULL | 13 | Permission denied |
| TMPDIR+TMP+TEMP 同时指向可写目录 | NULL | 13 | Permission denied |

**结论：设置 TMPDIR/TMP/TEMP 无法解决——musl `tmpfile()` 不检查这些环境变量，固定使用 `/tmp`。**

### /tmp 权限证据

```
ls -ld /tmp  →  drwxr-xr-x 2 root root 27 2024-06-06 /tmp
touch /tmp/.mp_test  →  Read-only file system (exit 1)
readlink -f /tmp  →  /tmp (非符号链接)
```

- `/tmp` 存在但挂载为**只读文件系统**（root:root，无写权限）
- `errno=13 (Permission denied)` 与 `Read-only file system` 一致
- 工具链中无可见 musl 源码，但经验证据确凿：
  musl `tmpfile()` 固定使用 `/tmp`，不读取 `TMPDIR`/`TMP`/`TEMP` 环境变量（与 glibc 行为不同）
- 这是**当前执行环境的限制**，不是 msgpack 库缺陷

> 两个 case 实际执行、未跳过、未删除、未降低断言、未修改测试语义。
> 未声称 CI Worker 一定会通过——仅在 `/tmp` 可写的环境上方能验证，本次环境未能验证。
> 未对 msgpack recipe 做任何环境 workaround patch。

## test_package 测试内容

`test_msgpack.c` 使用 7.0.1 真实公开 C API(经头文件确认)做序列化 round-trip:
- pack 数组 `[42, true, "msgpack"]`(msgpack_pack_array/int/true/str/str_body)
- unpack 回单个 array object,断言 `type==ARRAY`、`size==3`
- 逐元素验证: elem[0]==42(int)、elem[1]==true(bool)、elem[2]=="msgpack"(str)
- 验证 buffer 耗尽返回 `MSGPACK_UNPACK_CONTINUE`
- 验证 `msgpack_object_equal`(相等/不等)和 `msgpack_object_print_buffer`(返回正值)

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libmsgpack-c.a | 静态库 |
| include/msgpack.h, include/msgpack/*.h | C API 头文件 |
| lib/pkgconfig/msgpack-c.pc | pkg-config |
| lib/cmake/msgpack-c/msgpack-c-config.cmake | CMake config |

## 注意事项

- `package_info` 中 `cpp_info.libs` 用 `collect_libs(self)` 自动收集（静态模式下为 `msgpack-c`），与实际产物一致。
- CMake target 名 `msgpack-c::msgpack-c`、pkg-config name `msgpack-c`，与上游安装的 config/pc 一致。
