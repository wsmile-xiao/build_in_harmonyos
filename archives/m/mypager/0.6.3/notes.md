# mypager 0.6.3 适配笔记

## 任务信息

- 平台任务号：9075（活动：开源鸿蒙PC专项积分赛-依赖）
- 分支：feat/mypager-0.6.3；worktree：~/qzy/glm44-mypager
- 上游：https://github.com/romuald/mypager tag 0.6.3（tarball sha256 220ee3ed…f064）
- 语言：Perl 5（单文件脚本 434 行，任务声明 cpp 为 SCT 误标；lang-preflight 以文本特征判 c 通过——实际交付物为 Perl 脚本，本笔记如实更正）；构建系统：Makefile（仅 install/cp，无编译）
- 主理 agent：9/17-GLM-44（09-19 CI 挂起修复：GLM-56）
- 本任务在 ohpcd 平台异常期间适配：PR 建好后由用户在平台恢复后导入/绑定/提审。

## W0 依赖检查

- 零精确版本依赖（conan 意义上）。脚本运行时依赖：perl（核心模块 strict/warnings/POSIX/Encode/Digest::MD5/Fcntl/Module::Load/Term::ANSIColor 均为 perl 5.42 核心）；Term::ReadKey 为可选增强（代码内 eval + stty 回退）。
- OHOS hnp 自带 perl 5.42（/data/service/hnp/bin/perl），实测 `perl -c mypager` 通过。

## W0b 历史经验

- 仓库无 mypager 历史归档，首次适配。recipe-search 无同包配方。
- CI worker PATH 不含 /data/service/hnp/bin（CI 构建日志 env 实证），消费者测试须显式 PATH 前缀注入以解析 `#!/usr/bin/env perl`。
- CI worker 的 stdin 永不 EOF：任何等 stdin 的交互式运行都会挂到 4 小时超时（CI build #48997 实证）——脚本型包的 smoke 必须选无 stdin 依赖的行为。

## 上游测试清点（R51 证据）

Makefile 仅含 default（echo 安装提示）、install-bin/install-doc、uninstall 目标；无 check/test 目标，无测试框架：静态声明总数 N_static = 0。上游无测试程序资产（包体即单个 Perl 脚本）。

## 四维测试账本

| 维度 | 数量 | 说明 |
|---|---|---|
| 上游静态声明 N_static | 0 | Makefile 无 check/test 目标 |
| 构建注册 N_registered | 0 | 无上游测试资产 |
| 实际执行 N_executed | 0 | 无上游测试可执行（上游 smoke：perl -c + --installconf 由 build() 承担，见下） |
| 消费者测试 N_consumer | 1 | test_package/dd_consumer.c（N_assertion=3） |

build() 内的上游 smoke 门禁（上游无测试框架的等价执行）：
1. `perl -c mypager`——语法编译门（实测通过）；
2. `HOME=<构建目录>/confhome perl mypager --installconf`——真实运行可执行门（上游唯一文档化开关：
   向全新 HOME 写入 .mypager.conf 并退出码 0，配方再断言该文件生成；HOME 指向全新目录，
   既不碰真实用户配置，也不会触发"配置已存在，Overwrite? [y/N]"的 stdin 询问）。
   ⚠️ 不能 argless 或 `--help` 运行：脚本没有 --help 开关（只有 --installconf），
   无参数时循环读 STDIN 直到 EOF——CI worker stdin 永不关闭 → 构建挂起 4 小时超时（09-17 CI #48997 实证）。

## 消费者测试设计

1. dd_consumer.c 以使用者身份编译独立 C 程序；
2. test() 注入 PATH（hnp perl 解析脚本 shebang）与 MYPAGER_SCRIPT（打包产物绝对路径）；
3. 断言：①`mypager --installconf`（per-run 全新 HOME）退出码 0 且 ~/.mypager.conf 真实生成；
   ②短文本经分页器管道透传内容不丢失（短于一页的输入不得被截断）。任一失败退出码非 0。
   G2 实测输出：`dd_consumer OK: mypager --installconf and pipe-through verified`。

### 消费者测试修改说明（09-19 GLM-56）

- 原文件：test_package/dd_consumer.c（第 1 部分断言）与 conanfile.py build() 第 2 项 smoke。
- 原断言：`mypager --help` 退出码 0 且输出 usage。
- 修改原因：上游脚本没有 --help 开关；该断言在 CI worker 上把构建挂死 4 小时（build #48997 实证），
  属测试前提错误而非环境限制。
- 修改内容：改为 `--installconf` 行为断言（全新 HOME 下退出码 0 + .mypager.conf 生成），
  比原断言更贴近上游文档行为；第 2 部分管道透传断言不变；N_assertion 仍为 3。
- 结果：真机 conan create + test_package 通过（见验证命令节）。

## 构建方式

- 无编译步骤：build() 仅执行 perl -c 与 --installconf smoke；package() 复制 mypager（chmod 0755）与 LICENSE。
- commands.json（R38，工具类）：archives/m/mypager/commands.json（type=tool，name=mypager，versions 含 0.6.3）。

## 路径 B 判断

判定：**纯 A**。Perl 脚本包在 OHOS 的打包与验证模式（hnp perl + PATH 注入）对后续同类脚本
包有参考意义，但样本量 1、且依赖 hnp 环境细节，不足以形成可复用知识条目；无新错误签名。
无新增知识草稿、无知识库扩展 Issue。

## 构建环境

- 设备真机（OHOS aarch64），CONAN_HOME=~/tmp/ch/home-mypager；profile ci/conan/profiles/ohos-aarch64。
- 源码下载：官方 tarball 按 SHA256 预置共享 download_cache（E017 ghfast 超时防御，sidecar 双 URL）。

## 验证命令与结果

- `python3 scripts/ohc-run.py conan-verify mypager 0.6.3`：**Verdict PASS**（G0-G4）。
- 第一轮 G2 失败为消费者测试源码笔误（fp 未声明），修正后第二轮 PASS（非适配问题）。
- 09-19 GLM-56（--installconf 修复后）：conan-verify **Verdict PASS**（G0-G4，消费者测试
  输出 `dd_consumer OK: mypager --installconf and pipe-through verified`）。

## 已知限制

- Term::ReadKey（CPAN 非核心）未安装：脚本自动回退 stty 取终端尺寸，功能完整。
- install-doc（pod2man 手册）未包含：OHOS 无 pod2man，手册不影响二进制功能。

## finish 收尾块

- conan-verify：PASS（G0-G4）；W3 本地 CI：见 reports/w3-local-ci.log；W4 独立审计：提交前完成（P0/P1 清零）。
- 测试数字同源核对：notes.md = MANIFEST.yml = PR 正文 = result.json（N_static=0，N_executed=0，
  上游 smoke 2 项通过，N_consumer=1，N_assertion=3）。
- 提交方式：精确 add archives/m/mypager/（commands.json 在软件级目录）。
---

**编译结束**: 2026-09-19 03:05
**最终状态**: built
