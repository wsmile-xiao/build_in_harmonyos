# smu

smu 是将简化 Markdown 文本转换为 HTML 的命令行工具。上游项目：
[Gottox/smu](https://github.com/Gottox/smu)，许可证 MIT。

## OHOS 适配

smu 1.5 使用原版 C 源码和 Makefile，无第三方库依赖。Conan 配方通过
命令行 Makefile 变量指定 OHOS Clang、编译/链接选项并屏蔽上游配置中的
主机 `/usr` 路径；无需修改 C 源码或新增补丁。`test_package` 直接运行
安装包内的 `bin/smu`，检查 32 项固定预期的转换与命令行行为。

2026-09-23 在 HarmonyOS PC aarch64 上，单文件 OHOS profile 的
`conan create` 已从源码构建并运行包内测试，32/32 通过。验证细节见
[1.5 适配记录](1.5/notes.md)。后续隔离框架 G2 也从源码构建并运行
包内 32/32。2026-09-24 本地 W3 CI 又从源码建包、运行 32/32 并通过；
W3 的 L2 因上游不支持 `--version`/`--help` 记非阻塞 skip。
框架 `conan-verify` 的 G4 未定位包 ID、其 L2/L4/L5 被跳过却显示 PASS，
不能作为实质通过证据。完整 `finish` 在 W3 之后仍因知识图谱与提交
就绪检查未满足而退出 1；独立审计、官方 CI 与发布尚未完成。

## 使用

`smu` 从标准输入或文件读取文本，输出 HTML。例如：

```sh
printf '# Heading\n' | smu
```

上游的 `-v`、`-h` 和非法参数将信息写入 stderr 并返回 1；这是 v1.5
原有行为，自动测试按该契约核对。
