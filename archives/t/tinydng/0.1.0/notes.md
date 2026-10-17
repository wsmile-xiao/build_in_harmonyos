# tinydng 0.1.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt 仅构建测试入口 test_dng_loader；库本体 header-only 无需构建）
- 编译日期: 2026-09-05
- 编译器: clang/clang++（OHOS aarch64）
- 状态: built

## 软件形态

tinydng 0.1.0 是 header-only C++11 库：

- `tiny_dng_loader.h`（DNG/TIFF 加载，`TINY_DNG_LOADER_IMPLEMENTATION`）
- `tiny_dng_writer.h`（DNG/TIFF 写入，`TINY_DNG_WRITER_IMPLEMENTATION`）
- 依赖的第三方单头文件随源码分发：`stb_image.h`（loader 内部 JPEG 解码）、
  `miniz.h`/`miniz.c`（仅当定义 `TINY_DNG_LOADER_ENABLE_ZIP` 时被包含，用于 ZIP 压缩瓦片）

无外部依赖（`requires()` 为空）。配方以 `package_type = "header-library"` 打包上述
5 个文件到 `include/`，并额外打包 `miniz.c` 供消费方启用 ZIP 瓦片支持。

## 编译步骤

1. `conan create`（配方 `source()` 从官方 tag tarball 拉取，SHA256 校验）。
2. `build()`：用上游 CMakeLists 构建 `test_dng_loader`（上游唯一无外部依赖的测试入口），
   以源码树自带的 `colorchart.dng` 为输入真实运行，校验输出无 `Fail to load` 且含
   `width =` 元数据（日志存 `upstream-test_dng_loader.log`）。
3. `test_package/`：消费者测试 `test_tinydng.cpp`，tinydngwriter 写 16x16 RGB16 DNG
   → tinydng loader 读回，断言尺寸/位深/采样格式/像素字节逐位一致（22 处 CHECK）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `lang-preflight` 将任务误判为 python 并自动写 env_unsupported 终态 | 判定器把根目录 `setup.py`/`pyproject.toml`（pybind11 可选绑定，CMake 选项 `TINYDNG_WITH_PYTHON` 默认 Off）置于 CMakeLists 之前 | 保留证据（detected_language=python、源码统计 cpp:18+c:7 占 81%、CMake project(test_dng_loader CXX)），按 R47"辅助脚本不算主体"以主构建系统 CMake 为准继续 cpp 适配；任务实际完成构建与测试 |

## 源码修改

无补丁、无源码修改（header-only 库，上游源码原样打包）。

## 依赖版本

无外部依赖。

## 验证结果

```bash
# 上游测试入口（设备原生运行，exploration 阶段即验证）
$ clang++ -o test_dng_loader -O1 -std=c++11 test_loader.cc && ./test_dng_loader colorchart.dng
width = 1888 ... （45 行元数据，exit 0）

# 配方验证
$ python3 scripts/ohc-run.py conan-verify tinydng 0.1.0
# （结果见 reports/ 与 .ci-result.json）
```

## 注意事项

- 消费方如需 ZIP 压缩瓦片：需同时编译包内 `miniz.c`（或链系统 zlib 并定义
  `TINY_DNG_LOADER_USE_SYSTEM_ZLIB`），并定义 `TINY_DNG_LOADER_ENABLE_ZIP`。
- `test_dng_loader` 无断言且 `exit` 恒 0（上游实现如此），不能以退出码作为通过依据；
  行为验证依赖 test_package 的回环断言测试。
- 上游 `tests/byteorder/main.cc` 是依赖 libtiff 的实验工具（独立 Makefile，未接入
  CMake/构建体系），本次未执行，不属于上游自动化测试套件。
---

**编译结束**: 2026-09-05 14:27
**最终状态**: built
