# metalang99 1.13.5 适配笔记

## 编译环境
- 构建系统: cmake (header-only INTERFACE target)
- 编译日期: 2026-08-24
- 编译器: clang/clang++ (OHOS aarch64)
- 状态: built

## 软件性质

metalang99 是 hirrolot 开发的 C99 预处理器元编程库，header-only、零依赖。
- 官方仓库: https://github.com/hirrolot/metalang99
- tag: v1.13.5（2025-03-17 发布）
- license: MIT
- 语言标准: C99（断言宏在 C11 下走 `_Static_assert`，C99 下走数组技巧）
- 产物: 仅头文件（CMake INTERFACE target），无 .a/.so

## 源码校验

```
URL:    https://github.com/hirrolot/metalang99/archive/refs/tags/v1.13.5.tar.gz
SHA256: f3d1607d76b4b081d3295661c4c2b8d5fde4d5018b1aa409c84fb3a6660ffb90
```

SHA256 由本地 `curl ... | sha256sum` 实测获得，与 GitHub release tag v1.13.5
对应源码包一致。

## 上游测试调查

上游测试机制（实测自 v1.13.5 源码）：

1. `tests/CMakeLists.txt` 注册 **17 个 `add_executable` target**（无
   `add_test`/`enable_testing`，即未注册到 ctest）：
   `metalang99 / assert / choice / either / gen / stmt / lang / list /
   bool / maybe / nat / ident / tuple / util / variadics / seq / rec`
2. 每个 `tests/*.c` 的测试断言均为 `ML99_ASSERT_*` 宏，展开为
   `_Static_assert`（C11）或 C99 数组技巧。**编译成功 = 测试通过**，
   这正是上游 `scripts/test.sh` 的契约（cmake --build . 后仅显式运行
   `./gen` 与 `./stmt`，其余靠编译隐式验证）。
3. 上游 CI（`.github/workflows/c-cpp.yml`）调用 `./scripts/test-all.sh`
   = `test.sh` + `test-examples.sh`，在 ubuntu/macos/windows 三平台跑 gcc/
   clang/msvc，外加 tcc 与 C++ stmt 兼容性检查。

| 项目 | 数量 |
|------|------|
| 上游测试源文件数 | 17（tests/*.c 16 + tests/eval/rec.c 1） |
| 注册测试 target 数 | 17（add_executable） |
| 注册到 ctest 的 case 数 | 0（无 add_test） |
| 上游实际执行的可执行数 | 2（./gen + ./stmt，仅 Linux）+ 其余靠编译 |

## 上游正式测试 OHOS 实验证（2026-08-24）

使用官方 v1.13.5 原始上游 tests（未修改），用 OHOS clang
（aarch64-unknown-linux-ohos，sysroot=/usr/local/sysroot）实际构建：

| 指标 | 值 |
|------|-----|
| upstream test source files | 17 |
| upstream test targets | 17 |
| compiled | 17/17 |
| compile pass | 17 |
| compile fail | 0 |

构建命令（工作目录 `.tmp-ml99-verify/`，已清理）：
```
cmake <upstream-tests> -DCMAKE_C_COMPILER=.../clang \
      -DCMAKE_C_FLAGS="--target=aarch64-unknown-linux-ohos --sysroot=.../sysroot" \
      -DCMAKE_SYSTEM_NAME=HarmonyOS -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
      -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
cmake --build . -j4   → exit 0, 17/17 Built target, 0 error
```

所有 17 个 target（metalang99/assert/choice/either/gen/stmt/lang/
list/bool/maybe/nat/ident/tuple/util/variadics/seq/rec）均编译通过，
即全部 `_Static_assert` 断言成立。

### 运行时测试（gen / stmt）

上游 `scripts/test.sh` 在 Linux 额外运行 `./gen` 与 `./stmt`。本机
OHOS 构建产物实测可运行（OHOS 设备与 host 同为 aarch64 + musl libc）：

| 指标 | 值 |
|------|-----|
| runtime tests | 2 |
| executed | 2 |
| pass | 2 |
| fail | 0 |

```
./gen   → exit 0
./stmt  → exit 0
```

## 适配步骤

header-only 库，无编译产物。Conan recipe 只做源码下载 + 头文件拷贝：

```bash
conan create archives/m/metalang99/1.13.5 \
  -pr:h=ohos-aarch64-local \
  -pr:b=ohos-aarch64-local
```

## test_package 设计

`test_package/test_metalang99.c` 跨 **9 个功能点** 调用 metalang99 公开宏
API，断言均为 `ML99_ASSERT*`（_Static_assert）。功能点：

1. ML99_VERSION_COMPATIBLE / ML99_VERSION_EQ（版本语义）
2. ML99_inc / ML99_dec / ML99_add / ML99_sub（Peano 自然数）
3. ML99_natEq / ML99_natMatch（自然数相等/模式匹配）
4. ML99_true/false/not/and/or/if（布尔代数）
5. ML99_tuple/tupleCount/tupleGet/tupleTail（元组）
6. ML99_isLeft/isRight/eitherEq/unwrapLeft（either）
7. ML99_isJust/isNothing/maybeEq/unwrapJust（maybe）
8. ML99_list/cons/nil/listEq/isNil（列表）
9. ML99_id/const/compose（util）

ML99_ASSERT* 调用总数：57（逐条枚举真实值；grep -cE "ML99_ASSERT"
原始计数 58 含 1 行文件头注释，实际断言调用 57）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conanfile copy 需保留 include/metalang99 子目录结构 | metalang99.h 是 umbrella header，include 下一层 metalang99/ 子目录 | `copy(self, "*", src=include, dst=include, keep_path=True)` |
| 2 | OHOS SDK lld 运行时依赖 libxml2.so.16 | CI #17494 | test_package conanfile 复用 lld runtime path 注入模式 |

## 源码修改

无补丁，源码未修改（零 patch）。

## 依赖版本

无外部依赖（header-only 库）。

## 验证结果

```
conan create ... -pr:h=ohos-aarch64-local -pr:b=ohos-aarch64-local
→ metalang99/1.13.5: Package installed ... (header-only)
→ test_metalang99.c 编译通过（_Static_assert 全部成立）
→ test_metalang99 运行 exit 0
```

## 注意事项

- metalang99 是 header-only 库（CMake INTERFACE target），无 .a/.so 产物
- L2（--version 烟雾测试）不适用：header-only 库无 CLI 可执行，CI 会 skip
- L4（NX/PIE/RELRO）不适用：无二进制产物，CI 会 skip
- L5（产物基线）不适用：无二进制产物，CI 会 skip
- conandata.yml URL 保持 GitHub 原始 URL（R39），CI 镜像 fallback 自动处理

---

**编译结束**: 2026-08-24
**最终状态**: built
