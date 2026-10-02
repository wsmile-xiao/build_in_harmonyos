# virt-what

> Detects whether the system is running in a virtual machine and reports the result as facts.

## 简介

`virt-what` 是一个用于识别虚拟机与部分容器环境的命令行工具。它根据系统信息输出一行或多行检测结果；未识别到虚拟化环境时不输出事实。

该软件还提供 `virt-what-cvm` 和 `virt-what-cpuid-helper` 辅助程序。上游使用 Autotools 构建，当前版本为 1.27。

## OHOS 适配要点

- HarmonyOS PC aarch64 使用系统 clang 原生编译，无第三方 Conan 依赖。
- 上游旧版 `config.guess` 和 `config.sub` 不识别 HarmonyOS；1.27 版本补丁将其规范为 `aarch64-unknown-linux-ohos`。
- HarmonyOS 上 `id -u` 可能返回 `bad uid`，适配后跳过该不可用检查并以 best-effort 方式执行检测。
- HMDFS 下 `pwd`/`getcwd` 和 `umask 077` 有兼容性差异，版本补丁提供回退并避免生成所有者不可写的临时目录。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无第三方依赖 | — | 使用 HarmonyOS 系统 shell、clang 与 make；`dmidecode` 为可选探测工具 |

## 功能验证

```bash
virt-what --version
virt-what
```

## 参考

- [上游项目主页](https://people.redhat.com/~rjones/virt-what/)
- [上游 1.27 源码归档](https://people.redhat.com/~rjones/virt-what/files/virt-what-1.27.tar.gz)
