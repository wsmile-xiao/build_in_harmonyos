# DRAFT-expat-2.8.5-soname-stable-across-patch-bump：补丁级 bump 时 ABI soname 由上游版本变量重算，勿假设随版本号变

## 现象

把 expat 配方从 `2.8.4` bump 到上游 `R_2_8_5` 时，核对新源码 `expat/CMakeLists.txt` 发现：

```text
set(LIBCURRENT 13)   # sync
set(LIBREVISION 4)   # with      ← 2.8.4
set(LIBAGE 12)       # configure.ac!
math(EXPR LIBCURRENT_MINUS_AGE "${LIBCURRENT} - ${LIBAGE}")
```

2.8.5 只把 **`LIBREVISION` 4 → 5**，而决定 soname 的
`LIBCURRENT(13) - LIBAGE(12) = 1` **未变** → 产出的 soname 恒为 `libexpat.so.1`。
（`LIBREVISION` 是 libtool `-version-info` 的中间位，语义是「本版接口实现有改动但未增删接口」，
**不参与** soname 计算。）

## 根因与风险

版本号字符串变了（`2.8.4`→`2.8.5`）很容易诱导「bump 了就要动配方/动下游钉版」的直觉，但
**soname 与版本号是两个独立维度**：soname 只由上游的 ABI 版本变量派生。两种误判方向：

- **假阳性**：以为「版本涨了 soname 就变」，去改本配方 soname 相关处理、或把下游
  `requires` 抬版本重链 → 无谓的消费者重建，甚至破坏已上架二进制（本仓 expat 的 `libexpat.so.1`
  被 fontconfig/vips 等以 DT_NEEDED 引用，见 ML-0035 笔记的 DT_NEEDED 路径污染教训）。
- **假阴性（更危险）**：真正 bump 了 `LIBCURRENT` 或 `LIBAGE`（接口增删）时没察觉，
  二进制实际不兼容却仍当补丁级替换 → 运行期 `undefined symbol` / 崩溃。

在 HarmonyOS PC 侧这一维度尤其敏感：本仓 OHOS 配方刻意用
`-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` **不产版本号软链**（设备文件系统无法
`cmake_symlink_library`，issue #1912），只靠 toolchain 的 `-Wl,-soname,` 把稳定 soname 写进
DT_NEEDED。此时「soname 到底是什么值」直接决定消费者二进制的可重定位性，必须与上游一致。

## 可复用修复模式

对任何共享库做版本 bump（尤其补丁级）时，**从上游版本变量重算 soname 并与旧版对比**，
而不是从版本号字符串推断：

- CMake 工程（expat）：`readelf`/`grep` 出 `LIBCURRENT`/`LIBREVISION`/`LIBAGE`，
  soname 版本 = `LIBCURRENT - LIBAGE`；
- autotools 工程：`configure.ac` 的 `-version-info current:revision:age` →
  soname = `libNAME.so.$(current - age)`。

**只有 (current - age) 变化**才需要动配方 soname 处理或下游钉版；仅 `revision`/`LIBREVISION`
变化属二进制兼容补丁级替换，消费者无需重链。

## 验证证据

```bash
# 1) 上游版本变量（钉版 tag）
grep -nE "set\(LIB(CURRENT|REVISION|AGE)" <src>/expat/CMakeLists.txt
# 2) 产物真实 soname（OHOS 交叉产物亦可用 llvm-readelf）
readelf -d <pkg>/lib/libexpat.so | grep -i soname     # 期望 libexpat.so.1（2.8.4 与 2.8.5 一致）
```

本 PR 顺带核对：2.8.5 的 `CMakeLists.txt` 另外把新建的 `tests/hash_tests.c` 加入 `runtests`
目标（该 `START_TEST(test_hash_table)` 带 `if (g_chunkSize != 0) return;` 守卫，故只在
chunk-size 矩阵的 1 种配置下执行），更新后的上游实测 check 数以本 PR 的 CI runner 输出为准，
不照抄 2.8.4 的条数。
