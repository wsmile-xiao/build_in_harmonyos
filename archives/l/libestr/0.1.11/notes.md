# libestr 0.1.11 适配笔记（重做版）

> 本归档接管自 goblinrs 的 PR #4774（已关闭，CI 红根因：配方缺 tool_requires）。
> 修复配方已在 rsyslog-cisco 依赖链任务中本地验证通过（conan create EXIT 0）。

## 编译环境
- 构建系统: autotools（GitHub tarball 无 configure，autoreconf -fiv bootstrap）
- 编译日期: 2026-09-05
- 编译器: clang/clang++（OHOS SDK 交叉）
- 状态: published

## 相对 PR #4774 的关键修复

1. **tool_requires 注入**（CI 红根因）：`build_requirements()` 声明
   `automake/1.18` + `libtool/2.5.4`——CI clean 环境无系统级 autotools，
   旧配方裸跑 `autoreconf` 失败。
2. **OHOS 交叉 triplet**：`--build=aarch64-unknown-linux-gnu
   --host=aarch64-unknown-linux-ohos`，避免依赖 config.guess 对 OHOS 的识别。
3. **补丁清零**：旧版 2 个 config.guess/config.sub 补丁不再需要——
   tool_requires 的 automake 自带 OHOS-aware config.guess/config.sub，
   autoreconf 重新生成（R6：只改源文件不改生成文件）。
4. **R26 静态构建**：default_options shared=False，--enable-static --disable-shared。
5. **HMDFS workaround**：umask 022 + config.status 的 umask 077 sed 修复
   （E046：config.status 临时目录权限问题）。

## 验证记录

- 本地 `conan create`（ohos-aarch64 profile，--user=ohpcd --channel=stable）：EXIT 0
- test_package 输出：`libestr version: 0.1.11`、`String round-trip OK`、`test libestr 0.1.11: OK`

## 功能测试结果 (2026-06-03, 沿自旧归档)

12组30项API测试: 29 PASS / 1 FAIL (es_str2num_hex 上游bug)

### 已知上游缺陷

**es_str2num_hex**: `tolower(c[i]) - 'a'` 缺少 `+10`。上游代码缺陷，
`es_str2num("0xFF")` 返回 85（应为 255）。适配不修上游 bug，PR 正文已声明。

## 上库合规性

- ✅ 门禁 G1-G4 PASS
- ✅ W0 依赖检查：automake/1.18、libtool/2.5.4 均已在制品仓
- ✅ 制品仓查重：libestr 未发布（无重复适配）
- ✅ 无补丁（R6/R23）

## 注意事项

- 纯库无可执行二进制，G2 ⚠️1 正常（无需 commands.json）
- `autoreconf -fiv` bootstrap 需预先删除 `install-sh~`
- `install-sh~` 触发 automake BUG.am 虚警
---

**编译结束**: 2026-09-05 12:01
**最终状态**: published
