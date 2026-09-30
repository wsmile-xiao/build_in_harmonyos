# launchctl-completion

macOS `launchctl`(8) 的 bash 补全脚本数据包。上游 v2.0 仅含两个文件：
`LICENSE`（MIT）与 `launchctl-completion.sh`（713 行）；无构建系统、无
测试套件、无安装机制——Homebrew 以单条放置动作完成安装
（`bash_completion.install "launchctl-completion.sh" => "launchctl"`）。

## OHOS 适配形态（E241 data-package-pattern）

- 零编译、零改动：上游内容逐字节打包（`build()` 机读复核文件集合 +
  SHA256），安装即移植完成。
- 安装布局（Homebrew 同款）：

  ```
  <pkg>/share/bash-completion/completions/launchctl   # 改名放置，内容与上游逐字节一致
  <pkg>/licenses/LICENSE
  ```

- 依赖：`bash/5.3`（脚本使用 `compgen -V`——bash 5.3 新增选项——与
  `local -n` 命名引用）。补全文件由用户 bash **source** 加载，脚本自带
  shebang（`#!/usr/local/bin/bash`）不生效、无需修改。
- 配方不设 `package_type`、无 `settings`、无 `commands.json`：包内没有
  可执行产物（被补全的 `launchctl` 命令本身不在包内），R38 门禁不适用。

## 功能面已知限制（诚实披露，不修改上游）

- `launchctl` 本体在 OHOS 不存在：`complete -F` 注册无害，仅当用户
  手敲 `launchctl <TAB>` 时触发。
- 静态一级子命令补全（44 个字面量）在任何 bash >= 5.3 环境可用；
  动态数据源分支（`launchctl list`、`dscl`、`/Library/Launch*`、可选
  `fd`/`segment_dumper`）在 OHOS 产出空集。
- 脚本第 97/102/107 行 `launchctl list` 无 stderr 守卫：补全
  `list <TAB>` 等场景会打印一行 command-not-found 噪声。

## 验证

上游零测试（`NO_UPSTREAM_TESTS`，证据链见
`2.0/test_package/EXCLUDED-TESTS.md` 与同目录机读 JSON）。test_package
以 9 组 10 条适配点静态冒烟承担功能面证据：bash>=5.3 端到端、`bash -n`
语法、source 后 `complete -p launchctl` 逐字注册断言（复刻 Homebrew
test 块）、静态一级补全 44 项成员断言（纯 builtin 路径，不触外部命令、
不写 /tmp）、安装布局与逐文件 SHA256 固定输出比对。
