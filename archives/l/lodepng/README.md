# lodepng

## 简介
PNG encoder and decoder in C and C++, without dependencies（Lode Vandevenne，Zlib 许可）。

## OHOS 适配
- 构建系统: custom（上游无 CMake/autotools 安装目标，直接编译单源文件）
- 库本体仅 `lodepng.cpp + lodepng.h`，配方产出 `liblodepng.a/.so + include/lodepng.h`
- 无外部依赖，仅 libc/libc++
- 上游自包含 `lodepng_unittest` 在 `build()` 完整运行，以 stdout 横幅判定通过
- 详见各版本 notes.md 获取适配详情

## 依赖
- 无外部依赖

## 功能验证
- 上游 `lodepng_unittest`（38 个 doMain 测试组）完整运行清单
- Conan 消费者编码 PNG 签名并解码还原像素逐字节一致

## 参考
- https://github.com/lvandeve/lodepng
- https://lodev.org/lodepng/
