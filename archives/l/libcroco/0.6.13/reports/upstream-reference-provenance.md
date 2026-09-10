# upstream_reference_provenance — libcroco 0.6.13 R02 参考输出证明链

> R02 任务要求：对每一份失败参考输出记录官方 tag 内容、当前实际输出、逐行差异、
> 关联官方源码行为与上游变更证据；仅当三类证据相互一致时生成受配方管理的最小补丁。

## 证据基线

- 官方 tag：https://gitlab.gnome.org/GNOME/libcroco（tag `0.6.13`）
- 官方 release tarball：https://download.gnome.org/sources/libcroco/0.6/libcroco-0.6.13.tar.xz
- SHA-256（与官方 .sha256sum 清单一致）：`767ec234ae7aa684695b3a735548224888132e063f92db585759b422570621d4`
- 测试驱动器：tests/testctl run（对 tests/test-output-refs/ 参考做 diff 判定）

## 官方 tag 参考内容核验（gitlab raw vs tarball）

三份失败参考输出从 gitlab `0.6.13` tag raw 抓取的 SHA-256 与 tarball 内文件**逐字一致**：

| 文件 | gitlab 0.6.13 raw SHA-256 | tarball 参考 SHA-256 |
|---|---|---|
| test2.1.css.out | 25584c51f09a3d5a5592a823ab9d998c5f6dd75eaa067d0db1dbcefafdbcff30 | 25584c51f09a3d5a5592a823ab9d998c5f6dd75eaa067d0db1dbcefafdbcff30 |
| test2.2.css.out | 22d5f22091dd3c2b9cddbdc41c90e2b40c170b7eebaa6469e6134f6aa4ab1eb1 | 22d5f22091dd3c2b9cddbdc41c90e2b40c170b7eebaa6469e6134f6aa4ab1eb1 |
| test4.1.css.out | ee38bdbd721223eadcffb5e3a038f2ff75d75dd3573aa6bf6860a3cc4d2eee15 | ee38bdbd721223eadcffb5e3a038f2ff75d75dd3573aa6bf6860a3cc4d2eee15 |

⇒ 三份参考输出就是官方 `0.6.13` tag 的原始内容，无本地改写。

## 逐行差异（官方参考 vs 当前实际输出）

在 OHOS armv8 / clang-15 / glib 2.88.0.1 构建产物上以 testctl 实际运行，diff 结果：

### 1) test2.1.css.out — 一行
```
12c12
< prop1: "String"          （官方参考）
---
> prop1: "tring"           （实际）
```
输入（tests/test-inputs/test2.1.css）：`s1[foo] {prop1 : "\83 tring"}`。
字节级：实际输出为 `"\302\203 tring"`（U+0083 的 UTF-8 编码 + " tring"），
即 `\83` 转义被解码为 CSS 十六进制 0x83=U+0083；官方参考 `"String"` 首字符为
'S'（0x53）——旧代码把 `\83` 按十进制 83 解码（旧行为），0.6.13 为修复后行为。

### 2) test2.2.css.out — 两行
```
< line-height: 1.300em    vs   > line-height: 1.3em
< margin-left: 1.250em    vs   > margin-left: 1.25em
```
参考为固定 3 位小数（%.3f 风格）；实际为 `g_ascii_dtostr` 最短往返表示。

### 3) test4.1.css.out — 四行
```
<   padding : 0.400em;                 >   padding : 0.40000000000000002em;
<   padding : 0.900em;                 >   padding : 0.90000000000000002em;
<   margin-left : 0.300em;             >   margin-left : 0.29999999999999999em;
<   padding-left : 0.200em             >   padding-left : 0.20000000000000001em
```
参考为 3 位小数；实际为本机 glib 2.88.0.1 `g_ascii_dtostr` 的精确往返输出
（独立探针实证 `g_ascii_dtostr(0.4)='0.40000000000000002'`）。
数值本身一致，仅显示格式不同。

## 关联官方源码行为（0.6.13 tag 源码）

- `src/cr-num.c` `cr_num_to_string()`：非整数用 `g_ascii_dtostr(buf, G_ASCII_DTOSTR_BUF_SIZE, val)`
  —— 这是**修复后**行为（最短往返），不可能产生 `0.400em`/`1.300em` 这类固定 3 位输出。
- `src/cr-tknzr.c`：CSS 转义按十六进制解码（`\83` → U+0083），为 Bug 314831/394294 修复后行为。
- ChangeLog 明确记载：
  - `Bug 381040 - floating numbers always output to exactly 3 digits after decimal points.`
    （修复前固定 3 位小数——正是参考输出所展示的旧格式；修复后为最短往返）
  - `Bug 314831 - Escapes not recognized` / `Bug 394294 - Escape are wrongly computed`
    （cr-tknzr.c 转义计算修复）
- gitlab API 提交时间（0.6.13 分支）：
  - test-output-refs/test2.1.css.out：最后修改 **2003-04-04**（Dodji Seketeli）
  - test-output-refs/test2.2.css.out：最后修改 **2003-04-04**（同一次提交）
  - test-output-refs/test4.1.css.out：最后修改 **2004-03-04**
  - src/cr-num.c：最后修改 **2014-08-05**（gchar/guchar types and casting）
  - src/cr-tknzr.c：最后修改 **2017-04-16**

⇒ 参考输出在 2003-2004 年生成后从未随 Bug 381040 / 314831 / 394294 修复更新；
0.6.13 源码（2014/2017 后行为）在任何平台（含上游自己的 Linux）都无法复现这些参考。

## 三类证据一致性结论

| 参考文件 | 官方 tag 内容 | 实际输出 | 上游变更证据 | 一致性 |
|---|---|---|---|---|
| test2.1.css.out | "String"（十进制转义旧行为） | U+0083（hex 转义修复后行为） | Bug 314831/394294 + 参考 2003 年冻结 | 一致：参考为修复前输出 |
| test2.2.css.out | 1.300em/1.250em（3 位小数） | 1.3em/1.25em（g_ascii_dtostr） | Bug 381040 + 参考 2003 年冻结 + cr-num.c 2014 | 一致：参考为修复前格式 |
| test4.1.css.out | 0.400em/0.900em 等（3 位小数） | 0.40000000000000002em 等（精确往返） | Bug 381040 + 参考 2004 年冻结 + cr-num.c 2014 | 一致：参考为修复前格式 |

**结论**：三份失败参考输出均由官方 0.6.13 源码、官方变更记录与可重复实际输出
共同证明为陈旧参考（upstream reference staleness）。差异全部来自被上游修复的
旧行为（固定 3 位小数、十进制转义），非 OHOS 适配缺陷，非解析/序列化功能错误。
符合 R02 任务"不得修改上游生产源码以迎合旧参考"的前提——修复对象是参考输出本身。