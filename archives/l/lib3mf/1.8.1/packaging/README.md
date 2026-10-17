# lib3mf 1.8.1 packaging

HarmonyOS PC (arm64) 产物打包说明。

- 构建产物：`lib/lib3MF.so.1.8.1.0`（+ SONAME 符号链接 `lib3MF.so.1`、链接名 `lib3MF.so`）、`include/Model`、`include/Common`、`lib/pkgconfig/lib3MF.pc`
- 本地 staging 验证包：`lib3mf-1.8.1-ohos-arm64.tar.gz`（源码仓不提交二进制，仅本地留存供 packaging_present 自检）
- 正式发布：PR 合入 main 后由 CI 流水线 `conan create` + `conan upload` 发布到 cnb.cool 制品仓（`lib3mf/1.8.1@ohpcd/stable`）
- 消费方式：`conan install --requires=lib3mf/1.8.1`（依赖链自动拉取 libzip/1.11.4 + zlib/1.3.1.1）
