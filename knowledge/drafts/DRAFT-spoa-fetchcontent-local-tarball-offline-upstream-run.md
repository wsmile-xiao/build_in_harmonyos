# DRAFT-spoa-fetchcontent-local-tarball-offline-upstream-run

> Contributor: pc5-2 | Status: Draft | Updated: 2026-09-18
> Source: spoa 4.1.5 HarmonyOS PC Path B adaptation (task spoa-4.1.5-r01-pc5-2-20260918T114126Z)
> 对应 KV: knowledge/drafts/DRAFT-spoa-fetchcontent-local-tarball-offline-upstream-run.kv

## 主题 / 触发场景

上游 C/C++ 库（如 spoa）以 `FetchContent`/`ExternalProject` 在 configure 期拉取
**多个**测试依赖（bioparser、biosoup、googletest）源码，而这些依赖在 ohpcd
制品仓**未发布**、worker 又无法直连 github.com（`Failed to connect to
github.com port 443 ... timed out`）时，`FETCHCONTENT_SOURCE_DIR_<NAME>` 指向
**本地解压的官方 tag tarball** 即可不改上游源码、不改配方，完整编译并真实运行
上游测试套件，并产出双口径测试台账。

与既有条目的差异：
- **E342**：主路径为 `BUILD_TESTING=OFF` 放弃网络化上游测试，改跑 test_package；
  本候选**保留并真实运行**完整上游套件。
- **DRAFT-matchit-r01-gtest-ohpcd-offline-run**：matchit 用 ohpcd **已发布**的
  gtest 制品直链替换拉取；本候选的依赖**并未发布**，改用 `FETCHCONTENT_SOURCE_DIR`
  本地官方 tarball 注入，不依赖制品仓发布，且覆盖任意数量的 FetchContent 依赖
  （不限 gtest）。

## 现象 / error_signature

```text
Failed to connect to github.com port 443 after 65590 ms: Couldn't connect to server
fatal: unable to access 'https://github.com/rvaser/bioparser/'
CMake Error at FetchContent.cmake: ... (__FetchContent_doPopulation)
Could NOT find ZLIB (missing: ZLIB_LIBRARY ZLIB_INCLUDE_DIR)
Compatibility with CMake < 3.5 has been removed  (googletest 1.10.0 旧版 CMakeLists)
```

## 根因 / root_cause

上游 CMake 用 FetchContent 拉测试依赖（spoa 的 bioparser 3.1.0 / biosoup 0.11.0 /
googletest 1.10.0）；依赖未发布到制品仓 + GitHub 直连超时，configure 期即失败。
bioparser 的 gz 解析还要求 zlib，需从 OHOS SDK sysroot 供给。

## 方案 / rec_approach

1. 用可达通道下载官方 tag tarball 并解压到本地目录：
   `curl -L 'https://api.github.com/repos/<org>/<repo>/tarball/refs/tags/<tag>'`
   或 `https://codeload.github.com/<org>/<repo>/tar.gz/refs/tags/<tag>`（github.com
   网页直连超时但 api/codeload 可达）。
2. configure 时注入本地目录（必须用 `-D` 传给 CMake，环境变量不生效）：
   `-DFETCHCONTENT_SOURCE_DIR_<NAME>=<本地解压目录>`，每个依赖一个。
3. 依赖自身的系统库依赖（如 zlib）从 OHOS SDK sysroot 提供：
   `-DZLIB_INCLUDE_DIR=<sysroot>/usr/include -DZLIB_LIBRARY=<sysroot>/usr/lib/aarch64-linux-ohos/libz.so`。
4. 旧版依赖（googletest 1.10.0）与 CMake 4.x 策略冲突时加
   `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（细节见 E187）。
5. 构建测试目标并真实运行：`make <test_target> && ./bin/<test_binary>`，记录
   命令、cwd、退出码、日志 SHA-256 与 `--gtest_list_tests` 双口径。

## 验证

spoa 4.1.5：`spoa_test` 完整构建并运行，22/22 通过（源码声明 23 项，1 项在
`SPOA_USE_CEREAL` 互斥分支未实例化），全量通过率 22/23 (95.7%)，可执行集合
22/22 (100%)；命令、cwd、退出码、日志 SHA-256 见
archives/s/spoa/4.1.5/reports/test-report.md。

## 适用边界 / 反例

- 适用：上游 FetchContent 拉取测试依赖、依赖未发布、GitHub 直连受限、不改上游
  源码即可注入的 CMake 项目；可同时注入多个依赖。
- 反例：依赖在制品仓已发布时优先走 Conan 制品直链（DRAFT-matchit…）；不需要运行
  上游套件时走 E342 的 BUILD_TESTING=OFF 更省事；FetchContent 固定 hash 校验
  与本地 tarball 内容不一致时需核对 tag/commit。
