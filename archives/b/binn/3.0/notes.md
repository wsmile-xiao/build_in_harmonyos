# binn 3.0 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-09-06}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}

## 上游测试双口径台账（binn 3.0）

枚举规则：官方 tag 源码 `test/` 目录全部顶层 `void test_*(...)` 用户测试例程 + 独立 main 式测试，逐项列入；框架内部函数、样例、fixture 辅助不入独立用例但记录归属。

| # | 入口（源码声明） | 归属文件 | 分类 | 是否独立用例 | 是否运行 | 结果 |
|---|------------------|----------|------|--------------|----------|------|
| 1 | test_binn_version | test/test_binn.c | 用户测试 | 是 | 是（test_binn 可执行） | PASS |
| 2 | test_endianess | test/test_binn.c | 用户测试 | 是 | 是 | PASS |
| 3 | test_int64 | test/test_binn.c | 用户测试 | 是 | 是 | PASS |
| 4 | test_floating_point_numbers | test/test_binn.c | 用户测试 | 是 | 是 | PASS |
| 5 | test1 | test/test_binn.c | 用户测试 | 是 | 是 | PASS |
| 6 | test2(BOOL) | test/test_binn.c | 用户测试（main 调 2 次） | 是 | 是 | PASS |
| 7 | test3 | test/test_binn.c | 用户测试 | 是 | 是 | PASS |
| 8 | test_invalid_binn | test/test_binn.c | 用户测试 | 是 | 是 | PASS |
| 9 | test_binn2（驱动） | test/test_binn2.c | 用户测试 | 是 | 是 | PASS |
| 10 | test_virtual_types | test/test_binn2.c | 用户子例程（由 test_binn2 调） | 是 | 是 | PASS |
| 11 | test_int_conversion | test/test_binn2.c | 用户子例程 | 是 | 是 | PASS |
| 12 | test_binn_int_conversion | test/test_binn2.c | 用户子例程 | 是 | 是 | PASS |
| 13 | test_value_conversion | test/test_binn2.c | 用户子例程 | 是 | 是 | PASS |
| 14 | test_value_copy | test/test_binn2.c | 用户子例程 | 是 | 是 | PASS |
| 15 | test_binn_read(void*) | test/test_binn2.c | 参数化辅助（由 test_binn2 调） | 是 | 是 | PASS |
| 16 | test_binn_iter(BOOL) | test/test_binn2.c | 参数化辅助（TRUE/FALSE 两次） | 是 | 是 | PASS |
| 17 | main() JSON 转换往返 | test/test_binn_json.c | 独立 main 式测试（依赖 jansson） | 是 | 是 | PASS（r02 补丁修复上游 void main() 无 return 的未定义退出码，实测 rc=0；详见 r02 台账更新） |
| – | src/binn.h / src/binn.c | 框架头/源码 | 被测实现 | 否 | – | – |
| – | conversions/json/binn_json.c/h | 框架转换模块（需 jansson） | 被测实现 | 否 | – | – |
| – | examples/reading.c / writing.c | 样例 | 非独立用例 | 否 | 未运行（样例） | – |
| – | test_binn2.c 中被注释的 void main() | 冗余入口（上游注释禁用） | 非用例 | 否 | – | – |

- source_declared_total = 17（8+8+1，顶层 test 例程全数枚举）
- configured_executable_total = 17（全部编译为 test_binn 可执行 / json 测试）
- executed_passed_total = 17；失败 0；未运行 0
- 全量通过率 = 17/17 = 100%；当前配置可执行集合通过率 = 17/17 = 100%
- 构建入口：makefile `test:` 目标＝`cc -g -Wall -DDEBUG -o test/test_binn test/test_binn.c test/test_binn2.c src/binn.c` 后运行；test_binn_json 单独编译（追加 jansson 依赖：conan install jansson/2.15.1，include/库路径取自 conan 缓存）
- 日志：make-test.log / test_binn_json_run.log
## r02 返工更新：test_binn_json.c 退出码修复与台账复核（task binn-3.0-r02）

根因：上游 test/test_binn_json.c 声明 `void main()` 且无显式 return，进程退出码未定义
（OHOS aarch64 实测为 7）。修复：补丁 0001-fix-test-binn-json-main-return.patch 将入口
改为 `int main()` 并在末尾 `return 0;`，全部断言/输出语义零改动；补丁已登记 conandata.yml
（patch_type: portability）。修复后编译运行实测退出码 0，输出完整（successful conversion /
id/name/value/active/list items 12/23/34 全部打印）。

r02 台账复核结论（与 r01 枚举口径一致）：
- source_declared_total = 17（test_binn.c 8 + test_binn2.c 8 + test_binn_json.c 1）
- configured_executable_total = 17（make test 编译 test_binn 覆盖 16；test_binn_json
  经补丁修复后与 jansson/2.15.1 独立编译为可执行）
- executed_passed_total = 17；failed = 0；not_run_or_uninstantiated = 0
- 全量通过率 = 17/17 = 100%；当前配置可执行集合通过率 = 17/17 = 100%
- 第 17 例 test_binn_json 退出码由 7 修复为 0，不再计入 quality_warnings
- 日志：r02-make-test.log（make test，rc=0）、r02-json-build.log / r02-json-run.log
  （json 编译与运行，rc=0）
---

**编译结束**: 2026-09-06 23:07
**最终状态**: built
