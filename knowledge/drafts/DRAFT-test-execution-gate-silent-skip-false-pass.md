# `DRAFT-test-execution-gate-silent-skip-false-pass`：测试被静默跳过造成的假 PASS

> Contributor: Quas | Status: DRAFT | Created: 2026-09-30
> 与同 stem 的 .kv 配对。归纳自两条已实测入库的草稿：Box2D 2.4.1（doctest 未注册 CTest，PR #8849）与
> lapack-netlib/lapacke 0.3.30（设备原生构建下 CROSS=1 静默跳过）。本条把两者抽象为「测试执行门」这一类问题。

## 现象

测试“通过了”，但通过率是假的。两种已实测表现：

1. **空 CTest 套件退出码 0**（CMake/CTest）
   构建目录里明明有 `bin/unit_test`，`ctest` 却打印 `No tests were found!!!` 且 `$? == 0`；
   直接运行该二进制才看到真实数字（doctest：`test cases: 5 | 5 passed`，`assertions: 36 | 36 passed`）。
2. **平台守卫静默跳过**（autotools / GotoBLAS 谱系）
   `make test`、`ctest`、`make lapack-test` 几秒内“成功”退出，日志里没有任何 `run_test` / `----- PASS -----` 块。
   实测 lapacke 0.3.30：设备原生构建下 5,195,617 项 lapack-test 判定加 blat/ctest 全部未执行，却呈现为通过。

两类都不产生错误输出，唯一共同特征是：**退出码为 0，但没有任何用例真的跑过**。

## 根因

根在判定口径：把「命令退出码为 0」当成「测试通过」的证据。退出码是**执行门**的结果，不是测试结论的结果。

1. **注册缺失（CMake/CTest）**：上游用独立测试可执行文件，但 CMakeLists 从不调用
   `enable_testing()` / `add_test()`——官方 CI 就是直接运行那个二进制。配方改用 `cmake.test()` / `ctest` 驱动时，
   ctest 得到空套件：打印 `No tests were found!!!` 并返回成功。“无测试可跑”与“测试全部通过”在退出码上不可区分。
2. **平台探测误判 + 守卫跳过（autotools/GotoBLAS 谱系）**：
   - `CROSS=1` 只由 `c_check` 记录：`c_check:4` 用 `uname -s` 在设备上取到 `HarmonyOS`，
     而编译器探针（`c_check:40-67` 匹配 `*OS_LINUX*`）判定 `os=Linux`；`c_check:409` 判定两者不一致即 `cross=1`，
     `:492` 写入 `Makefile.conf`（`f_check` 不写 CROSS）。于是 **OHOS 设备上的原生构建被误判成交叉编译**。
   - 上游 `Makefile:410` 用 `ifneq ($(CROSS), 1)` 守卫 `lapack-test` 的 INSTALL 自检与 `lapack_testing.py` 执行段，
     `test/Makefile` 与 `ctest/Makefile` 的就地执行门同理。`CROSS=1` 时 make 正常退出、无任何告警。

## 修复步骤（可操作，顺序不可颠倒）

1. **先证伪：证明测试真的执行了**
   - CTest：`ctest -N` 或看 `Total Tests` 计数，为 0 即未执行
   - make 系：`make -n <test-target>` 确认执行行真的展开（例如是否出现 `lapack_testing.py`）
   - 把**真实执行的用例数 / 断言数**写进交付记录
2. **再按成因修执行门**
   - 注册缺失：配方在 `build()` 中直接执行上游测试二进制，`cross_building()` 守卫；多配置生成器补 `build_type`
     子目录；Windows 补 `.exe`。不要用 `cmake.test()` / `ctest` 充当证据。
   - 平台守卫：**仅当设备原生构建（构建机=目标机）**时，在测试步骤命令行覆盖判定变量（`make lapack-test CROSS=0`），
     并保留 `make -n` 前后对照（`CROSS=1` 计 0、`CROSS=0` 计 1）作为证据。
3. **最后统一交付口径**：上游用例数、实际执行数、通过数三个数字同时出现；禁止只报「构建成功 / 退出码 0」。

## 验证方式

- `ctest -N` 有非零用例数，或 `bin/unit_test` 直接运行输出真实 `test cases` 计数；
- `grep ^CROSS <build>/Makefile.conf` 与 `make -n ... CROSS=1 / CROSS=0` 的 `grep -c` 对照（0 → 1）说明执行段确实被恢复；
- 交付记录中出现「上游 N / 实执行 M / 通过 M」三个数字，且 M 的来源可重放。

## 适用范围

- 所有把退出码或粗扫输出当测试证据的配方、CI 包装器与交付记录；
- 构建系统侧：CMake/CTest（注册缺失）与 autotools/GotoBLAS 谱系 Makefile（平台守卫跳过）；
- 平台侧：OHOS 设备上「`uname -s` 非 Linux 而编译器探针判 `OS_LINUX`」的原生构建（真交叉构建不适用，见边界）。

## 反例与边界

- **反例一**：在上游没有 `add_test()` 注册时调用 `ctest` / `cmake.test()` 作为测试证据。
- **反例二**：用 `BUILD_UNIT_TESTS=OFF` / `BUILD_TESTING=OFF` / `--disable-tests` 关闭测试来「解决」执行问题。
  那是删除质量证据，适配后测试对比会出现负增长，无法证明库在 HarmonyOS 上行为正确。
- **反例三**：手改生成的 `Makefile.conf` 或 `c_check` 来「消除」`CROSS=1`——那会破坏上游平台探测语义，连带影响其他架构。
- **边界**：`CROSS=0` 覆盖只对「原生构建被误判为交叉」合法。真交叉构建（构建机 ≠ 目标机）中目标可执行本就不能在构建机运行，
  此时应改由设备侧回灌执行，并如实记录「目标执行未验证」。
- **相邻条目**：E363（旧式 Bash 测试框架的 setup 失败被报成上游套件通过）同属「假绿」家族，但根因是 setup 失败未向上传递；
  本条根因是执行门根本没打开（注册缺失 / 守卫跳过）。
