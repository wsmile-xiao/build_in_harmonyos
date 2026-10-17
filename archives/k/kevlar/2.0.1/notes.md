# kevlar 2.0.1 适配笔记

## 编译环境
- 构建系统: makefile（纯 make，无 configure；makefile 提供 kevlar/rst2html/md2html 三个 CLI 目标）
- 编译日期: 2026-09-21
- 编译器: clang/clang++（OHOS arm64 profile）
- 状态: built

## 编译步骤

```bash
# 源码：官方 tag v2.0.1 归档（零依赖纯 C）
make CC=clang CFLAGS="-Wall -Wextra -O3 -fPIC" all
# 注意：makefile 的 md2html 链接目标硬编码 `gcc`，环境中无 gcc 时
# 需提供 gcc -> clang 包装（conanfile generate() 自动生成并注入 PATH）。
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make all` 编译失败：`recipes/md2html.c:36: too few arguments to function call, expected 3, have 2` | 上游 `md_parse()` 声明 3 参（含 offset），独立 recipe `md2html.c` 仍按旧 2 参调用，属上游编译错误（上游 `make all` 在任何平台都会失败） | 补丁 0001：`md_parse(in_file_path, out_file_path, 0)` |
| 2 | `kevlar build`/`rst2html` 挂起死循环（CPU 100%），产物为空 | `rst_get_file_length()` 用 `for (char c = getc(infile); c != EOF; ...)` 统计行数；本平台（OHOS arm64）`char` 为 unsigned，`getc` 返回的 `EOF(-1)` 截断为 `0xFF`，永不等于 `EOF` → 无限循环 | 补丁 0002：循环变量改为 `int c` |
| 3 | makefile md2html 目标硬编码 `gcc` 链接 | 构建环境无 gcc（仅 clang） | conanfile `generate()` 在 build_folder 私有 bin 目录生成 `gcc`->clang wrapper，`build()` 将该目录前缀注入 PATH（R33 合规：不依赖 shell 未定义变量） |

## 源码修改

- `recipes/md2html.c`（补丁 0001-recipes-md2html.c.patch）：md_parse 调用补 offset 参数
- `src/kevlar_rst_to_html.c`（补丁 0002-src-kevlar_rst_to_html.c.patch）：getc 循环 char→int 修复 EOF 检测

## 依赖版本

- 零第三方依赖（pure C，仅 C 标准库；`md2html` 链接 `-lm`）
- 工具链：clang 15.0.4 / make 4.4.1

## 验证结果

```bash
# 端到端站点生成（消费者验证，test_package/test.sh 复现）
./bin/kevlar help            # exit 0，打印 help
./bin/kevlar new demo-site   # exit 0，生成骨架
./bin/kevlar build           # exit 0，生成 dist/index.html + dist/hello-world.html
# markdown 内容正确渲染：<h1>Welcome to kevlar!</h1>
./bin/md2html in.md out.html # exit 0
./bin/rst2html in.rst out.html # exit 0
# conan-verify: G0-G4 + L2/L4/L5 全 PASS；W3 本地 CI 模拟通过（exit_code=0）
```

## 上游测试说明

kevlar 2.0.1 上游**无任何自动化测试**：makefile 无 check/test 目标；
无 tests/ 目录；README 的 v3 计划才提出引入单元测试。CLI 功能验证
以真实站点生成 + 各二进制 smoke 测试覆盖（见 test_package）。

## 注意事项

- kevlar 是 CLI 应用（package_type=application），非库：无 cpp_info.libs，
  需在软件级目录提供 `commands.json`（R38，L0k 门禁校验）。
- 上游 `kevlar new` 通过 `system("git clone ...")` 克隆主题；沙箱 CI 中
  test_package 直接本地提供主题模板以保证 hermetic（不依赖网络）。
- W3 期间整仓 junk_check full 模式会命中其他库（cloog/kics）已提交的
  .build-closed/.staging-verified 基线空文件，已按基线隔离流程处理：
  记录路径与 SHA-256 → 临时隔离 → 复跑门禁 → 原样恢复并核对哈希一致。
---

**编译结束**: 2026-09-21 01:04
**最终状态**: built（PR 交付阶段；制品上传后才升级为 published）
