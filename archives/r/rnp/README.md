# RNP

## 简介

RNP 是高性能 C++ OpenPGP（RFC4880）工具集，含 `librnp` 开发库与 `rnp`/`rnpkeys` 命令行，为 Mozilla Thunderbird 所用。

## OHOS 适配

- CMake 构建，加密后端选 Botan3（`CRYPTO_BACKEND=botan3`），复用仓库 `botan3/3.12.0`
- 依赖 `json-c/0.18`、`bzip2/1.0.8`、`zlib/1.3.1`；测试期用 `gtest/1.17.0`，关闭上游 `DOWNLOAD_GTEST` 在线拉取
- `build()` 内运行 `ctest --output-on-failure` 并按 `ctest -N` 与 `LastTest.log` 计数上报
- 同时产出库与命令行工具，软件级已声明 `commands.json`

## 依赖

- botan3 3.12.0
- json-c 0.18
- bzip2 1.0.8
- zlib 1.3.1

## 功能验证

```bash
rnp --version
rnpkeys --version
```

## 参考

- 官网：https://www.rnpgp.org/
- 上游仓库：https://github.com/rnpgp/rnp
- 版本发布页：https://github.com/rnpgp/rnp/releases/tag/v0.18.1
