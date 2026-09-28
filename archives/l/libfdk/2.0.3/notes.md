# libfdk 2.0.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-26
- 编译器: clang/clang++
- 状态: built（待 HMBS 真机 rule4 门禁验证后由后端提交）
- 分支: feat/libfdk-2.0.3
- 申请人: sheepss
- 队伍: 来都来了

## 上游信息
- 上游仓库: https://github.com/mstorsjo/fdk-aac
- 上游标签: v2.0.3
- 发布包: https://downloads.sourceforge.net/project/opencore-amr/fdk-aac/fdk-aac-2.0.3.tar.gz
- SHA256: 829b6b89eef382409cda6857fd82af84fabb63417b08ede9ea7a553f811cb79e（与 ConanCenter recipes/libfdk_aac 2.0.3 及 FreeBSD ports 校验一致）
- 许可证: FDK-AAC（见源码 NOTICE）
- 依赖: 无外部依赖

## 编译步骤

采用 CMake 构建，关闭示例程序，仅安装库：

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DBUILD_PROGRAMS=OFF -DFDK_AAC_INSTALL_CMAKE_CONFIG_MODULE=ON -DFDK_AAC_INSTALL_PKGCONFIG_MODULE=ON
cmake --build build -j1
cmake --install build
```

配方内等价逻辑见 `conanfile.py` 的 `generate()` 与 `build()`。

## 上游测试盘点

- `test/run-test.sh`: 2 路 ref 对比（Sample01_4.wav stereo 与派生 mono，各经 test-encode-decode 全配置编码后 diff 对应 ref 文件）。
- `test/ref-stereo.txt`、`test/ref-mono.txt`: 参照哈希。
- `test-encode-decode.c`、`wavreader.c`、`sha1.c`: 仅当 `BUILD_PROGRAMS=ON`（CMake）或 `EXAMPLE=1`（autotools）时编译。
- CMake 无 `enable_testing`/`add_test`，Makefile.am 无 `TESTS`/`check_PROGRAMS`，故无 `make check` 与 `ctest -N` 注册用例。
- `run-test.sh` 需 `curl media.xiph.org` 下载 WAV（md5 a5c105544c64ce92c6c5c06d280e6b9c）并用 `ffmpeg` 派生 mono（md5 3bfccac9f2e527ba3ef888874f09a409），密封 CI 无网络夹具与 ffmpeg，无法逐字运行。
- 结论: 上游测试总数 2（stereo + mono），口径 `auto`（单一 shell harness 两路 diff），配方以内存合成方波 PCM 离线镜像同编解码路径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 包名与现有 fdk-aac 重复疑虑 | 仓库已有 `archives/f/fdk-aac/2.0.3`，任务要求新建 `archives/l/libfdk/2.0.3` | 按任务路径新建 libfdk，conan 名与目录一致，cmake 目标仍用上游 `FDK-AAC::fdk-aac`，notes 如实记录同源关系 |
| 2 | 上游测试需联网与 ffmpeg | run-test.sh 硬依赖外部 WAV 与 ffmpeg | test_package 以内存合成 stereo/mono 方波走同 API（AAC-LC 64k，RAW transmux），不做文件与网络 IO |
| 3 | 避免包变为工具包 | BUILD_PROGRAMS=ON 会安装 aac-enc，需 commands.json | 保持 BUILD_PROGRAMS=OFF，测试二进制仅在 test_package 构建，不进安装包 |

## 源码修改

无补丁。

## 依赖版本

无 conan 依赖。构建工具为真机注入的 cmake/make/ninja/python3（HMBS_CMAKE 等）。

## 验证结果

本地 Windows 仅做配方静态检查，未跑 conan（按任务要求不在本机运行 conan，真机验证由 HMBS 后台执行）：

```bash
git rev-parse --verify HEAD
git status --short
```

- `ci/conan/profiles/ohos-aarch64` 存在。
- `HMBS_TEST_PACKAGE_RESULT` 与 `HMBS_UPSTREAM_TEST_RESULT` 均由 test_package 真机 `ctest + test_libfdk` 结束后打印，计数来自 CMakeLists 声明的 4 个 ctest 与 run-test.sh 的 2 路，不做 stdout 字符串数数。
- 真机 evidence（执行数/通过数/日志）待 HMBS 预检回填后写入 PR 正文，本轮不猜测。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方，库名 fdk-aac，cmake 目标 FDK-AAC::fdk-aac |
| conandata.yml | 官方 SourceForge 发布包 URL + SHA256 |
| test_package/test_libfdk.c | encoder/decoder/roundtrip-mono/roundtrip-stereo 四用例真实 API 调用 |
| test_package/CMakeLists.txt | 4 个 ctest 注册 |
| test_package/MANIFEST.yml | 上游 2 路审计 + 消费者 4 用例声明 |
| manifest.yaml | 版本级构建元数据 |
| notes.md | 本文件 |

## 注意事项

- 本包为纯库，不提供 `commands.json`。
- 与 `fdk-aac/2.0.3` 同源，包名不同，按任务要求独立成包。
- 任何配方改动后旧验证即失效，需 HMBS 重新完整预检。
