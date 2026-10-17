# TapTempo

[TapTempo](https://taptempo.tuxfamily.org/) 是通过键盘敲击间隔测算 BPM 的命令行工具。版本 1.4.5 使用 GPL-3.0-or-later 许可。

## OHOS 适配候选

配方使用作者官网提供的签名版 1.4.5 源码归档及 SHA-256 校验。补丁提高 CMake 最低兼容版本，并允许分别开启本地化与上游测试。当前候选默认关闭 NLS，以免在未核实 OHOS `msgfmt`、`libintl` 前假定依赖已满足；英文命令行与节拍功能可由包内测试验证。需要本地化时可指定 `-o taptempo/*:with_nls=True`，须先验收构建工具与目标端 Intl。

旧输入在 H1 HarmonyOS PC aarch64 的原生构建、上游 19 个 Catch2 用例/95 条断言和 10 组原生消费者测试通过；旧 Conan 首次 `conan create` 计时敏感消费者为 7/10，随后同一包 `conan test` 为 10/10，旧正式 W3 亦曾通过。当前七补丁候选在 H1-008 的 OHOS/armv8 Conan 和正式 W3 均完成包内消费者 10/10，W3 两脚本 rc0、CI 结果 exit_code=0；随后单独在 H1 原生 CMake `test` 目标补跑当前七补丁树的上游 19/19、95 条断言，并从真实 Conan ELF 经官方工具产出 release/debug tar。完整 `finish` 原次仍 rc1，W5/summary/staging 未完成；独立 W4、官方 CI 和 PR 尚未执行。详细记录见 [1.4.5 适配笔记](1.4.5/notes.md)。

独立 W4 曾发现原消费者计时断言存在门禁波动；修订脚本逐拍等待程序输出，以送入和响应时间界定目标实际消费间隔并核对 BPM，两份运行报告已移出候选。修订脚本在 Windows 主机真实程序上 10/10，并能识别固定 BPM 与忽略采样窗口的模拟程序；H1-008 已覆盖当前七补丁候选的包内消费者与 W3，但最终候选的正式 W4 仍待完成。
