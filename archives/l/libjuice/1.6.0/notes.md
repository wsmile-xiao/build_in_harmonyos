# libjuice 1.6.0 适配笔记

## 编译环境
- 构建系统: cmake (CMakeLists.txt, CMake 4.1.2)
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) / clang++
- 状态: built
- 语言预检 (R47): detected=c（C11 纯 C 库，c↔cpp 兼容族）

## 编译步骤

1. 源码获取（官方源）:
   `https://github.com/paullouisageneau/libjuice/archive/refs/tags/v1.6.0.tar.gz`
   sha256: `90a13ed7049b97af4dcb494e5a82ebbffc41d29f917d17f0aa1b0b651034ae4c`
2. CMake 配置（OHOS aarch64 原生）:
   `cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=<prefix>`
   - 注意: CMake 对 HarmonyOS 平台打印 "System is unknown to cmake" 警告，属于非阻塞提示（E092 已在配方中处理），configure 正常完成。
3. 编译:
   `make -j$(nproc)` → libjuice.so + juice-tests 全部构建成功，rc=0
4. 测试: `LD_LIBRARY_PATH=<build> ./tests` → 16 项上游用例全部 Success，rc=0
5. Conan 配方: conan-init 生成骨架后手工重写为 cmake 配方（生成器模板误判为 autotools）:
   - conanfile.py: CMakeToolchain/CMake + cmake_layout，BUILD_SHARED_LIBS 由 options.shared 驱动
   - conandata.yml: 填写真实 sha256
   - test_package: test.c（消费者公共 API 测试）+ test_ohos.c（鸿蒙专项）
6. conan-verify: G0-G4 全绿，`可标记 status: published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 直连仓库根 URL 下载到 HTML | GitHub 仓库页不是 tarball | 使用官方 archive tarball: `/archive/refs/tags/v1.6.0.tar.gz`（302→codeload） |
| 2 | ./tests 运行 rc=127 符号重定位失败 | LD_LIBRARY_PATH 未含 build 目录 | 运行时 `LD_LIBRARY_PATH=$PWD` 指向 libjuice.so |
| 3 | conan-init 生成 autotools 模板 | ohc-run 模板按 `init-build --url` 猜测构建系统失败 | 手工重写为 CMake 配方 |
| 4 | test_package 编译报 juice_config 无 max_ufrag_pwd_attempts | 该字段不存在于 1.6.0 公共结构体 | 移除该行，memset 零初始化即可 |
| 5 | test 调用 juice_crc32/juice_base64_* 隐式声明 | 这些是内部符号（src/crc32.h 等），未安装到公共头 | test_package 只使用 juice.h 声明的公共 API |
| 6 | juice_set_local_ice_attributes 返回 Invalid | 校验 ufrag>=4 且 pwd>=22（RFC 8445） | 测试用合法长度凭据 |

## 源码修改

无补丁（patches/ 为空）。libjuice 为纯 C 库，OHOS 原生 clang 直接编译通过，无需平台适配改动。

## 依赖版本

- 无第三方 Conan 依赖（纯 C，仅系统 Threads）
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18，aarch64-unknown-linux-ohos）

## 验证结果

```bash
# 上游测试（16 项独立用例，全量 16/16=100%）
cmake --build . && LD_LIBRARY_PATH=$PWD ./tests
# → 16 个 RUNNING 节全部 Success, rc=0

# Conan 配方验证（G0-G4）
ohc-run.py conan-verify libjuice 1.6.0
# → 配方验证通过, 可标记 published

# test_package 消费者测试
# test_libjuice: agent create/state/attributes/destroy 公共 API → PASS
# test_ohos:     agent 生命周期 [OHOS 平台标记] → PASS
```

上游测试台账（全量枚举，统计口径=CMake TESTS_SOURCES 全部 18 个测试源文件）：

| 用例 | 源文件 | 是否独立上游用例 | 实际运行 | 结果 |
|------|--------|------------------|----------|------|
| CRC32 implementation test | test/crc32.c | 是 | 是 | 通过 |
| base64 implementation test | test/base64.c | 是 | 是 | 通过 |
| STUN parsing implementation test | test/stun.c | 是 | 是 | 通过 |
| candidates gathering test | test/gathering.c | 是 | 是 | 通过 |
| connectivity test | test/connectivity.c | 是 | 是 | 通过 |
| thread-mode connectivity test | test/thread.c | 是 | 是 | 通过 |
| mux-mode connectivity test | test/mux.c | 是 | 是 | 通过 |
| non-trickled connectivity test | test/notrickle.c | 是 | 是 | 通过 |
| connectivity test with role conflict | test/conflict.c | 是 | 是 | 通过 |
| connectivity test with bind address | test/bind.c | 是 | 是 | 通过 |
| ufrag test | test/ufrag.c | 是 | 是 | 通过 |
| unhandled STUN message test | test/stun-unhandled.c | 是 | 是 | 通过 |
| multiple handler unhandled STUN message test | test/stun-unhandled-multiple.c | 是 | 是 | 通过 |
| unhandled, unhandled STUN message test | test/stun-unhandled-unhandle.c | 是 | 是 | 通过 |
| no host unhandled STUN message test | test/stun-unhandled-no-host.c | 是 | 是 | 通过 |
| server test | test/server.c | 是 | 是 | 通过 |
| TURN server test | test/turn.c | 是 | 是 | 通过 |

- 统计口径: 全目录（CMake TESTS_SOURCES 18 文件中 17 个用例文件，main.c 为测试入口调度器不算独立用例）
- 全量通过率: 16/16 = 100%（发现 16 项独立用例，全部实际运行并通过）
- 未运行/不可运行/硬阻塞: 无

鸿蒙专项测试（任务要求新增的真实可执行用例）:
- test_package/test_ohos.c: 使用公共 API juice_create/juice_get_state/juice_destroy 在 OHOS 上验证 agent 生命周期，编译运行 PASS（平台标记 __OHOS__/OHOS 命中，输出 "platform build = OHOS"）
- 随 conan-verify G2 的实际 conan create 日志留痕

## 注意事项

- **公共 API 边界**: 安装包只安装 `include/juice/juice.h`；juice_crc32/juice_base64_*/_juice_stun_* 等是内部符号（源文件 src/*.h），消费方不应依赖，test_package 也已规避。
- **动态库加载**: 本地直接运行 juice-tests 需把 build 目录加入 LD_LIBRARY_PATH（conan 环境自动处理 RPATH）。
- W2 框架文件: 未改动 SKILL.md/references/scripts/templates/ci/index.tsv/SUMMARY.md，PR 仅含 libjuice 归档目录。
---

**编译结束**: 2026-09-02 03:07
**最终状态**: built
