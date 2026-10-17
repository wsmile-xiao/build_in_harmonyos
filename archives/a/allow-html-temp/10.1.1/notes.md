# allow-html-temp 10.1.1 HarmonyOS PC 适配说明

## 软件性质

allow-html-temp 是 Thunderbird WebExtension，不包含 C/C++ 原生代码。其交付物是 XPI（ZIP 格式）扩展包，运行时由 Thunderbird 的 Gecko/WebExtension 环境解释执行。因此本适配不伪造目标平台编译，而是在 HarmonyOS PC Conan 流程中完成可复现打包和消费者结构验证。

## 构建方案

- 从 GitLab 官方 10.1.1 标签归档获取源码并校验 SHA256。
- 使用 Python 标准库 `zipfile`，不引入未发布的 Conan 依赖。
- 仅打包运行所需的 `manifest.json`、许可证、locale、API、图标、选项页和脚本。
- 归档条目按字典序写入，并统一为 ZIP 最早合法时间戳，确保相同源码得到相同 XPI。
- 安装到 `share/allow-html-temp/allow-html-temp-10.1.1.xpi`。

## 测试口径

上游 10.1.1 源码没有测试目录、测试框架或自动化测试命令，上游测试据实记为 0/0（不适用）。本适配自行补全 18 项测试：8 项单元测试读取安装后 XPI 中的 `getButtonPolicy()` 并验证快捷键、显示模式、远程内容和内联附件功能契约；10 项集成断言验证 XPI 存在、大小、CRC、条目顺序、manifest、关键运行资源和固定时间戳。新增测试结果为 18/18 PASS（100%）。

## 平台边界

本包验证的是与平台无关的 WebExtension 制品完整性。Thunderbird UI 中的交互行为依赖宿主应用和邮件账户，不能在无 Thunderbird 的 Conan Worker 中伪造为已通过。
---

**编译结束**: 2026-08-18 03:37
**最终状态**: built
