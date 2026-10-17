# E543 — 上游测试参考输出陈旧（reference outputs 早于源码行为修复）：三证据证明链 + 配方管理最小补丁更新参考

> Contributor: 4CD6 | Status: Draft | Updated: 2026-09-10
> Source: libcroco 0.6.13 高难度挑战 R02（OHOS aarch64，feat/libcroco-0.6.13）
> 关联先例: E011（config.status tmpdir）、E122（config.sub linux-ohos）、E236（libtool .la 元数据）

## 错误特征

`testctl` 非回归测试运行正常、无崩溃，但输出比对 KO：

```text
SOME TESTS ARE KO :(
See tests/tests-error.log
--- test-output-refs/test2.1.css.out
-prop1: "String"
+prop1: "tring"
--- test-output-refs/test2.2.css.out
-line-height: 1.300em
+line-height: 1.3em
--- test-output-refs/test4.1.css.out
-  padding : 0.400em;
+  padding : 0.40000000000000002em;
```

差异只涉及转义字符与浮点显示格式，解析/序列化功能正确、无崩溃。

## 触发条件

- 构建系统: autotools（tests/testctl + test-output-refs diff 判定）
- 阶段: testing
- 特征: 官方 release 年代久远（参考文件冻结于 2003-2004），源码在后续多年被
  Bug 修复改变行为但参考输出未重生成

## 根因分析

上游 `test-output-refs/` 参考输出生成于 2003-2004 年（gitlab API 提交时间实证），
此后上游修复了多个行为 Bug 但从未重生成参考：

- Bug 381040：`floating numbers always output to exactly 3 digits after decimal
  points`——修复后 `cr_num_to_string` 改用 `g_ascii_dtostr`（最短往返表示），
  无法再产生 `0.400em`/`1.300em` 这类固定 3 位小数输出；
- Bug 314831 / Bug 394294：`Escapes not recognized` / `Escape are wrongly
  computed`——`cr-tknzr.c` 转义计算修复，`\83` 由十进制 83（'S'）改为十六进制
  0x83（U+0083）。

因此 0.6.13 源码在任何平台（含上游自己的 Linux）都无法复现其自身参考——
参考输出与源码行为永久脱节，属于上游测试资产陈旧而非适配缺陷。

## 解决方案

### 推荐方案（三证据证明链 + 配方管理补丁）

1. **证据1（官方 tag 内容）**：从官方 gitlab tag raw 抓取失败参考文件，
   与 tarball 内参考做 SHA-256 逐字比对——一致证明参考为官方原物、无本地改写；
2. **证据2（上游变更记录）**：gitlab API 查参考文件最后提交时间（远早于源码
   最近修改）+ ChangeLog 定位改变行为的 Bug（381040/314831/394294）；
3. **证据3（可重复实际输出）**：在构建产物上重跑 testctl 获取逐行 diff，
   确认差异行全部落在被修复行为的特征格式上。

三类证据一致确认"参考陈旧"后：
- 生成最小补丁，将参考输出更新为修复后行为（**只改 tests/test-output-refs/**，
  不碰生产源码）；
- 补丁登记进 `conandata.yml` 的 `patches:`（受配方管理），`patch_type` 标注
  `test-references`；
- 对官方归档干净副本验证 `patch --dry-run` 与实际应用（SHA 比对）；
- 重跑 testctl 全量入口与全部输出比对，要求 16/16（或任务要求数）通过。

### 禁止做法

- ❌ 回退库生产源码以迎合旧参考（会把上游 Bug 修复改回去，且影响消费者行为）；
- ❌ 直接改仓库内参考文件而不走配方补丁（补丁须对官方归档干净应用）；
- ❌ 跳过、排除、禁用、软化比较、伪造输出或改统计口径把未通过项写为通过。

## 验证

```bash
# 参考文件冻结时间（gitlab API）
curl -fsSL 'https://gitlab.gnome.org/api/v4/projects/GNOME%2Flibcroco/repository/commits?path=tests/test-output-refs/test2.1.css.out&per_page=1'
# 官方 tag raw 与 tarball 参考 SHA 比对
curl -fsSL 'https://gitlab.gnome.org/GNOME/libcroco/-/raw/0.6.13/tests/test-output-refs/test2.1.css.out' | sha256sum
# 补丁干净应用
patch --dry-run -p1 < patches/0003-refresh-test-refs.patch
# 全量重跑（libcroco 实例：11 入口、16 项比对全过）
cd tests && ./testctl run   # -> ALL THE TESTS ARE OK
```

## 关联条目

- 相关: E011（HMDFS config.status umask）、E122（config.sub linux-ohos）、
  E236（libtool .la 元数据）——同属 autotools 老库 OHOS 适配族
- 先例: DRAFT-ccfits-2.7-stale-pc-prefix-regen（另一类"陈旧资产"：依赖 .pc
  绝对 prefix）