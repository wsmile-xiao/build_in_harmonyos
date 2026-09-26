# DRAFT-E723 — autosetup 系 configure 在 OHOS 的三连错与配方三改

> Draft: DRAFT-E723
> Stem: `ohos-autosetup-configure-bootstrap` — pairs with the same-stem `.kv`
> 来源事件：jimtcl 0.83 OHOS 适配（任务 contrib-14157，2026-09-25）

## 基本信息

- **ID**: DRAFT-E723
- **严重度**: 2
- **类别**: build-system|platform|autosetup
- **触发工具**: configure / autosetup
- **阶段**: configuration

## 错误特征（按出现顺序）

```text
1) No working C compiler found. Tried cc and gcc.
2) autosetup/autosetup-config.guess: can't create .../cgXXXXXX/dummy.c: Permission denied
   autosetup/autosetup-config.guess: unable to guess system type
3) Error: Invalid configuration `aarch64-unknown-linux-ohos': OS `ohos' not recognized
4) Error: Unknown option --oldincludedir      （--enable-static/--disable-shared 同族）
```

任一命中即定位到本条；四类分别对应**自举编译器 / config.* 代际 / config.sub 校验 /
Conan 注入参数**四个层级。

## 根因 (Root cause)

autosetup（Steve Bennett 的 autotools 兼容实现）与三方假设互不相容：

1. `autosetup/autosetup-find-tclsh` 在无已装 jimsh/tclsh 时自举 `jimsh0`，
   编译器候选只有 `cc gcc c89 c99`，**不消费 `CC`**（只认 `CC_FOR_BUILD`/`HOST_CC`）；
   OHOS 设备 PATH 只有 clang ⇒ 直接失败。
2. 上游 vendored 的 `autosetup-config.{guess,sub}`（2021-06-03 快照）无
   `HarmonyOS` / `ohos` 分支；主 case 不命中后 config.guess 落到编译探测路径，
   在 HMDFS `umask 077` 临时目录上写 `dummy.c` 被拒（放大成 `Permission denied`，
   与 E564 观察到的表象相同，但**本代脚本锚点布局不同**）。
3. Conan 2.29 `AutotoolsToolchain` 按 GNU autotools 想定默认注入
   `--oldincludedir/--datarootdir`（autosetup/system.tcl 兼容目录表没有这两项），
   `package_type=static-library` 时还注入 `--enable-static/--disable-shared`
   （autosetup 只实现 `--shared` 开关）—— configure 首屏即 `Unknown option`。
4. 附带枚举坑：Conan 2.29 的合法 package_type 是 **`static-library`（连字符）**；
   `library` 类型强制要求声明 `shared` 选项。

## 解法 (Fix) — 配方三改

| # | 改动 | 位置 |
|---|------|------|
| ① | `env.define("CC_FOR_BUILD", conf["tools.build:compiler_executables"]["c"])`（经 `tc.environment()` 传给 `tc.generate(env=...)`；native 双 profile 下 AutotoolsToolchain **不会**自动生成该变量） | conanfile `generate()` |
| ② | 两份 portability 补丁：`config.guess` 主 case **首位**注入 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`（早退，绕开 TMPDIR 探测）；`config.sub` 在 `case $os` 通用列表加 `ohos*`、`case $kernel-$os` 组合表加 `linux-ohos*` | `patches/0001-*`、`patches/0002-*` |
| ③ | `tc.configure_args = [a for a in tc.configure_args if not a.startswith(("--enable-static","--disable-shared","--oldincludedir","--datarootdir"))]` | conanfile `generate()` |

**与 E564 的分工**：E564 针对 2012–2015 旧式 `GUESS=` 前时代的 config 脚本（maybe_os +
basic os 双锚点、禁用 perl 工具）；本条是 **2021 版 vendored autosetup 快照**（主 case 注入 +
`case $os` / `case $kernel-$os` 两处），并额外覆盖 CC_FOR_BUILD 与 Conan 参数剔除两个
E564 未涉及的层面。两者锚点集合不同，可并存。

## 验证 (Verification)

```sh
# 设备可执行（$TASK_DIR 落点，不用 /tmp）
cd "$WORKSPACE_ROOT/tmp/builds/jimtcl-0.83.work"      # pristine 源
CC=/data/service/hnp/bin/clang ./configure --prefix=/ 2>&1 | head -3   # 复现 1/2
cd "$TASK_DIR/applytest/jimtcl-0.83"                   # 打过补丁的源
sh autosetup/autosetup-config.guess                    # → aarch64-unknown-linux-ohos
sh autosetup/autosetup-config.sub aarch64-unknown-linux-ohos   # → 接受，rc=0
# 端到端：conan create rc=0（含 make -j1 check 与 test_package 12 断言全绿）
```

实测：jimtcl 0.83 三改后 `conan create` rc=0；补丁三关（NUL=0 / `@@` hunk ≥1 /
真 apply 后逐字节 `cmp` 一致）通过。

## 影响范围

一切 vendored `autosetup/` 的上游（jimtcl、sqlite-autoconf、autosetup 生态）；
判别：`ls autosetup/autosetup-find-tclsh` 或 prescan 命中 `No working C compiler found`。
