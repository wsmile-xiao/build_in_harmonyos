# DRAFT-E743-embedded-ringbuf-cpp-self-contained-header-first-include：header-only 模板库的「首个 include 即交付头」自包含探针——缺 `<stddef.h>` 在 OHOS/musl+libc++ 下当场 `unknown type name 'size_t'`

> Status: DRAFT（Reserved entry id **E743**，`tools/knowledge_id.py --claim --task embedded_ringbuf_cpp-1.3`）
> Source: embedded_ringbuf_cpp 1.3 HarmonyOS PC 适配（2026-09-25）
> Related: device-facts §二.17（header-only 全组命中路径解析缺陷、须人工补测）、
>          `DRAFT-jsoncons-1.9.0-test-count-and-baseline-noise`（四口径不混用与 N 归因）

## 背景

`embedded_ringbuf_cpp`（https://github.com/wizard97/Embedded_RingBuf_CPP ，tag 1.3 == 上游 HEAD
`5cd8410`）是纯头文件 C++ 模板环形缓冲：上游无构建系统、无测试框架、零依赖，
`package_type = "header-library"`。交付面只有 `RingBufCPP.h` + `RingBufHelpers.h`。

## 现象（错误面）

消费者按 README 记载的第一种用法写：

```cpp
#include <RingBufCPP.h>     // 作为本 TU 的第一个 include
```

在 OHOS（musl + libc++，clang 15）下**直接编译失败**：

```text
src/RingBufCPP.h:6:26: error: unknown type name 'size_t'
template <typename Type, size_t MaxElements>
                         ^
src/RingBufCPP.h:78:12: error: unknown type name 'size_t'   （共 4 处）
1 error generated.
```

只要该 TU **先** include 了 `<stdio.h>`/`<stddef.h>`/`<cstdint>` 之类头就一切正常，
所以这类包的"能编过"完全取决于消费者 include 顺序——是最典型的**顺序依赖假象**，
`conan create`/test_package 若被写成先 include 标准头就永远抓不到。

## 根因

`RingBufCPP.h` 自身只 `#include "RingBufHelpers.h"`，而非 Arduino 分支的
`RingBufHelpers.h` 只 `#include <stdint.h>`——**`<stdint.h>` 不定义 `size_t`**
（定义它的是 `<stddef.h>` 等），于是头文件**不自包含**：它依赖消费者在它之前
恰好 include 过某个提供 `size_t` 的头。这与平台无关，是上游头文件缺陷，
在 musl/libc++ 这种"不额外捎带"的实现上必然暴露。

## 方案

`patches/0001-…-stddef-self-contained.patch`（bugfix，2 行新增、无平台条件分支，R8 合规）：

```diff
--- a/RingBufCPP.h
+++ b/RingBufCPP.h
@@ -1,6 +1,8 @@
 #ifndef EM_RINGBUF_CPP_H
 #define EM_RINGBUF_CPP_H
 
+#include <stddef.h>  /* size_t: used below; header must be self-contained */
+
 #include "RingBufHelpers.h"
```

**探针定式（可复用于任何 header-only 包）**：把「第一个 include 就是交付头」写进
两处并让二者互为证据——

1. `build()` 里写一个最小 TU（`#include <RingBufCPP.h>` 打头 + 实例化 + add/pull），
   用 profile 的 `tools.build:compiler_executables` 编译并运行；
2. `test_package/test.cpp` 同样以交付头打头，并在 CMakeLists 里 `file(SHA256 …)`
   把**被测头**的 sha 打进日志（同时证明「测试靶向 == package() 交付的那一份」）。

补丁落地必须走 conan 实际执行路径自证（`patch_ng … apply(strip=0, root=…)` +
`filecmp` 与目标树逐字节一致），因为 conan `patch()` 默认 `strip=0`。

## 复现命令（设备可直接执行）

```sh
# 0) 任务 env
. "$HOME/tmp/embedded_ringbuf_cpp-1.3/env.sh"
SRC="$TASK_DIR/w0/src"          # 官方 tag 1.3 解包树（sha256 与 CCI conandata 一致）

# 1) 上游原样：首个 include 即交付头 → 必失败
printf '#include <RingBufCPP.h>\nint main(){return 0;}\n' > "$TASK_DIR/repro.cpp"
clang++ -std=c++17 -I "$SRC" "$TASK_DIR/repro.cpp" -o "$TASK_DIR/repro.out"
echo "rc=$?"                    # 实测 rc=1：unknown type name 'size_t' ×4

# 2) 打上补丁后同 TU → 通过
clang++ -std=c++17 -I "$TASK_DIR/patchwork/mod" "$TASK_DIR/repro.cpp" -o "$TASK_DIR/repro.out"
echo "rc=$?"                    # 实测 rc=0

# 3) 补丁对 conan 真实路径自证（strip=0 + 逐字节一致）
python3 -c "
import patch_ng, filecmp, os, sys
pkg = os.environ['PACKAGE_DIR']
ps = patch_ng.fromfile(pkg + '/patches/0001-ringbufcpp-stddef-self-contained.patch')
assert ps and ps.apply(strip=0, root=sys.argv[1])
assert filecmp.cmp(sys.argv[1] + '/RingBufCPP.h', sys.argv[2], shallow=False)
print('PATCH SELF-TEST PASS')" "$TASK_DIR/patchwork/verify2" "$TASK_DIR/patchwork/mod/RingBufCPP.h"
```

## 同批登记的计数口径（同一任务，供 N 归因复用）

上游无测试框架时 **N=0 也要按四口径清点并逐项归因**，不能只写"无测试"：

```sh
git clone --depth 1 https://github.com/wizard97/Embedded_RingBuf_CPP
git -C Embedded_RingBuf_CPP ls-tree -r --name-only HEAD   # 8 文件、无 tests/
grep -rInE "assert\(|TEST\(|CPPUNIT_TEST|BOOST_TEST" Embedded_RingBuf_CPP | wc -l   # 0
# 唯一含 test 的文件本身编译不过 → 归因证据：
clang++ -std=c++17 -I Embedded_RingBuf_CPP Embedded_RingBuf_CPP/examples_no_arduino/test.cpp
#   fatal error: 'RingBuf.h' file not found (rc=1)
```

→ 源码宏数 0 / 框架注册数 0 / assertion 数 0 ⇒ **N=0**；`test_package` 消费者用例
（12 用例 249 断言）计入「鸿蒙特有测试」行，**不进上游分母**（四口径不混用）。
