# marst 2.8 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 自带 configure + ltmain.sh，无需 autoreconf）
- 编译日期: 2026-09-12
- 编译器: clang（OHOS aarch64 交叉工具链）
- 状态: built

## 编译步骤

1. `conan create`（AutotoolsToolchain 生成 OHOS aarch64 toolchain；configure 无特殊参数）
2. 产物：`bin/marst`（Algol→C 翻译器）、`bin/macvt`（listing 转换器）、`include/algol.h`、`lib/libalgol.a`（运行库）
3. package() 删除 `lib/*.la`（libtool 绝对路径问题，检查清单 #6）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` 风险（同批 jwhois 实测命中） | 2007 年版 config.guess/config.sub 在 OHOS 上无法猜测且不认识新 triplet | generate() 在 `os == "OHOS"` 时追加 `--build=aarch64-unknown-linux-gnu`（仓库 adms 配方同款先例），预防性规避 |
| 2 | `config.status: line 795: ./confYsmdBx/subs1.awk: Permission denied` → `could not setup config files machinery`（实测命中） | 知识库 E011：HMDFS UID 映射导致 configure 内 `umask 077` 创建的临时文件对 sed/awk 不可读写 | 按知识库 E011 受控方案，build() 中对 configure 执行 `umask 077 → umask 022` 替换（gsl/2.8 配方同款实现） |

## 上游测试清点（R51 第一步）

- Makefile.am 注册 **1 个真实功能 check 目标**：macvt 转换 euler.txt → marst 翻译 gps.alg/euler.alg → 宿主 CC 编译 gps.c 链接 `.libs/libalgol.a` + `-lm` → 运行验证矩阵乘积 C = A*B 为单位阵
- `tests/` 下 130 个 `*.alg` 是手工测试语料（语言特性样例程序），**无自动化 harness**，不计入自动化注册数
- **上游静态测试数 N_static = 1**（check 目标，真实注册）

## 消费者测试（test_package，N_consumer = 1）

`test.sh` 对 marst 做端到端消费者测试（4 断言，复刻上游 check 方法论）：

1. `marst --version` 输出含 `Version 2.8`
2. `marst --help` 输出含 `Usage:`
3. 内嵌 hello.alg → `marst -t -w hello.alg -o hello.c`（与上游 `.alg.c` 后缀规则同参）→ 断言生成 C 代码
4. 用包内 `algol.h` + `libalgol.a` + `-lm` 编译 hello.c 并运行 → 断言输出 `Hello, world!`

（实际运行结果见验证结果节与 PR 正文；run 结果回填）

## 四维测试账本

| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态声明 N_static | 1 | Makefile.am check 目标 |
| 构建系统注册 N_registered | 1 | 同上（make check） |
| 实际执行 N_executed | （run 后回填） | test_package 内复刻执行 |
| 未执行分类 | 0 | — |
| 消费者测试 N_consumer | 1（4 断言） | test_package/test.sh |

## 源码修改

无补丁（patches: {}）。

## 依赖版本

无外部依赖（运行时数学函数仅 `-lm`，OHOS musl libc 提供）。

## 路径 B 判断

- 本包为 release tarball 直配置的 autotools C 项目，构建期未触发新的平台特定错误签名。
- 端到端"翻译器→编译→运行"消费者测试方法论与 flex（CLI+lib 同包）模式均为仓库既有先例，非新增跨仓库知识。
- 结论：**纯路径 A，不申报路径 B**。查重依据：无新 E 条目草稿生成，无新错误签名。

### 对话 #1（2026-09-13，GLM-19）

状态: built

- W0/W0b：预检通过（零外部依赖）；上游无历史归档与历史 notes
- 语言预检：c，autotools，通过
- 配方：conan-init 模板首稿 + 两项修复（--build triplet；E011 umask 022，后由 refresh-patch 固化为 patches/0001-configure.patch）
- conan-verify：rc=0（G0-G4/L2/L4/L5 全过），消费者测试 4/4 断言 PASS（端到端翻译-编译-运行）
- 上游 make check：构建树内真机执行 rc=0，gps 矩阵乘积输出单位阵（N_executed=1/1）
- finish：W3 本地 CI 模拟通过；状态 built
- configure 参数与耗时：`--build=aarch64-unknown-linux-gnu`，make -j1 单机数分钟
- 编译结果：bin/marst、bin/macvt、include/algol.h、lib/libalgol.a 正常产出

## 验证结果

- conan-verify（round2，2026-09-13 01:15，rc=0）：G0/G1/G2（conan create 干净构建）/G3/G4/L2/L4/L5 全部通过
- 消费者测试 test_package/test.sh 真机执行输出（见 reports/conan-create.log）：
  - `[test] marst --version` → `OK: --version reports Version 2.8`
  - `[test] marst --help` → `OK: --help prints usage`
  - 翻译 hello.alg → `OK: translator produced C code (74 lines)`
  - 编译运行 → `Hello, world!` / `OK: translated program ran and printed Hello, world!`
  - `ALL CONSUMER TESTS PASSED`
- 上游 make check 证据（N_executed=1 依据，round4，2026-09-13 02:16，构建树内真机执行）：
  - 前置修复：随包 configure 同样含 `umask 077`（E011），按同方案 sed 替换 022 后 configure 通过；`CC=clang ./configure --build=aarch64-unknown-linux-gnu`（无 cc 命令 + config.guess 不识别 OHOS）
  - `./configure` rc=0、`make -j1` rc=0、`make check` rc=0
  - check 输出：`Matrix C = A * B:` 打印 5×5 单位阵 → `If matrix C = A * B is unity, the check is OK`（上游 gps 用例真机通过）
  - 完整日志：`~/builds/marst-2.8.work/glm19-{configure,make,make-check}.log`
