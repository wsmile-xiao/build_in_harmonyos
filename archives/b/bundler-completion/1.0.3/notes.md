# bundler-completion 1.0.3 适配笔记

## 编译环境
- 构建系统: custom（纯 bash 补全脚本，无需编译）
- 编译日期: 2026-09-12
- 编译器: N/A（纯文本文件）
- 状态: built

## 编译步骤

bundler-completion 是 Ruby Bundler 命令的 bash 补全脚本，无传统编译流程：

1. 上游源码: mernen/completion-ruby v1.0.3
   （tarball sha256 `cbcd002bba2a43730cff54f5386565917913d9dec16dcd89345fbe298fe4316b`，下载后校验通过）
2. `conan create` 由配方完成安装：
   - `get()` 解压源码（strip_root）
   - `completion-bundle` → `share/bash-completion/completions/bundler`
   - `MIT-LICENSE` → `licenses/`
3. `package_info` 导出 `resdirs = ["share"]`（纯数据包，无 bin/lib/include）

安装名映射沿用 Homebrew bundler-completion formula 的 `completion-bundle` → `bundler`。
该脚本加载后为 `bundle`/`bundler` 及版本化别名（bundle2.0–2.7、bundle3.0–3.3、
bundler2.0–2.7、bundler3.0–3.3）注册 `complete -F __bundle`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试套件无法直接运行 | `tests/completion-bundle/test.sh` 需要真实 Rails 应用（RAILS_TEST_APP_DIR）和 bash-completion 库 | 在设备上构造最小 Rails 应用（Rakefile 提供 db:migrate 任务）并把 bash-completion 源码目录纳入环境 |
| 2 | Rails 依赖的 nokogiri 在 OHOS/aarch64 无可用原生扩展 | 预编译 musl `.so` 缺少 `.note.ohos.ident`，dlopen 报 Permission denied | `--ignore-dependencies` 安装纯 Ruby 组件并为 nokogiri 生成 ruby 平台 spec，`rails --help` 可用 |
| 3 | 补全测试一度返回空结果 | `~/.cache/completion-ruby/rails--exec` 缓存了此前失败轮的空输出 | 清理该缓存目录后重跑，结果稳定 |

## 源码修改

无源码修改（纯文本 completion 脚本，无补丁）。

## 依赖版本

| 依赖 | 类型 | 说明 |
|------|------|------|
| bash-completion | 运行依赖 | 提供 `_get_comp_words_by_ref` / `_filedir` / `__ltrim_colon_completions` 等补全框架函数 |

无编译依赖。

## 验证结果

- 上游测试（设备实跑）: `bash tests/completion-bundle/test.sh` → 4/4 PASS
  （basic commands / global options / `bundle exec rake` / `bundle exec rails`）
- 消费者测试（test_package）: 校验安装文件存在、`bash -n` 语法通过、定义 `__bundle()`、
  含 `complete -F __bundle` 注册、source 后 `complete -p bundler` 与 `complete -p bundle`
  均指向 `__bundle`（6 项断言）
- 配方验证: 设备 W3 finish 流水线（`conan create` + conan-verify G0–G4/L2/L4/L5 + 本地 CI 模拟）

## 注意事项

1. 本包只包含 bundler 补全（上游 `completion-bundle`）。`bundle exec rake|rails …`
   的子命令参数补全依赖上游其余脚本（completion-rake/completion-rails），不在本包范围。
2. 需要 bash-completion 包提供补全框架才能生效（source 后 `bundle <Tab>` 才有补全输出）。
3. 纯数据包：全部制品位于 `share/`，无 bin/lib/include 目录。

**编译结束**: 2026-09-12
**最终状态**: built
