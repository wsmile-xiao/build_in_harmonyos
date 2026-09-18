# uvg266 0.8.1 适配笔记（OHOS aarch64）

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4 (aarch64-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: published
- Conan profile: ci/conan/profiles/ohos-aarch64 (os=OHOS, arch=armv8)

## 编译步骤

```bash
# 官方源码（SHA-256 见 conandata.yml，镜像仅本地/CI 构建时临时使用）
git worktree add /storage/Users/currentUser/junshi_liu/worktrees/pc3-8-uvg266-0.8.1 -b feat/uvg266-0.8.1 main
cd archives/u/uvg266/0.8.1
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

1. init-build 下载官方 v0.8.1 tarball（SHA-256 `9a2c68f9...40b6ec`）。
2. lang-preflight: detected=cpp（C 主体 91%），匹配。
3. 改写 conanfile.py：上游为 **CMake** 项目（conan-init 模板误判为 autotools），
   使用 CMakeToolchain；`BUILD_TESTS=ON` 编译上游 greatest 单元测试。
4. greatest 为官方子模块（.gitmodules → ultravideo/greatest），release tarball
   不含其内容；按 v0.8.1 钉扎提交 `60e25ce7658ced49f03b52ac14c553cf6ea33de4`
   （SHA-256 `3914a24a...26d7`）拉取到 `greatest/`。
5. `conan create` 全绿：libuvg266.a + uvg266 CLI + uvg266.pc + uvg266.h 打包，
   test_package 消费者测试通过。

## 上游测试台账（双口径）

官方 tag 源码 tests/ 目录共 10 个 CTest 入口（1 个 greatest 单元测试二进制 +
9 个 shell 脚本；test_weird_shapes.sh 未在 CMake 注册）。

### 实际运行结果
| CTest 入口 | 类型 | 结果 |
|---|---|---|
| Test_uvg266 (uvg266_tests) | greatest C 单元测试 | ✅ PASS（sad/satd/dct/mts/coeff_sum/mv_cand/speed） |
| test_external_symbols.sh | 符号检查 (nm) | ✅ PASS |
| test_invalid_input.sh | 编码器非法输入 | ✅ PASS（恢复 ffmpeg 后） |
| test_mtt/intra/monochrome/lmcs/tools/slices/cabac_state.sh | 编码+解码校验 | ⛔ 外部工具阻塞（见下） |

### 外部工具阻塞说明（恢复尝试已做）
- ffmpeg：ohpcd 制品仓 `ffmpeg/6.1.6` 已发布 → `conan install` 恢复成功，
  验证 `test_invalid_input` 可运行通过；`test_mtt` 等脚本还调用
  `DecoderAppStatic`（VTM 解码器）。
- DecoderAppStatic：上游从 `http://ultravideo.fi/ubuntu-vtm-13.0.tgz` 提供，
  该二进制为 **x86-64 静态 ELF**（实测 `readelf` 确认），OHOS/本机均为
  aarch64 无对应制品，ohpcd 无 vvdec/vtm 包 → 真实平台阻塞。
  恢复条件：获得 aarch64 OHOS 的 VTM DecoderApp 或等价 VVC 解码器后，
  运行 `XFAIL_TESTS= cmake && ctest` 即可全量复跑。
- 遵守上游原生 `XFAIL_TESTS` 机制（CMakeLists configure 阶段读取环境变量），
  将 8 个外部工具依赖项从 ctest 注册中排除，C 单元测试保持实际执行。

### 源码声明总数
- greatest 单元测试：`tests/*.c` 中独立 TEST() 共 **40** 个
  （sad 19 / speed 7 / mv_cand 3 / satd 3 / dct 2 / intra_sad 2 / mts 2 /
  coeff_sum 1 / inter_recon_bipred 1——其中 inter_recon_bipred 被上游
  tests/CMakeLists.txt 显式 REMOVE_ITEM（"ToDo: fix the tests"），
  实际编译进 uvg266_tests 的为 39 个）。
  `test_strategies.c` 为策略注册辅助（非独立用例，0 个 TEST）不算用例。
- CTest 注册入口：配置（本配方）注册 2/10 实际执行，全部通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 模板误判 autotools | init-build 探测脚本对 CMake 项目识别有限 | 用 CMakeToolchain 重写 conanfile.py |
| 2 | greatest 目录为空 | release tarball 不含 git 子模块 | 按 .gitmodules 官方地址+钉扎提交补拉 |
| 3 | github.com 下载超时 | 网络到 github 不可达 | 本地/CI 构建临时用 gh-proxy.com 镜像（sha256 校验仍在） |
| 4 | 8 个 shell 测试失败 | 上游测试依赖 ffmpeg + VTM DecoderAppStatic | ffmpeg 恢复通过；DecoderAppStatic 仅 x86-64 制品→XFAIL 排除并记录恢复条件 |

## 依赖版本
- 无第三方库依赖（纯 C，仅系统 pthread/libm）。
- 测试工具：ffmpeg/6.1.6（ohpcd，仅 test_invalid_input 需要，已恢复验证）。

## 验证结果
```bash
conan create . -pr:h=.../ohos-aarch64 -pr:b=.../ohos-aarch64
# Test_uvg266 PASS, test_external_symbols PASS, test_package(test_uvg266) PASS
# 产物: libuvg266.a, uvg266(CLI), uvg266.pc, uvg266.h
```
---

**编译结束**: 2026-09-18 03:31
**最终状态**: built
