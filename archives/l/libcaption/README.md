# libcaption

## 简介
libcaption 是用 C 编写的闭路字幕（closed caption）编解码库，实现 CEA-608 / CEA-708 子集，并提供 H.264 SEI NALU 封装工具，MIT 许可。

## OHOS 适配
- CMake 原生构建，纯 C 库，无任何 OS 特定调用，零源码级平台补丁
- 唯一补丁：`cmake_minimum_required(2.8)` → `3.10`（CMake 4.x 兼容，与 NixOS package.nix 一致）
- re2c 可选且默认关闭，上游已提交 `eia608_from_utf8.c.cached`，无需 re2c 工具
- 打包时关闭 `BUILD_EXAMPLES`（13 个 CLI 示例非库产物），仅产出 `libcaption` 库 + `caption/*.h` 头文件

## 依赖
- 无编译依赖
- 无运行时依赖

## 功能验证
```bash
conan create archives/l/libcaption/0.8 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
conan test archives/l/libcaption/0.8/test_package -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 上游测试
- 正式测试：1 项（test_wrap，utf8 行折叠，确定性输入，无媒体依赖）
- eia608_test / test_sei 在上游 CMakeLists.txt 中被注释，非正式测试
- examples/ 13 个 CLI 工具属示例，不计入正式测试

## 参考
- 主页: https://github.com/szatmary/libcaption
- 源码: https://github.com/szatmary/libcaption/archive/refs/tags/v0.8.tar.gz
