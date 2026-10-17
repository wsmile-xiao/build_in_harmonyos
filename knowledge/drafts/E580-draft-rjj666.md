# E580-draft-rjj666 — LDC tarball 内 `test_runner.d` 空模板：批量 unittest「全过」是假象，必须逐模块官方 `%.test` 复刻

> **Contributor**: rjj666 | **Status**: DRAFT | **Updated**: 2026-09-17
> **Severity**: 🟡 medium | **Category**: testing / dlang / ldc / ohos / verification

## 症状：一个「好到不真实」的测试结果

liblphobos/1.42.0（D 语言标准库 Phobos）适配首轮实测时出现这样的结果：

* 把 Phobos 176 个模块（`std/` 166 + `etc/` 10）编译进一个批量 UT 库；
* 用 LDC 发行 tarball 内自带的 `test_runner` 执行；
* **176/176 全部通过，exit=0，无任何失败**。

⚠️ 反直觉信号：同源码的 ldc/1.42.0 适配当年基线只有 94.7%——
一个**新适配的平台**凭什么比基线还干净？抽查单模块日志后发现：
**日志零输出、耗时趋近 0**。全过是假象。

## ★ 判别特征：读 tarball 内 `test_runner.d` 的 main

```d
// runtime/druntime/src/test_runner.d —— 空模板特征
void main() { /* 无模块参数解析、无执行判定、直接返回 */ }
```

三个致命点：

1. **不解析模块名参数**——传 `std.array` 还是 `std.zlib` 还是乱码，行为一致；
2. **未把被测模块纳入执行判定**——unittest 是否运行、是否失败，与它无关；
3. **任意参数无条件 `exit=0`**——永远「成功」。

坐实方法（可选）：向批量方案注入一个**必败断言模块**，批量 runner 依然
exit=0——runner 根本没执行任何 unittest。

## 根因

上游 Phobos 的 unittest 体系是**逐模块**的：`runtime/phobos/Makefile`
（posix.mak 已废弃并转发）为每个模块提供 `std/<module>.test` 目标：

```make
# 官方形态（DMD 语法）
std/%.test : %/package.d
	$(DMD) $(DFLAGS) -main -unittest -version=StdUnittest -run $*
```

而 tarball 里的 `test_runner` 是给 CMake 构建 druntime 自测用的**占位入口**，
不是「给任意模块批量跑测试」的通用 runner。两套东西被混用的瞬间，
测试结论就整体失真了。

## 修复：逐模块官方 `%.test` 的 ldc2 等价复刻

```bash
ldc2 -conf= -I<本包>/include/d \
  -w -de -preview=dip1000 -preview=dtorfields -preview=fieldwise \
  -i -main -unittest -d-version=StdUnittest \
  -defaultlib=phobos2-ldc-shared,druntime-ldc-shared \
  -L-L<本包>/lib -L-lz -L-lm \
  -run std/array.d        # ← 逐模块执行，N 次
```

### 三个方言/参数要点

| # | 要点 | 说明 |
|---|------|------|
| 1 | `-version=` → `-d-version=` | DMD 方言 `-version=X` 在 ldc2 报 `does not allow a value`；LDC 语法为 `-d-version=X`（与上游 runtime CMake 的 `PHOBOS2_EXTRA_UNITTEST_FLAGS` 一致） |
| 2 | 官方基础 DFLAGS 不可省 | `-w -de -preview=dip1000 -preview=dtorfields -preview=fieldwise`；缺 dip1000 时 `std/algorithm` 等模块 @safe 借用检查直接**编译失败**——该失败与测试结果无关，勿误归因为库缺陷 |
| 3 | 判定口径 | 输出含 `N modules passed unittests` 且 exit=0 → PASS；无输出且 exit=0 → SKIP（无 unittest 块，**不计入分母**）；否则 FAIL |

### 效果对照（liblphobos/1.42.0 实测，唯一变量即执行方式）

| 方案 | 结果 | 定性 |
|---|---|---|
| 批量 UT 库 + tarball `test_runner` | 176/176 全过 | **假象，已废弃** |
| 逐模块官方 `%.test` 复刻 | 123 PASS / 9 FAIL / 44 SKIP / 0 TIMEOUT = **123/132 = 93.2%** | 真实口径 |

93.2% 与 ldc/1.42.0 同源码当年基线 94.7% 吻合（差异模块均可平台/环境归因），
交叉验证该口径有效。

## 适用范围

一切以 LDC/DMD 发行 tarball 为源、且上游 unittest 体系是逐模块 Makefile 目标
（`%.test` / `D_MODULES` 口径）的适配任务：

* `ldc`、`liblphobos`，以及未来任何 D 语言运行时/标准库包；
* 判别式：上游测试文档写的是 `make std/xxx.test` 而非「运行 test_runner」。

## 禁止的做法

**❌ 用 tarball 内 `test_runner` 批量执行 UT 库，并把全过结果作为上游测试通过率上报。**
这不是实现技巧的差异，而是虚假验证（欺骗面）：100% 的通过率从未被任何
unittest 支撑，真实失败全部被掩盖。

**❌ 见「编译失败」就归因为库缺陷。**
省略官方基础 DFLAGS（尤其 dip1000）导致的 @safe 编译失败，是执行口径错误，
不是被测库的问题。

## 诚实标注（limitations）

1. 「批量方案零输出」的判定基于逐模块日志抽查 + 必败注入坐实，未对 176 个
   模块逐一注入复核（成本与必要性不匹配）。
2. 本条只覆盖 LDC 生态；GDC/DMD 其他发行形态的 runner 行为未验证。
3. `SKIP` 不计分母的口径与 ldc/1.42.0 任务一致；若评审口径不同，通过率
   分母会变（176 全量口径为 70.5%），但结论排序不变。

## 相关

| 条目 | 关系 |
|------|------|
| `DRAFT-ohos-sigrtmin-not-deliverable-gc-suspend-deadlock` | 同属 ldc/liblphobos 任务线经验，主题不同：那条是 OHOS 信号投递缺陷（运行时死锁），本条是测试执行口径（假通过） |
| `E085` / `E493` / `E203` | 本条 md 引用的 D 生态适配前置知识（pthread_cancel shim、program_invocation_name）见这三条 |
