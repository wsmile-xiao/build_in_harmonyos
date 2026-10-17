# 测试报告 — libgmpxx 6.3.0（HarmonyOS PC 适配）

> **项目**: libgmpxx 6.3.0
> **测试日期**: 2026-09-19
> **测试环境**: HarmonyOS PC 设备（aarch64，OHOS 6.0，clang 15.0.4，libc++，conan 2.29.1）
> **测试类型**: 官方测试套件（GMP tarball tests/cxx）+ conan test_package 消费者测试

---

## 一、测试摘要

计数单位为测试程序：上游 = autotools `check_PROGRAMS` 框架注册项；鸿蒙特有 =
`test_package` 消费者程序。逐目录分解、取数命令与差额归因见 1.1。

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 TOTAL（= PASS+FAIL+SKIP+NOT_RUN） | 201 | — |
| 通过 (PASS) | 23 | 已运行项 23/23（100%） |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 未运行 (NOT_RUN) | 178 | — |

**已运行项通过率**: ✅ **23/23（100%）**（上游 22/22 + 鸿蒙特有 1/1）

### 1.1 上游 N（总数）与未运行项归因

- 上游 N = **200**：GMP 6.3.0 官方 tarball `tests/**` 各 `Makefile.am` 的
  `check_PROGRAMS` 注册项（取候选数法最大值；含外部审查「实测 N=190」的 `t-*` 子集，
  190 为本值子集、同单位，另 10 个具名项 = mpz 的 reuse/dive/dive_ui/convert/io/logic、
  mpq 的 io/reuse、mpn 的 logic、mpf 的 reuse）。逐目录：

  | 目录 | check_PROGRAMS | 其中 `t-*` | PASS | FAIL | SKIP | NOT_RUN |
  |------|---------------:|-----------:|-----:|-----:|-----:|--------:|
  | tests/（根） | 8 | 8 | 0 | 0 | 0 | 8 |
  | tests/cxx | 22 | 22 | 22 | 0 | 0 | 0 |
  | tests/misc | 3 | 3 | 0 | 0 | 0 | 3 |
  | tests/mpf | 28 | 27 | 0 | 0 | 0 | 28 |
  | tests/mpn | 53 | 52 | 0 | 0 | 0 | 53 |
  | tests/mpq | 15 | 13 | 0 | 0 | 0 | 15 |
  | tests/mpz | 64 | 58 | 0 | 0 | 0 | 64 |
  | tests/rand | 7 | 7 | 0 | 0 | 0 | 7 |
  | **合计** | **200** | **190** | **22** | **0** | **0** | **178** |

  自洽式：`TOTAL 200 = PASS 22 + FAIL 0 + SKIP 0 + NOT_RUN 178`。

- **测试减少原因（rule2/3）**：178 项 NOT_RUN **不是「测试被删减」**，而是**交付面不同**
  ——libgmpxx 是 GMP 源码树内 C++ 绑定的打包名，本包只 install
  `gmpxx.h`/`libgmpxx.a`/`libgmpxx.pc`，`package()` 裁剪 `libgmp.a`/`gmp.h`/`gmp.pc`；
  这 178 个程序的测试对象是 **libgmp C API**，由 `gmp/6.3.0` 包交付（本包 require 它）。
  同型先例：zfp（审方 N 口径入表 + 通过率按执行口径 + 显式换算）。
- **替代验证**：`tests/cxx` 22 个程序全部链接**同源** `libgmp.a`（同一构建树、
  `--enable-cxx` 同构配置）实跑通过，绑定层对 C 库的调用在链接期与运行期被完整覆盖。
- **范围边界**（不计入 N）：`tests/devel` 只有 `EXTRA_PROGRAMS`（不属 `make check`）；
  `mini-gmp/tests` 的 31 个 `t-*` 用独立手写 Makefile + `run-tests`（非
  `check_PROGRAMS` 注册、主 configure 不构建）。
- **N 取数命令**（设备可直接执行；`S` = GMP 官方 tarball 解包根，sha256
  `a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898`）：

  ```sh
  python3 -c "
  import os,re
  S='<gmp-6.3.0 解包根>'; tot=0; t=0
  for dp,_,fs in os.walk(os.path.join(S,'tests')):
      if 'devel' in dp.split(os.sep) or 'Makefile.am' not in fs: continue
      x=open(os.path.join(dp,'Makefile.am')).read().splitlines()
      for i,l in enumerate(x):
          if re.match(r'\s*check_PROGRAMS\s*=',l):
              b=l.split('=',1)[1]
              while b.rstrip().endswith('\\'): i+=1; b=b.rstrip()[:-1]+' '+x[i]
              p=[w for w in b.split() if '$' not in w]; tot+=len(p)
              t+=len([w for w in p if w.startswith('t-')]); break
  print('TOTAL=%d T_STAR=%d'%(tot,t))"
  ```

  实测输出：`TOTAL=200  T_STAR=190`。
- **通过率的两个口径**：上游总量口径 N=200（框架注册项，含本包不交付的 C API 套件）；
  本次执行口径 N′=22（`tests/cxx` 全部）。**上游通过率按执行口径记 22/22（100%）**，
  不写成 22/200——两者单位不同，换算关系即上表（200 − 178 NOT_RUN = 22 PASS）。

## 二、测试结论

### 2.1 总体评价

✅ **已运行项全部通过，未运行项如实记账（不写 PASS）**。上游 C++ 绑定官方测试 22 个
程序在设备实跑全部 PASS（直接静态链接 harness，方法与逐项记录见
reports/upstream-tests-cxx-log.md）；test_package 消费者测试随 conan create 实跑，5 项
断言全过（mpz 大整数平方、2^100 十进制位数、mpq 有理数相加、mpf 浮点乘法、operator<<
非内联插入器）。上游其余 178 个程序为 libgmp C API 套件，不在本包 install 面，按
NOT_RUN 记账（原因与替代验证见 1.1）。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无 | 无 | 🟢 |

### 2.3 可用功能清单

```
✅ mpz_class：任意精度整数（构造/算术/移位/比较/输出）
✅ mpq_class：任意精度有理数（构造/约分/加法/比较）
✅ mpf_class：任意精度浮点（构造/乘法/比较）
✅ operator<</operator>>：经 libgmpxx 非内联插入器/抽取器
✅ 静态链接：libgmpxx.a 与同源 gmp/6.3.0（libgmp.a）联用
```

## 三、执行环境与证据

- conan-verify 门禁结论（跳过项按「跳过」记账，不计 PASS）：
  - G0 / G1 / G2 / G3：✅ PASS（报告：reports/conan-verify-report.md）
  - G4：干净轮报告为 `✅ PASS` 并附 `⚠️ 无法找到程序包 ID`；20:57 轮实跑为
    `✅ lib/: 1 .a + 0 .so`、`✅ include/: 1 个头文件`
  - L2 / L4：⏭️ 跳过——本包为纯静态库，安装树内没有 `bin/` 可执行文件、没有 ELF 动态
    产物，两门禁结构性不适用；人工补测（产物清单核对、消费者程序真跑、L4 不适用判据）
    见 reports/conan-verify-supplement.md
  - L5：`reports/baseline.json` 已落盘（8 个条目），20:57 轮报
    `✅ PASS（产物与基线完全一致，8 个文件）`；两次同源构建的字节差异与基线口径见
    notes.md 的「L5 基线口径说明」
- W3 本地 CI 模拟通过：`reports/w3-local-ci.log` 汇总 `Total 1 / Success 1 / Failed 0`、
  exit 0（`.ci-result.json`）。**该日志里 `L1c: Upstream official tests (make check/ctest)
  executed in build phase` 是误报**：`ci/conan/build_and_test.sh` 用正则
  `make.*check|ctest|…` 扫构建日志，命中的是 GMP make 输出里的告示文本
  `If you have not already run "make check", then we strongly recommend that you do so`
  （同日志第 2673 行），而本配方 `build()` 并不执行 `make check`
  （`test_package/MANIFEST.yml` 已如实声明 `upstream_test_in_build: false`）。
  上游测试的真实证据是下面的 harness 实跑记录，不是这一行。
- 上游测试实跑记录：reports/upstream-tests-cxx-log.md
- 上游测试未随包内置 make check 的原因与方法披露：设备 HMDFS getcwd(2) 间歇故障使
  libtool 链接测试可执行文件确定性失败，改用同编译器/宏的直接静态链接 harness 实跑

## 四、已知限制

- libgmpxx.a 必须与同源 gmp/6.3.0 链接使用（Conan 依赖图已强制精确版本）
- 包为静态专用：shared 需求由 gmp/6.3.0.1 覆盖（conanfile configure 阶段显式拒绝并提示）
