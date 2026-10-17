# glibmm 2.66.7.1 适配笔记

## 构建配置

- 构建系统：Conan 2 + Meson
- 源码：GNOME 官方 `glibmm-2.66.7.tar.xz`
- 依赖：`glib/2.84.0.1`、`libsigc/2.10.8`
- 组件：`glibmm-2.4`、`giomm-2.4`
- 默认构建 shared 库

官方 release tarball 包含预生成绑定，以 `maintainer-mode=false` 构建，不要求
`mm-common` 或 `gmmproc`。为覆盖完全缺少 Meson 的 CI Worker，配方下载并校验
官方 PyPI `meson-1.9.1` 纯 Python wheel，在源码目录解包后通过临时 wrapper
显式调用，不依赖 Worker 的全局 `PATH`。安装 shared ELF 后执行 OHOS 重签；
缺少签名工具的交叉 SDK 环境会跳过该步骤。

## 测试

`build()` 调用真实上游 `meson.test()`。交叉构建时目标 ELF 无法在构建机执行，
因此只在可运行目标程序时执行。OHOS 原生测试命令排除 `failing` suite：

```text
meson test -v -C <build-folder> --timeout-multiplier=16 --no-rebuild --no-suite=failing
```

补丁只将需要外部网络的 `giomm_tls_client_test` 在 HarmonyOS 上标记为
`failing` suite；该测试是排除项，不计为通过。

真实测试结果：Meson 发现 34 个上游测试程序，实际执行 33 个并通过 33/33，
失败 0；`giomm_tls_client_test` 排除 1 项。Conan 消费者测试编译、链接并运行
打包后的 `glibmm-2.4`/`giomm-2.4`，9/9 断言通过。详见
`reports/test-report.md`。
---

**编译结束**: 2026-08-17 17:38
**最终状态**: built
