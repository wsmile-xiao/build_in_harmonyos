# spfft 1.1.1 — 适配笔记

任务：平台 10846｜档位【中】｜语言 cpp｜构建系统 cmake｜首次适配
上游：https://github.com/eth-cscs/SpFFT tag v1.1.1（github 直连不可达，经 gh-proxy
镜像取源，sha256 675a0481...d766c 与官方 tag archive 一致）

## 1. 构建面

CMake 纯净工程。OHOS 取舍：SPFFT_MPI=OFF（无 MPI 运行时）、SPFFT_OMP=OFF、
CUDA/ROCm 自动关闭（无 GPU）、SPFFT_FFTW_LIB=FFTW + 依赖制品仓 fftw/3.3.10.3
（W0 preflight + conan download 探针确认已发布）。零源码补丁。

## 2. 上游测试面（如实申报：未执行）

上游 tests/ 为 gtest 套件（local_tests/ 6 文件 + mpi_tests 仅 SPFFT_MPI 时注册），
构建经 CMake FetchContent 从 github 拉 googletest v1.5.2/CLI11：
- 构建主机直连 github 不可靠（本轮取源即遇 Empty reply，E299 家族）；
- gtest、CLI11 制品仓未发布（conan download 报 acceleration policy，fftw 对照命中）；
⇒ SPFFT_BUILD_TESTS=OFF，upstream_static=6 / 执行 0 / 未执行 6（原因=网络与
依赖发布面，非代码缺陷）。若后续 gtest/CLI11 发布或网络面修复，改 ON 重跑即可。

## 3. 消费者测试（补偿性真实计算面）

test_package/test_spfft.c：以打包头文件+库执行真实 2x2x2 C2C 往返
（grid/transform 创建 → backward 含缩放 → forward 无缩放 → 频域值精确
等于原值×8，容差 1e-9）——4/4 PASS。证明头文件布局、库导出、FFTW 后端
联动在 OHOS 全部可用。

## 4. B 判定

- **none（理由）**：适配全部落点为上游原生开关（MPI/OMP/CUDA/tests 均有正式
  CMake 选项）与制品仓既有依赖（fftw），无源码补丁、无 OHOS 专属新机制。
  唯一非代码面发现（FetchContent 网络不可达致上游测试未执行）属环境面，
  已如实申报于 test_summary，不足以独立成条。

## 5. CI 取源风险预声明

源 URL 为 github tag archive（CI 镜像改写会自动加 gh-proxy.com 回退，R39）；
sha256 以实测+镜像下载双向核对一致。
---

**编译结束**: 2026-09-25 08:33
**最终状态**: built

## 上游测试补跑（2026-09-26，CIW-8 执行 + CIW-F3 复跑）
FetchContent 网络面曾遮蔽上游测试面；预置 googletest v1.15.2 / CLI11 v2.3.2 /
nlohmann-json v3.11.2 源码（MD5 对齐上游 tests/CMakeLists.txt）+ FETCHCONTENT_SOURCE_DIR_*
断网注入 + 复用 conan toolchain（fftw/3.3.10.3 制品）后，上游 tests/local_tests/ 的
run_local_tests 可完整构建执行：**850 tests / 5 suites 全通过**（CIW-8 13:5x 9.6s；
CIW-F3 16:16 复跑 5.98s，结果一致）。证据：reports/local-tests-run.log + local-tests-run.md。
未修改上游任何测试源码；未改配方与 HEAD 构建产物。
