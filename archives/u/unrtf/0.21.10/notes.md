# unrtf 0.21.10 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
python3 scripts/ohc-run.py init-build unrtf 0.21.10 --url=https://ftp.gnu.org/gnu/unrtf/unrtf-0.21.10.tar.gz
conan create archives/u/unrtf/0.21.10 --profile:host=ci/conan/profiles/ohos-aarch64 --profile:build=default --build=missing
```

Conan 配方执行：

```bash
./configure --prefix=<package_folder> --datarootdir=${prefix}/share
make -j1
make install -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config/config.guess: unable to guess system type` | 上游 2017 版 config.guess 不识别 HarmonyOS | 在 Conan 配方中构建前补充 HarmonyOS 分支，映射到 `*-linux-ohos` |
| 2 | `config.sub ... linux-ohos failed` | 上游 config.sub 不接受 `linux-ohos` | 在 Conan 配方中构建前补充 `linux-ohos*` |
| 3 | `make: jobserver mkfifo ... Operation not permitted` | HarmonyOS/HMDFS 环境限制 FIFO | 构建和安装使用 `-j1` |

## 源码修改

存在 1 个持久化补丁 `patches/0001-ohos-autotools-config.patch`，通过 `conandata.yml` 声明并由 `apply_conandata_patches(self)` 应用；该补丁仅修改 `config/config.guess`、`config/config.sub`，用于支持 HarmonyOS/linux-ohos。

另有 1 个构建时兼容修补：`conanfile.py` 在执行 `configure` 前将 `configure` 中创建 `confXXXXXX`/`$tmp` 临时目录的 `umask 077` 调整为 `umask 022`，用于修复 HMDFS 下 `config.status` 临时目录权限问题，避免将 autoconf 生成文件修改纳入持久化 patch。

## 依赖版本

无外部 Conan 依赖。

## 验证结果

```bash
unrtf --version
unrtf --text sample.rtf
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 官方 GNU 源码 URL 与 sha256 |
| test_package/conanfile.py | L1 smoke test |
| test_package/MANIFEST.yml | 测试清单 |
| commands.json | 命令行工具声明 |
---

**编译结束**: 2026-07-15 00:45
**最终状态**: built
