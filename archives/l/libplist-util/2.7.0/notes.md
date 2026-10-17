# libplist-util 2.7.0 HarmonyOS 适配记录

## 来源与依赖

- 上游项目：https://github.com/libimobiledevice/libplist
- 源码地址：https://github.com/libimobiledevice/libplist/releases/download/2.7.0/libplist-2.7.0.tar.bz2
- SHA256：`7ac42301e896b1ebe3c654634780c82baa7cb70df8554e683ff89f7c2643eb8b`
- Conan 第三方依赖：无。`plistutil` 与 libplist 内部对象在同一个 Autotools 源码包中构建。

官方发布物名称是 `libplist`，其中包含 `plistutil`；本归档将该命令行工具拆分为 Conan 工具包 `libplist-util/2.7.0`。

## 构建适配

- 构建系统：Autotools。
- `settings.os` 仅接受 `Linux` 和 `OHOS`。
- 使用 `--without-cython`、`--with-tools`、`--with-tests`。
- 使用 `--enable-static --disable-shared`，确保工具在不携带 libplist 库文件时仍可执行。
- HarmonyOS 使用 `--build=aarch64-unknown-linux-gnu` 绕过 `config.guess` 识别缺口。
- HarmonyOS 在 build folder 中生成私有 `.hmos_fix/mktemp` 包装器，使 Autoconf 在 HMDFS 上使用 mkdir 回退路径。
- `package()` 删除上游安装的 `include/` 和 `lib/`，仅保留 `bin/plistutil`、`share/man/man1/plistutil.1` 和许可证。

## 上游测试清点

上游 `test/Makefile.am` 注册 41 个 `.test` 脚本和 7 个辅助测试程序，统一入口为 `make check`。Linux WSL Conan 构建已实际运行 `make -j1 check`，结果为 41/41 通过、0 跳过、0 失败、0 错误。

## 消费者测试

1. `test.c`：执行 `plistutil --version`，验证 XML→JSON 和 JSON→XML 转换，并检查关键值和键在往返过程中保留。
2. `test_ohos.c`：仅允许在定义 `__OHOS__` 的目标上编译，在 `/data/local/tmp` 或 `TMPDIR` 创建 plist 文件，实际执行打包的 `plistutil` 并检查输出。

## 验证结果

- Conan 2.29.1 / WSL Ubuntu / `wsl-build`：Autotools 构建、上游 41/41 和 Linux test_package 已通过。
- HarmonyOS 6.0 `hdc`：已连接 `127.0.0.1:5555` 的 x86_64 VM；使用 OpenHarmony SDK 26.0.0 clang 15.0.4、`x86_64-linux-ohos` target 和 sysroot 交叉编译 `plistutil` 及 `test_ohos`，推送至 `/data/local/tmp` 后实测：`plistutil --version` 输出 `plistutil 2.7.0`，`test_ohos` 输出 `PASS: HarmonyOS plistutil temp-file conversion test`。
- 仓库完整 CI：Windows 和 WSL 均已运行 `python -X utf8 tests/run_all.py`；除既有 `test_v1220.py`（测试夹具固定 Git 路径不存在）和 `test_v1221.py`（仓库基线缺少 headeronly/copy catalog 条目）外，其余套件通过。两项失败均未触及本包文件；包级 `prescan`、W0、Conan verify 和元数据校验均通过。
