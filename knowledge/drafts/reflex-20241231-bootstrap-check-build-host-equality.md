# 自举 `make check` 的静默假通过：`@no_cross@` 在交叉构建下把自检规则置空

> Draft: `DRAFT-REFLEX-20241231-BOOTSTRAP-CHECK-BUILD-HOST-EQUALITY`
> Stem: `reflex-20241231-bootstrap-check-build-host-equality` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-REFLEX-20241231-BOOTSTRAP-CHECK-BUILD-HOST-EQUALITY
- **严重度**: 3
- **类别**: autotools|cross-compilation|test-harness
- **触发工具**: configure|make|conan
- **阶段**: configure|testing

## 错误特征

两个方向都会踩：

**（a）裸 `./configure` 直接失败** —— 包里 vintage `config.guess` 不认识 HongMeng 内核：

```
checking build system type... ./config.guess: unable to guess system type
...
uname -s = HarmonyOS
uname -r = HongMeng Kernel 1.12.0
configure: error: cannot guess build type; you must specify one
```

**（b）更危险的一种：`make check` 退出码 0，但一条断言都没执行**。交叉构建下
`cross_compiling=yes` ⇒ `@no_cross@` 替换为空 ⇒ 依赖"执行刚构建的产物"的自检规则被摘掉：

```make
check: ...
@no_cross@	$(MAKE) mkscan            # ← cross_compiling=yes 时这一行整体消失
@no_cross@	diff scan.c initscan.c
```

于是 `make check` 立即返回 0，CI 显示"测试通过"，**而自举比对从未发生**。

判据：在该套件输出里搜其**特有字串**（reflex 为 `Check successful, using COMPRESSION=...`、
`mkscan.sh`、`diff scan.c -`）。只有退出码 0 不足以证明它跑过。

## 根因

`configure` 由 `cross_compiling` 决定 `@no_cross@` 的替换值：

- `--build` 与 `--host` 经 `config.sub` canonical 化后**相等** ⇒ `cross_compiling=no`
  ⇒ `@no_cross@` 为空 ⇒ 自检规则**启用**（检查的是"本机能执行刚构建的产物"）。
- 两者**不等**（或不传、由 config.guess 猜测）⇒ `cross_compiling=yes` ⇒ `@no_cross@`
  展开为 `#` 之类注释符 ⇒ 自检规则**被注释掉**。

所以"交叉构建"这一看似正确的姿势，恰好会静默关闭这类包唯一的回归测试。

## 影响范围

- autotools 包中"用刚构建的产物自举/自检"的 target（`make check`、self-tests、
  bootstrap-regeneration）—— 它们**要求执行**构建产物，因此天然被 `@no_cross@` 守卫。
- CI 里只校验 `make check` 退出码、不校验断言是否真的执行的场景。
- `config.guess` 过旧、无法识别目标内核（HarmonyOS / HongMeng Kernel）的移植场景。

## 推荐方案

**方法**: `set-equal-build-and-host-triplet-to-enable-self-tests`

1. **判定"是否真的跑了"**：在套件输出里 grep 其**特有字串**，而非只看退出码。
2. **显式传相等的 `--build` / `--host`**：本例 `--build=aarch64-linux-ohos`
   与 `--host=aarch64-linux-ohos`，两者 canonical 后相等 ⇒ `cross_compiling=no`
   ⇒ 自检启用；同时这一步天然绕开 vintage `config.guess` 不识别内核的问题。
3. **在 recipe 的 `generate()` 里收敛作用域**：只对 `self.settings.os == "OHOS"` 追加这两个
   参数，避免影响其它平台的正常交叉语义。
4. **把证据写进报告**：把该套件特有输出（如 `Check successful, using COMPRESSION=...` 出现
   N 次）写进 `reports/test-report.md` 与 `reports/w3-local-ci.log`，证明断言确实执行过。

## 验证命令

```bash
./configure --prefix=/ --build=aarch64-linux-ohos --host=aarch64-linux-ohos \
            --disable-shared --enable-static
make -j1
make check 2>&1 | grep -E 'Check successful|mkscan|diff scan\.c'   # 必须有输出，否则自检没跑
```

## 取证记录

- 包: reflex 20241231（`archives/r/reflex/20241231`）
- 逐字证据: `reports/w3-local-ci.log` —— `Check successful, using COMPRESSION=""` 与
  `"-Ce" / "-Cm" / "-f" / "-Cfea" / "-CFer" / "-l"` 共 7 次；
  `reports/test-report.md`「3.1 通过的测试」；`notes.md`（问题 #1）
- 另注: finish 内置的干净构建校验（G0）用**裸 `./configure`**、不带本包必需的
  `--build/--host`，故必然在此包上误报"configure 失败"。**conan-verify 的 G2 与 W3 才走
  recipe 注入的正确参数**，应以它们为准。
