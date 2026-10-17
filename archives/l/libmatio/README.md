# matio

> MATLAB MAT 文件 I/O 库：读取和写入 MAT v4 / v5 / v7.3（HDF5）格式，支持压缩。

## 简介

matio 是一个 C 库，用于读写 MATLAB 的 MAT 文件格式。它支持：
- MAT Level 4（基础数值矩阵）
- MAT Level 5（结构体、元胞数组、稀疏矩阵、压缩存储）
- MAT Level 7.3（基于 HDF5 的 v7.3 文件，含压缩）
- 稀疏矩阵、复数数据、多维数组等全部数据类型

上游同时提供 autotools 与 CMake 双构建入口（等价）。本仓库采用 CMake 入口（与 hdf5/netcdf 同路线，依赖经 CMakeDeps 接线）。

## OHOS 适配要点

- `os=OHOS` 时须显式设 `CMAKE_SYSTEM_NAME=OHOS` + `CMAKE_SYSTEM_PROCESSOR=aarch64`，否则 cmake 找不到 `Platform/HarmonyOS.cmake`，产物无 `DT_SONAME` 并传染下游。
- 上游测试套件（3338 个 autotest 用例 → 8197 个 ctest 条目）在 build 阶段经 `test/convert_at_to_ctest.py` 转成 ctest 跑，需 Python3 解释器（OHOS 上 `/data/service/hnp/bin/python3`）；链式用例（_1→_N）有顺序依赖，须完整顺序跑。
- 补丁 0001（conan）：thirdParties.cmake 新增 Conan 2 CMakeDeps 的 hdf5::hdf5 目标分支（上游目标级联只认 hdf5::hdf5-shared/-static 与 HDF5::HDF5）。
- 补丁 0002（portability）：src/mat.c Mat_mktemp 模板缓冲区按硬编码 /tmp 21 字节计算 → TMPDIR 优先解析 + PATH_MAX 缓冲区（OHOS /tmp 只读，长 TMPDIR 必截断/回退失败）。修复前 391/8197 个 ctest 条目（readwrite_delete_variables 链）失败，修复后 8197/8197 ctest 条目全过。
- 产物含 `matdump` 命令行工具（`bin/`），按 R38 登记于软件级 `commands.json`，且 bin/ 下 ELF 须代码签名（binary-sign-tool 经 shutil.which 解析，兼容 CI 与本机安装路径）。

## 排除与替代

不单独提供 `matio` 命令——工具名是 `matdump`（用于在终端 dump MAT 文件内容）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| hdf5 | 1.14.6 | MAT v7.3（HDF5）支持必需 |
| zlib | 1.3.1.1 | MAT v5/v7.3 压缩存储必需 |
| libaec | 1.1.7 | hdf5 传递依赖（SZIP） |

## 功能验证

```bash
# 消费方视角（test_package，CMakeDeps 找包）：
conan create archives/l/libmatio/1.5.30 --profile:build default --profile:host ohos-aarch64-device --build=libmatio/1.5.30
# 上游官方测试（3338 个 AT_SETUP 用例 / 5389 AT_CHECK 断言 → 转换器展开为 8197 个 ctest 执行条目）在 conan create 的 build 阶段自动执行。
# test_package（1 个测试用例）：100 运行时断言（v4/v5 未压缩/v5 压缩/v7.3 未压缩/v7.3 压缩 5 组回环 × 16 + 错误输入 6 + 长 TMPDIR 删除回归 14）。
# 适配后测试用例总数：3339（3338 上游用例 + 1 个 test_package 用例）。

# 命令行验证：
matdump somefile.mat
```

## 参考
- [官方文档](https://github.com/tbeu/matio/wiki)
- [源码仓库](https://github.com/tbeu/matio)
- [1.5.30 Release](https://github.com/tbeu/matio/releases/tag/v1.5.30)
