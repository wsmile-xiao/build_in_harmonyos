# cllayerinfo

OpenCL **ICD Loader** 项目（[OCL-dev/ocl-icd](https://github.com/OCL-dev/ocl-icd)）随源码
一起构建的命令行诊断工具。它初始化 loader 的 layer 链后，用 `clGetLayerInfo` 逐个打印每个
层的 API 版本与名字，用于排查 OpenCL 层（`OPENCL_LAYERS` / `OPENCL_LAYER_PATH`）是否被
正确加载、层与 loader 的接口版本是否匹配。

## 功能概述

- 初始化 ICD loader 的 layer 链（读 `OPENCL_LAYERS` 显式列表与 `OPENCL_LAYER_PATH` 目录）
- 对每个成功加载的层打印：
  - `CL_LAYER_API_VERSION`（层实现的接口版本，当前为 100）
  - `CL_LAYER_NAME`（层自报的名字）
- 层加载失败时通过 loader 的 debug 输出（`OCL_ICD_DEBUG`）给出原因，工具本身仍正常退出

## OHOS 适配

- 本包交付 `bin/cllayerinfo`；loader 源码被直接编进该二进制
  （上游 `Makefile.am`：`cllayerinfo_SOURCES = cllayerinfo.c $(libOpenCL_la_SOURCES)`），
  因此运行时**不依赖** `libOpenCL.so`，无需额外运行时依赖
- `libOpenCL.so`、OpenCL 头文件与 `.pc` 由 `archives/o/ocl-icd` 交付，本包安装后清理，
  避免两个包各自持有同一 SONAME
- 上游 GitHub tag 归档不含 `configure`，配方在构建期 `autoreconf` 自举，并显式钉住
  `--build/--host=aarch64-unknown-linux-ohos`（上游自带 `config.guess` 不识别 HarmonyOS）
- 上游测试 `make check`（autotest 套件）在 `build()` 内真实执行，实测计数见版本目录
  `notes.md` 与 `test_package/MANIFEST.yml`

## 依赖关系

- 编译依赖：无第三方运行时依赖（仅 libc/pthread）；构建工具 `automake/1.18`、`libtool/2.5.4.1`
  经 conan `tool_requires` 提供；生成 dispatch 表需要系统 `ruby`
- 运行依赖：无

## 参考资料

- 上游仓库：https://github.com/OCL-dev/ocl-icd
- 版本目录：`archives/c/cllayerinfo/2.3.3/`
