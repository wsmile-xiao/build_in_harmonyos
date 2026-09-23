# colpack 1.0.10 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am；GitHub archive 无预生成 configure，需 autoreconf 自举）
- 编译日期: 2026-09-08
- 编译器: clang/clang++（OHOS aarch64）
- 状态: built

## 编译步骤

1. 设备原生探索构建（源码树内）：
   - `autoreconf -fi` 自举（需 libtoolize，LT_INIT）
   - `./configure --prefix=$DEFAULT_PREFIX`
   - `make -j2 && make install DESTDIR=$TEST_PREFIX && make check`
2. Conan 配方构建（conanfile.py build()）：
   - `autoreconf --force --install`（automake/1.18 + libtool/2.5.4 以 tool_requires 提供）
   - 显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`（跳过 config.guess）
   - OHOS 下 E011/E114 修复（ac_tmp 重定向 + TMPDIR，与 abiword-plugin-docbook 同法）
   - 默认 `--enable-static --disable-shared`（R26 消费端零 .so 运行时依赖）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type`（uname -s = HarmonyOS） | E007：GNU config.guess 无 HarmonyOS 分支 | 探索阶段用 `scripts/patch-autotools-ohos.pl` 补丁；最终配方显式传 --build/--host 三元组（automake 1.18 config.sub 已接受 ohos-linux），不打源码补丁 |
| 2 | config.status 报 `can't create ./conf*/subs1.awk: Permission denied` | E011/E114：HMDFS mktemp 临时目录 umask 077+setgid 不可写 | 探索阶段 sed `umask 077→022`；配方内 OHOS 分支重定向 ac_tmp+TMPDIR（同 abiword-plugin-docbook 3.0.8） |
| 3 | TESTS 程序运行时读 `$(TOP_DIR)/Graphs/*.mtx` | 示例程序以编译期 TOP_DIR="." 定位数据文件 | 源码树内构建运行 make check（CWD=源码根，Graphs/ 可见），5/5 通过 |
| 4 | init-build 自动解压不完整（145 项 tar 只落 11 个文件） | init-build 解压环节对该 tarball 异常（HMDFS） | 手动 `tar xzf --strip-components=1` 重建 work/.orig 后正常 |

## 源码修改

无源码补丁（patches/ 为空）。平台差异全部在配方 build() 内以"构建期自举参数 + 生成脚本重定向"处理：
- config.guess 不识别鸿蒙 → 显式 --build/--host（E007），不改源码树；
- config.status 临时目录 HMDFS 权限 → E011/E114 ac_tmp/TMPDIR 重定向，作用于 autoreconf 生成物。

## 依赖版本

- 运行依赖：无
- 构建工具依赖（tool_requires，制品仓已发布）：automake/1.18、libtool/2.5.4
- 构建期系统工具：autoconf 2.73、clang/clang++（OHOS NDK）

## 验证结果

上游测试（设备原生，automake parallel-tests harness）：

```text
# TOTAL: 5  # PASS: 5  # SKIP: 0  # FAIL: 0  # XPASS: 0  # ERROR: 0
PASS: SampleDrivers/Basic/color_bipartite_graph_using_BipartiteGraphBicoloringInterface
PASS: SampleDrivers/Basic/color_bipartite_graph_using_BipartiteGraphPartialColoringInterface
PASS: SampleDrivers/Basic/color_graph_using_GraphColoringInterface
PASS: SampleDrivers/Basic/Generate_seed_matrix_for_Hessian
PASS: SampleDrivers/Basic/Generate_seed_matrix_for_Jacobian
```

说明：上游静态声明测试 = Makefile.am `TESTS = ${basic_examples_PROGRAMS}` 共 5 个；
另 14 个 Matrix_Compression_and_Recovery 示例程序（ADIC 1 + ADOL-C 12 + CSR 1）仅在
`--enable-examples` 下构建、未注册 TESTS，不计入测试口径。消费者测试 test_package
（test.cpp）1 个：内嵌上游 mtx-spear-head.mtx，真实调用 GraphColoringInterface 完成
SRC_FILE 解析 + DISTANCE_TWO 着色并断言颜色向量（见 test_package/MANIFEST.yml）。

## 注意事项

- 库产物名为 libColPack（大小写敏感），cpp_info.libs = ["ColPack"]。
- package() 移除 `examples/`（TESTS 示例二进制）与 libtool `.la`，交付物仅 lib/include。
- ColPack 为 LGPL-3.0-or-later（COPYING.LESSER），非 MIT。
- 本库无强制外部依赖（OpenMP 可选，本配方未启用）。
---

**编译结束**: 2026-09-09 00:12
**最终状态**: built
