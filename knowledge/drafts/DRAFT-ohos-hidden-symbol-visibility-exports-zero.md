# DRAFT-ohos-hidden-symbol-visibility-exports-zero — 上游默认隐藏符号 + 源码无 visibility 标注：编译成功但导出 0 个符号

> **对应结构化数据**：`knowledge/drafts/DRAFT-ohos-hidden-symbol-visibility-exports-zero.kv`
> **验证实例**：glu 9.0.3（Mesa GLU，PR #10090，OHOS PC aarch64，SDK 26）
> **Status**: DRAFT ｜ **Severity**: 🔴 high ｜ **Updated**: 2026-09-15

## 1. 一句话

上游构建脚本**无条件**开启默认符号隐藏（`gnu_symbol_visibility: 'hidden'` /
`-fvisibility=hidden`），而源码里**没有**给公开 API 加 `visibility("default")` 标注。
结果：**编译成功、产物尺寸正常、打包签名全过，但动态符号表导出 0 个目标符号**，
消费者链接必然失败。

## 2. 症状（四个绿灯，一个致命隐患）

以 glu 9.0.3 为例，`conan create` 全程：

| 检查点 | 结果 |
|--------|------|
| 编译 | ✅ `rc=0` |
| 产物存在 | ✅ `libGLU.so.1.3.1`，1,575,424 字节（尺寸健康）|
| 打包 | ✅ 成功 |
| 签名 | ✅ `.codesign` 段已写 |
| **动态符号表导出 `glu*`** | ❌ **0 个**（全部 `LOCAL HIDDEN`）|

错误直到**消费者侧链接**才出现：

```
ld.lld: error: undefined reference to 'gluOrtho2D'
```

极易被误归因成「消费者的 CMakeDeps / 链接参数有问题」——而真正的问题在库自身。

## 3. 根因与实测对照

`glu-9.0.3/src/meson.build:106` 无条件写：

```meson
gnu_symbol_visibility : 'hidden',
```

而 glu 源码（`src/*.c`）中**没有任何** `visibility default` 标注。实测受控对照
（同一份源码，唯一变量是**那行是否删除**）：

| 配置 | dynsym 导出 `glu*` | 产物大小 |
|------|-------------------|---------|
| 上游原样（带 hidden）| **0**（全 `LOCAL HIDDEN`）| 1,575,424 B |
| 删除该行 | **64**（`gluOrtho2D` = `GLOBAL DEFAULT`）| 1,714,688 B |

## 4. 关键诊断命令（**必须**用 `--dyn-syms`）

```bash
# ✅ 正确：数动态符号表的「导出」面
readelf --dyn-syms lib<pkg>.so | grep -cE 'FUNC +GLOBAL +DEFAULT'
readelf --dyn-syms lib<pkg>.so | grep -cE 'FUNC +GLOBAL +DEFAULT.*<API 前缀>'
# 期望：与源码公开 API 数量相当，绝不是 0
```

```bash
# ❌ 错误：`.symtab` 不等于可链接导出面
nm lib<pkg>.so | grep gluOrtho2D          # 能查到名字，但它可能是 LOCAL
readelf -s lib<pkg>.so | grep gluOrtho2D  # 同上 —— 被 hidden 的符号在这里是 LOCAL
```

**被 hidden 的符号在 `.symtab` 里仍能查到名字**（标记 `LOCAL`），但它**不在**
`.dynsym` 里 → 消费者链接时依然 `undefined reference`。

## 5. 推荐方案

在配方里用补丁去掉（或收窄）默认隐藏，并**用 `readelf --dyn-syms` 复验**。
三种处理方式，按侵入性递增：

| 方式 | 做法 | 适用 |
|------|------|------|
| **① 直接删除该行**（推荐）| 删掉 `gnu_symbol_visibility: 'hidden'` | 源码无任何 visibility 标注（glu 即此，0 → 64）。副作用：内部符号也被导出，对 ABI 洁净度有洁癖的上游不够优雅，但对 OHOS 适配够用 |
| ② 按需导出 | 给公开 API 补 `__attribute__((visibility("default")))` | 需保留内部隐藏、库很大需控制导出面。代价：改动点 = 公开 API 数量（glu 需标 64 个）|
| ③ 版本脚本 | meson 传 `link_args` 加 `--export-dynamic-symbol` 或 version script | 上游已有符号白名单 |

补丁（方式①，对 meson 项目）：

```diff
--- a/src/meson.build
+++ b/src/meson.build
@@ -103,7 +103,6 @@
  library(..., install : true,
-  gnu_symbol_visibility : 'hidden',
   ...)
```

**修完必须复验**（不能以 `rc=0` 作为完成判据）：

```bash
readelf --dyn-syms <pkg>/lib/lib<pkg>.so | grep -cE 'FUNC +GLOBAL +DEFAULT.*<API 前缀>'
# 期望从 0 变为与公开 API 数量相当的正数
```

并在 notes / README 如实写明「删除了默认隐藏，故内部符号亦被导出」。

## 6. 禁止

- ❌ **以「`conan create` 成功」认定适配完成** —— 本坑的产物是四个绿灯 + 导出 0 个符号。
  「编译通过」不构成「库可用」的证明。
- ❌ **用 `readelf -s` / `nm` 判断导出** —— 那是 `.symtab`，被 hidden 的符号在里面
  仍能查到名字（`LOCAL`），但**不可被链接**。必须用 `readelf --dyn-syms`。
- ❌ **见到 `undefined reference` 就先改消费者侧** —— 本问题层下根因在库自身。
  先花 10 秒查库的 dynsym，再考虑消费者配置。
- ❌ **把「符号没导出」与「依赖库没链接进来」混为一谈** —— 后者查 `readelf -d` 的
  `NEEDED`，前者查 `readelf --dyn-syms` 的导出面。**问题层不同，诊断命令与修法完全不同**。
- ❌ **改完补丁不验证就提交** —— 必须复验导出面（确认恢复 + 未引入新的构建失败）。

## 7. 适用范围

**适用**：任何 meson / CMake 构建、且构建脚本设置默认符号隐藏
（`gnu_symbol_visibility: 'hidden'` 或 `-fvisibility=hidden`）而上游未给导出 API 加
visibility 标注的库。

**不适用**：纯静态库（无 `.dynsym` 概念）；可执行文件。

## 8. 与既有条目的关系（差异化定位）

| 既有条目 | 关系 |
|---------|------|
| **E465** | 那条讲用 embedded-Python launcher 绕过 OHOS worker 的 dlopen 边界（**测试装置**问题），与本条「库自身没导出符号」是**完全不同的两个问题层**。⚠️ 特别提示：本条曾被误标为「E465 ELF 符号可见性」引用过，二者无关 |
| **DRAFT-ohos-r34-static-lib-symbol-check** | 那是 R34 **测试侧**对静态库依赖做符号校验（`DT_NEEDED` 里没有依赖库名时改查 `dbinit`/`tdsdbopen` 符号）；本条是**库自身导出面**为空，前者是测试方法论，后者是产物缺陷 |
| **DRAFT-ohos-desktop-gl-via-mesa-osmesa** | 同批产出的姊妹条目（glu 适配的另一条发现），讲依赖选择而非符号可见性 |

> 查重（2026-09-15）：main 上 `gnu_symbol_visibility` / `symbol-visibility` /
> `符号未导出` / `无导出符号` / `导出符号为 0` / `LOCAL.*HIDDEN` **均 0 命中**；
> `dynsym` 命中 10 个、`readelf --dyn-syms` 命中 11 个，逐一核对后**无一讲
> 「默认符号隐藏致导出 0」**这一问题层（多为 R34 测试侧符号校验、musl RTTI 合并、
> strip 相关）。本条为空白领域。

## 9. 方法论提炼

1. **判定「库是否可用」要看消费者视角的可链接性证据**（dynsym 导出面 + 消费者链接实测），
   而不是构建流程的绿灯。四个绿灯不代表产物可用。
2. **区分 `.symtab` 与 `.dynsym`** —— 前者含局部符号、不可链接；后者才是导出面。
   这是本坑被误判的技术根源。
3. **诊断顺序「从产物往上看」** —— 先查本库 dynsym（10 秒），再查消费者链接参数。
   反了会在正确的下游反复改动。
4. **`undefined reference` 有两类根因** —— 自身没导出 vs 依赖没链接（`DT_NEEDED`）。
   先定性问题层再选命令。
