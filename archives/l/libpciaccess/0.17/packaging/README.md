# Packaging

本版本通过 Conan 配方构建和分发，不在源码仓中提交二进制压缩包。

发布产物由合并后的 CI release 流水线根据 `conanfile.py`、`conandata.yml`、`test_package/` 和 `patches/` 生成并上传至制品仓。
