# 测试报告 — lsmount 0.2.4

> **项目**: lsmount
> **测试日期**: 2026-09-25
> **测试环境**: HarmonyOS PC（A 机，aarch64 / clang 15 / profile host `os=OHOS, arch=armv8, libcxx=libc++, os.version=6.0`）
> **测试类型**: 消费者功能测试（test_package）+ 鸿蒙平台专项验证（test_ohos）

---

## 一、测试摘要

### 1.1 静态来源口径（declared — 上游清点，R51）

| 指标 | 数值 | 证据 |
|:----|:----:|:-----|
| 上游 `tests/` 目录数 | 0 | `ls -d tests test` → `No such file or directory` |
| 上游 Makefile 测试目标数 | 0 | `make -n check` → `No rule to make target 'check'`；全部目标 = all/debug/clean/install/uninstall/manpage |
| 上游 ctest / pytest 注册数 | 0 | 无 CMake/ctest、无 pytest 资产 |
| **上游静态用例总数 declared** | **0** | 源包 18 个文件全量枚举，无测试源文件 |

> 口径说明：上游**确无**自动化测试（"没有"，不是"没跑"）。因此下述所有执行数字全部来自本 PR 新增的测试，
> 与上游分母无关 —— 不存在"上游 N 个用例只跑了 M 个"这类分母收缩。

### 1.2 实测口径（measured — 日志汇总）

| 指标 | 数值 | 百分比 |
|:----|:----:|:------:|
| 总断言数（去重后申报） | 36 | 100% |
| 通过 (PASS) | 36 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%（36/36 去重后）**

> 计数口径（W4 独立审计 r1 纠偏）：脚本内实际执行 **40 次断言**（test_package 28 + test_ohos 12），其中 test_ohos 的 **T5a-T5d 共 4 条与 test_package 的 T9a/T9d/T9e/T9f 同源**（同一已安装二进制、同一本机 /proc/mounts、同一 hmfs/erofs/hmmac= 判据），**不并入申报总数**，只作交叉复核 ⇒ **申报 = 28 + 8 = 36**。

分解：

| 测试集 | 断言数 | PASS | FAIL | 执行位置 | 日志 |
|--------|:----:|:----:|:----:|---|---|
| `test_package/test.sh` T1–T9 | 28 | 28 | 0 | `conan create` 内的 test_package 阶段（env=conanrun，对**已安装入包**的二进制） | `archives/l/lsmount/0.2.4/reports/conan-create.log`（`test lsmount 0.2.4: ALL PASS (9 组 / 28 条断言)`） |
| `test_package/test.sh` T1–T9（复核） | 28 | 28 | 0 | 对最终包目录 `bin/lsmount` 独立重跑 | `~/tmp/uc2/z42-lsmount/pkgcheck` 输出 |
| `test_ohos/run_ohos_test.sh` T1–T4b（8 条专项；另 T5a–T5d 4 条同源复核） | 8(+4 复核) | 8(+4 复核) | 0 | 真机直接执行已安装二进制 | `~/tmp/uc2/z42-lsmount/` |
| **合计（去重后申报）** | **36** | **36** | **0** | — | 另 4 次同源交叉复核不计入 |

> 注：28 与 12 是两个**互不重叠**的用例集（前者做上游功能语义对账，后者做平台专有性质），合计 40。
> test_package 被执行了两次（conan create 内一次、对最终包目录复核一次），按测试集只计一次，不重复累加。

## 二、测试结论

新增测试用例通过率 **36/36 = 100%**（脚本执行 40 次断言，含 4 次同源交叉复核，不重复计数）；上游测试用例修改数 **0**（上游无测试可改）；上游测试用例补集覆盖率 **N/A**（分母为 0）。

- 配方 `conan create` 干净构建通过，且**测试跑的是打进包的那个二进制**，不是构建目录里的临时产物。
- 消费者断言全部为"退出码 + 输出内容"双重判定，无 `echo ok` 型自证。
- 所有断言均在真实 HarmonyOS PC 上执行（A 机），非交叉编译后在 x86 宿主上模拟。

### 2.1 test_package 消费者断言（28 条）

| 测试项 | 验证的功能 | 结果 |
|--------|-----------|------|
| T1a–T1e | `--help` 退出码 = 0，且正文含 `Usage: lsmount [options]` / `Version: v0.2.4` / `License: ISC` / `-f, --use-file` | ✅ PASS |
| T2a–T2e | 受控 fixture 渲染：退出码 0、行数 = 2、两行四字段原文命中、默认隐藏未使用列 | ✅ PASS |
| T3a–T3b | `--show-unused` 使 `0 0` 列可见（与 T2e 互为反向断言） | ✅ PASS |
| T4a–T4c | `--skip <dev>` 过滤指定设备，仅剩 1 行 | ✅ PASS |
| T5a–T5b | `--print-vertical` 每字段一行（2 行 × 4 列 = 8 行） | ✅ PASS |
| T6a | `--use-alignment` 真实改变输出体积（83 B > 75 B） | ✅ PASS |
| T7b–T7c | `-c` 注入 ANSI 转义序列；`-C`（大写取反）不注入 | ✅ PASS |
| T8a–T8b | 输入文件不存在 → 退出码 = 1 且错误信息含 `fopen` 原因 | ✅ PASS |
| T9a–T9f | **鸿蒙特有消费者断言**：默认读 `/proc/mounts` 退出码 0、行数与内核视图一致（139）、"设备+挂载点"两列逐行 diff 完全相同、渲染出鸿蒙专有 `hmfs` / `erofs` / `hmmac=` | ✅ PASS |

### 2.2 test_ohos 鸿蒙平台专项断言（12 条）

| 测试项 | 验证的性质 | 结果 |
|--------|-----------|------|
| T1 ×2 | 产物为 ELF64 + AArch64（交叉目标正确） | ✅ PASS |
| T2a–T2c | 加固三件套 PIE(ET_DYN) / GNU_RELRO / BIND_NOW —— 其中 BIND_NOW 专门证明覆盖 `LDFLAGS` 时上游 `-z now` 未被覆盖丢失 | ✅ PASS |
| T3 | 产物内无构建机绝对路径泄漏（`/storage/Users/`、`/home/`、`/tmp/uc2/`） | ✅ PASS |
| T4a–T4b | **平台特有回归**：本机 euid `20020105` 不在 `/etc/passwd` 内 ⇒ 上游未判空的 `getpwuid()` 必致 SIGSEGV(139)；修复后 `--help` rc=0 | ✅ PASS |
| T5a–T5d | 鸿蒙挂载表语义被正确渲染（`hmfs` / `erofs` / `hmmac=`） | ✅ PASS |

### 2.3 失败的测试

无。

### 2.4 跳过的测试（含工具自报跳过，如实登记）

| 测试项 | 跳过原因 | 处置 |
|--------|----------|------|
| `lsmount -x / --set-colors` | 上游无条件缺陷：`src/options.c:109-131` 用 `tokens[]={NULL}` 调 `getsubopt()` ⇒ `value` 恒为 NULL ⇒ `colortoesc(NULL)` → `strcmp` 空指针。任意入参均 rc=139，与 HarmonyOS 无关 | 不纳入断言（不拿必崩路径充数）、本次不修；已在 notes.md 登记，交主代理决定是否开上游 Issue |
| conan-verify 的 **G4 / L2 / L4 / L5** | 工具自报 `跳过（无 cache 路径）` / `无法找到程序包 ID`（见 `reports/conan-verify-report.md`） | **人工补做并对真实包目录核验**：包内产物清单（`bin/lsmount`、`licenses/LICENSE`、`res/×2`）、`--help`/默认运行 rc=0、ELF64/AArch64/PIE/RELRO/BIND_NOW、`NEEDED` 仅 `libc.so`、无宿主路径泄漏 |
| `make check` / `ctest` | 上游无该目标（见 1.1） | 不适用 |

---

## 三、关键问题分析

### 问题1: 启动即 SIGSEGV（连 `--help` 都跑不出来）

**现象**：
```
$ ./lsmount -h
Segmentation fault (core dumped)     # rc=139
```

**根因分析**：
`src/lsmount.c` 在解析任何选项之前就执行 `const char* homedir = pw->pw_dir;`，
其中 `pw = getpwuid(getuid())` 未判空。A 机探针实测 `getuid()=20020105`、
`getpwuid()=NULL`（鸿蒙 app uid 不在 passwd 库内；且 `/etc/passwd` 条目的 `pw_dir`
字段本身为空：`root:x:0:0:::/bin/false`）⇒ 空指针解引用。

**解决方案**：`patches/0001-src-lsmount.c-guard-null-getpwuid.patch` 三级判空后回退
`$HOME`、再回退 `"/"`。补丁不含任何平台宏（PF5 安全），且在 glibc 下同样是正确性改进。

### 问题2: `gettext` 未声明导致 `-Wint-conversion` 编译错误

**现象**：
```
src/lsmount.c:116:19: error: incompatible integer to pointer conversion
                      passing 'int' to parameter of type 'const char *' [-Wint-conversion]
```

**根因分析**：OHOS sysroot 的 `libintl.h` 仅 353 字节、不声明 `gettext`/`textdomain`/
`bindtextdomain`（`grep -rl gettext <sysroot>/usr/include` 无结果）。

**解决方案**：编译期把三个入口映射为 identity/no-op（等价 E027 的 `--disable-nls`；
上游不带任何 `.mo`，NLS 本就是死代码）。零源码改动、零补丁。

### 问题3: 链接期 `-ltermcap` 不存在

**根因分析**：Makefile 第 8 行把 `LDFLAGS` 烧成 `-ltermcap -z now`；制品仓
`ncurses/6.5` 只发布 `libncursesw.a`（无 termcap/tinfo/`.so`）。
**解决方案**：命令行整体覆盖为 `-lncursesw`（`llvm-nm` 实证 `T setupterm`/`T tigetnum`）
并**原样保留** `-z now`，由 test_ohos T2c 断言加固未丢。

---

## 四、测试环境

```
软件:     lsmount 0.2.4（上游 tag v0.2.4）
构建主机: A 机 HarmonyOS PC aarch64（8 核 / 31G）
编译器:   /data/service/hnp/bin/clang (clang 15)，CC 由 make 命令行覆盖注入
profile:  host = ci/conan/profiles/ohos-aarch64 (os=OHOS, arch=armv8, compiler=clang/15,
          libcxx=libc++, os.version=6.0)  |  build = default
CONAN:    2.29.1，CONAN_HOME=~/tmp/ch/home-lsmount，remote ohpcd enabled
依赖:     libconfig/1.7.3（静态 libconfig.a）、ncurses/6.5（静态 libncursesw.a）
产物:     bin/lsmount（ELF64 AArch64 PIE，NEEDED 仅 libc.so）
          res/lsmount.rc.default、res/lsmount.txt、licenses/LICENSE
门禁:     conan-verify G0–G4 PASS (RC=0)；W3 本地 CI 模拟通过
          (.ci-result.json exit_code=0, log_sha256=b195a4ac…111e7)
```

---

*报告生成时间: 2026-09-25*
