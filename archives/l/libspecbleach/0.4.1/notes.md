# libspecbleach 0.4.1 适配笔记

## 编译环境
- 构建系统: cmake（CMakeLists.txt project VERSION 0.4.1 LANGUAGES C，C 标准 17）
- 编译日期: 2026-09-28
- 编译器: clang/clang++ 15.0.4
- 状态: built（conan-verify G0-G4+L2/L4/L5 全 PASS，W3 本地 CI 隔离复验后通过）

## 编译步骤
```bash
# 源码获取（GitHub 直连超时，codeload 直链可用）
curl -o libspecbleach-0.4.1.tar.gz \
  https://codeload.github.com/lucianodato/libspecbleach/tar.gz/refs/tags/v0.4.1
# sha256=76ae2cbf43397dc7f4f646a28d75a83ab3786211fb2daf8167dcf97de58568bd

# CMake 配置（含测试与 extras；AVX 仅 x86_64，arm64 关闭）
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DENABLE_TESTS=ON \
      -DENABLE_EXAMPLES=ON -DENABLE_AVX=OFF -DSPECBLEACH_BUILD_EXTRAS=ON ..
cmake --build . -j$(nproc)
# libsndfile 恢复后：PKG_CONFIG_PATH=$HOME/tmp/pkgfix（修复副本）重配，ctest 41/41
ctest --output-on-failure -j$(nproc)

# Conan 配方验证（配方内集成上游 CTest 39/39）
conan create archives/l/libspecbleach/0.4.1 -pr:h=ci/conan/profiles/ohos-aarch64 \
        -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 github.com 超时 | 执行端到 github.com 网络受限 | codeload.github.com 直链下载（E569 覆盖） |
| 2 | curl 写 /tmp 失败 (exit 23) | /tmp 只读/不可写（E002） | 改用 $HOME/tmp |
| 3 | sndfile.pc 指向失效缓存路径，CMake "Imported target includes non-existent path" | conan 预编译包 .pc 内嵌构建机缓存绝对路径 | sed 修复副本 + PKG_CONFIG_PATH 重定向（C1 知识候选） |
| 4 | W3 JC1/JC5 命中 cloog/kics 基线状态文件 | junk_check full 整仓扫描 | git rm --cached 隔离→复跑→git add -f 恢复，SHA 一致（复用 DRAFT-fastnoiselite） |
| 5 | test_package 初版使用旧 API SpecBleachHandle | v0.4.1 API 已重构为 specbleach_denoiser_* | 按公开头 specbleach_denoiser.h 重写消费者测试 |

## 源码修改
无（纯配方/测试适配，未改上游源码，patches=0）

## 依赖版本
- libsndfile/1.2.2（仅测试门控，预编译包 21b17f8b，os=OHOS/6.0/armv8/clang15/libc++17）
- 运行时依赖：libc（系统）、-lm（私有）
- vendored: thirdparty/pffft（源码内置）

## 验证结果
- 上游测试双口径：source_declared_total=41，configured_executable_total=41（配方内 39 + libsndfile 门控 2），executed_passed_total=41/41 (100%)，failed=0，uninstantiated=0
- 配方内可复现口径：39/39（conan create 日志，sndfile 未找到时 2 门控入口不实例化）
- 鸿蒙专项 test_ohos/run_ohos_test.sh：T1-T4 全 PASS（产物结构/aarch64 ELF/路径泄漏/API 运行时）
- 消费者 test_package/test.c：conan create 内运行 PASS（latency=4056）
- 关键日志 SHA-256：config=2672f30cb331889af124368b1d623161f9d1fb6220a113eb2dfdf193e00d65f7 build=22ea9ba526ee883c30c1fd35cf931786599718d3647a0cc1a3bb1683c147348f ctest=35636bd3c37c3fd12434ce553d4bd54b49b3ae464507587ed3127402a09b3575

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml | CMake 配方 + 官方源 URL/sha256 |
| test_package/ | 消费者测试（test.c + conanfile.py + CMakeLists + MANIFEST.yml） |
| test_ohos/run_ohos_test.sh | HarmonyOS 专项验证（T1-T4） |
| reports/test-report.md | 测试报告与基线隔离复验 |
| reports/path-b-candidate.md | 知识候选台账与七轴查重 |
| knowledge/drafts/DRAFT-libspecbleach-0.4.1-conan-prebuild-pc-stale-cache-path.{kv,md} | 路径 B 知识草稿 |

## 上游测试双口径台账（R51 申报）
- source_declared_total: 41（tests/ 下 40 个 .c + 1 个 .cpp，官方 v0.4.1 tag 可复制枚举）
- configured_executable_total: 41 = 39（CMake 注册，含 stereo/cpp_smoke）+ 2（libsndfile 门控 test_audio_file_regression、test_integration_realworld_quality，依赖恢复后实例化）
- executed_passed_total: 41/41 (100%)，failed=0，uninstantiated=0
- 配方内可复现口径：39/39 (100%)（conan create 日志可见；sndfile 未找到时 2 门控入口不注册）
- 带外恢复口径：41/41（$HOME/tmp/pkgfix 修复 sndfile.pc 后重配 ctest，日志 SHA 见上）
- 每项映射：tests/test_*.c → CMake 宏 add_specbleach_test/test_name → add_executable(test_name) → add_test(ctest 注册) → 实际二进制执行日志
- 注册名别名：test_martin←test_martin_noise_estimator.c、test_brandt←test_brandt_noise_estimator.c、test_spp_mmse←test_spp_mmse_noise_estimator.c；test_bm3d_filter←test_bm3d_filter.c 同名
- 依赖恢复：libsndfile/1.2.2（ohpcd 预编译包 21b17f8b，os=OHOS/6.0/armv8/clang15/libc++17）conan install 下载后修复 sndfile.pc 无效路径，PKG_CONFIG_PATH=$HOME/tmp/pkgfix 重新 configure 实例化两个原跳过入口；test_audio_file_regression PASS、test_integration_realworld_quality PASS

**编译结束**: 2026-09-28 11:44
**最终状态**: built

## 知识候选台账与查重（Path B 判定，详见 reports/path-b-candidate.md）
- C1 conan 预编译包 .pc 失效路径 → new_draft：knowledge/drafts/DRAFT-libspecbleach-0.4.1-conan-prebuild-pc-stale-cache-path.{kv,md}
- C2 W3 junk_check full 命中基线 → reuse_existing（DRAFT-fastnoiselite-1.1.1-jc-full-mode-baseline-junk-isolation 完整重复）
- C3 codeload 直链 + /tmp 陷阱 → reuse_existing（DRAFT-E569 + E002 覆盖）
- 决定: path B（C1 new_draft），PR 携带 .kv/.md 草稿对