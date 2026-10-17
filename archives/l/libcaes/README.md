# libcaes

libcaes 是跨平台 AES 加密的 C 函数库（libyal 家族），提供上下文与 Tweak 上下文管理、ECB/CBC/CCM/XTS 加解密接口。

## OHOS 适配

- 构建系统为 GNU Autotools，采用上游 `make dist` 产物（自带 configure、Makefile.in、ltmain.sh 与 libcerror 子树），开箱即用，无需 synclibs 自举与 autoreconf。
- `config.guess` 增加 HarmonyOS 检测分支、`config.sub` 增加 ohos 模式（E007）。
- `configure`/`config.status` 内 `umask 077` 改为 `022`，兼容 HMDFS 文件系统（E011）。
- 安装期使用 cp/mkdir shim 与 chmod 容错，兼容真机文件系统能力。
- 静态构建（`--enable-static --disable-shared`），关闭 Python 绑定与 NLS，无外部 Conan 依赖。
- 上游测试为 `make check` 注册的 7 个 `caes_test_*` 单元程序，配方构建期全量直接执行。

## 依赖

无外部依赖。源码包内含 libyal 子库 libcerror（随包编译为 noinst 静态库，不对外传递）。

## 参考

- 上游仓库: https://github.com/libyal/libcaes
- 20251121 发布页: https://github.com/libyal/libcaes/releases/tag/20251121
