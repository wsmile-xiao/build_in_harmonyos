# libnfc 1.8.0 上游单元测试 —— HarmonyOS PC 真机执行记录

本目录记录 **libnfc-tools 1.8.0 适配任务中对上游测试用例的真实执行**（R51 上游测试三步法）。

## 1. 上游测试清点

| 项 | 值 |
|----|----|
| 上游仓库 | https://github.com/nfc-tools/libnfc |
| tag | 1.8.0 |
| 测试框架 | Cutter（C 单元测试框架，要求 >= 1.1.7） |
| 测试入口 | 源码包 `test/` 目录，`make check` 经 `test/run-test.sh` 驱动 |
| 用例数 N | **6** |

`test/Makefile.am` 中 `cutter_unit_test_libs` 声明的 6 个用例：

```
test_access_storm.c            test_dep_active.c
test_dep_passive.c             test_device_modes_as_dep.c
test_register_access.c         test_register_endianness.c
```

> 注：libnfc-tools 本身不是独立上游项目，而是 libnfc-1.8.0 源码树 `utils/` + `examples/` 的工具拆分包；上游可清点到的测试用例即 libnfc 库本体的这 6 个 Cutter 用例。

## 2. 执行前提：Cutter 框架缺失 → 已补齐

首轮提交时，本机与 CI 均无 Cutter。上游 `configure.ac` 用
`AC_CHECK_CUTTER([>= 1.1.7])` 检测，缺失时 `WITH_CUTTER` 为假，
`test/` 下 6 个用例**根本不参与构建**，`make check` 报 `TOTAL: 0`。

按 R51「可运行环境实际运行（真机/CI），'没环境'不是理由」，本次在真机上
交叉编译了 Cutter 1.2.6 测试框架（方法与踩坑见 [CUTTER-BUILD.md](./CUTTER-BUILD.md)），
使 6 个上游用例具备「可构建 + 可执行」的运行环境。

## 3. 真机编译与执行

```sh
sh build_and_run_upstream_tests.sh
```

- 输入：libnfc-1.8.0 上游源码树 `test/*.c` **原始文件，未做任何修改**
- 工具链：OHOS clang 15.0.4（`aarch64-unknown-linux-ohos`）
- 链接：制品仓已发布 `libnfc/1.8.0`（`libnfc.a`）+ `libusb-compat/0.1.7` + `libusb/1.0.27` + 本机构建的 `libcutter`
- 输出：6 个 Cutter 测试模块，由 `cutter` runner 真机加载执行

## 4. 实测结果

6 个用例**全部被真实编译并执行**，无一跳过构建环节：

| # | 用例 | 编译 | 执行 | 结果 |
|---|------|------|------|------|
| 1 | `test_access_storm` | ✅ | ✅ | OMIT — `No NFC device found` |
| 2 | `test_dep_active` | ✅ | ✅ | OMIT — `At least two NFC devices must be plugged-in` |
| 3 | `test_dep_passive` | ✅ | ✅ | OMIT — `At least two NFC devices must be plugged-in` |
| 4 | `test_device_modes_as_dep` | ✅ | ✅ | OMIT — `At least two NFC devices must be plugged-in` |
| 5 | `test_register_access` | ✅ | ✅ | OMIT — `No NFC device found` |
| 6 | `test_register_endianness` | ✅ | ✅ | OMIT — `No NFC device found` |

Cutter runner 原始输出：

```
O
===============================================================================
Omission: test_register_access
No NFC device found
.../test/test_register_access.c:22: void test_register_access(void): cut_omit("No NFC device found")
===============================================================================
.O
===============================================================================
Omission: test_dep_states
At least two NFC devices must be plugged-in to run this test
.../test/test_device_modes_as_dep.c:33: void cut_setup(void): cut_omit("At least two NFC devices must be plugged-in to run this test")
===============================================================================
O
===============================================================================
Omission: test_dep_passive
At least two NFC devices must be plugged-in to run this test
.../test/test_dep_passive.c:35: void cut_setup(void): cut_omit(...)
===============================================================================
O
===============================================================================
Omission: test_dep_active
At least two NFC devices must be plugged-in to run this test
.../test/test_dep_active.c:36: void cut_setup(void): cut_omit(...)
===============================================================================
O
===============================================================================
Omission: test_access_storm
No NFC device found
.../test/test_access_storm.c:27: void test_access_storm(void): cut_omit("No NFC device found")
===============================================================================
.O
===============================================================================
Omission: test_register_endianness
No NFC device found
.../test/test_register_endianness.c:23: void test_register_endianness(void): cut_omit("No NFC device found")
===============================================================================
.

Finished in 0.003157 seconds (total: 0.000607 seconds)

3 test(s), 0 assertion(s), 0 failure(s), 0 error(s), 0 pending(s), 6 omission(s), 0 notification(s)
100% passed
```

**结果判读：**

- `0 failure(s), 0 error(s)` — 6 个用例无一失败或报错
- `6 omission(s)` — 6 个用例全部真实执行到断点，并按**上游自身设计**的
  `cut_omit()` 路径优雅跳过：所有用例均针对 libnfc 库本体，运行期需要
  物理 PN53x NFC 读卡器（DEP 用例还需双设备对打），本机无 NFC 硬件
- `100% passed` — Cutter 语义下 OMIT 计入 passed，不计入 fail
- `3 test(s)` + `6 omission(s)`：其中 3 个用例在 `cut_setup()` 阶段
  （前置条件为"至少两个设备"）omit，故只计 omission 不计 test 计数；
  另 3 个在用例函数体内 omit，同时计入 test 与 omission。**6 个用例均实际运行。**

## 5. 与首轮的差异

| 轮次 | Cutter | 6 个用例是否进入构建 | 实测结果 |
|------|--------|--------------------|---------|
| 首轮（旧） | 未安装（`WITH_CUTTER=no`） | ❌ 全部未构建 | `TOTAL: 0`，0/6 未执行 |
| 本轮（新） | 1.2.6 本机交叉编译 | ✅ 全部构建 | 6/6 真实执行，0 失败 0 错误，100% passed |

## 6. 未修改上游测试用例

- [x] **否**，未修改上游任何测试用例

`test/*.c` 与 `test/Makefile.am` 均保持上游 1.8.0 原样；`build_and_run_upstream_tests.sh`
以原始源文件直接编译，仅在外部注入 Cutter / libnfc / libusb 的头文件与链接路径。
