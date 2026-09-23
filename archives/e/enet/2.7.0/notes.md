# enet 2.7.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4
- 状态: published
- 上游仓库: https://github.com/zpl-c/enet
- tag: v2.7.0

## 编译步骤

enet 2.7.0 使用原生 CMake 构建（CMakeLists.txt，project(enet C)），与 1.3.18
的 autotools 不同，无需 autoreconf / config.guess 补丁：

```bash
# 1. 配置（OHOS aarch64 原生编译，clang 15.0.4）
cmake . -DCMAKE_BUILD_TYPE=Release -DENET_STATIC=ON -DENET_SHARED=OFF -DENET_TEST=ON
# 2. 编译
cmake --build . -j2
# 3. 产物
#    libenet.a + enet_test / enet_test_unit / enet_test_extra_peers / enet_test_ipv4_only
# 4. 上游测试
./enet_test_unit && ./enet_test && ./enet_test_extra_peers && ./enet_test_ipv4_only
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 配方模板 | 工具按 1.3.18 历史推断构建系统，但 2.7.0 已迁移 CMake | 改用手写 CMake 配方（ENET_STATIC/ENET_SHARED/ENET_TEST 选项），无 autoreconf |
| 2 | 新库 R01 无 worktree | feat/enet-2.7.0 分支不存在 | 任务授权 worktree_creation_authorized，从 main 创建唯一专用 worktree |

## 源码修改

无（0 个补丁）。enet 2.7.0 为纯 POSIX C 库，OHOS aarch64 原生编译零修改。

## 依赖版本

无第三方运行时依赖（纯 C，仅 libc + socket API）。
构建期无 tool_requires（CMake 原生构建，不需要 automake/libtool）。

## 验证结果

```bash
# 上游测试（双口径，完整台账见 reports/test-report.md）
# 口径一：源码声明 7 个独立用例（test_times.c 6 个 TEST + build.c 1 个集成用例）
# 口径二：当前配置 4 个可执行目标
# 全部通过：7/7 用例、4/4 目标，exit 0
./enet_test_unit   # 6/6 PASSED
./enet_test        # 32 客户端连接/收发包/断开，PASS
./enet_test_extra_peers  # 5000 peers 变体，PASS
./enet_test_ipv4_only    # IPv4-only 变体，PASS

# HarmonyOS 专项测试（test_package/test.c，真实消费者回环测试）
./test_enet_ohos   # client/server 127.0.0.1 可靠包双向校验 + 优雅断开，PASS

# Conan 验证
conan-verify: G0-G4 + L2/L4/L5 全通过
W3 本地 CI: incremental 模式通过（JC/L0/L1 pass，100%）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（ENET_STATIC=ON，ENET_TEST=OFF 打包） |
| conandata.yml | 官方 URL + 实际 sha256 |
| test_package/ | 真实消费者回环测试 + MANIFEST.yml |
| reports/ | bootstrap/source/adaptation 审计日志 + 双口径测试台账 |

## 注意事项

- 上游测试无 ctest 注册（CMakeLists 未 enable_testing/add_test），测试为直接可执行目标；
  R51 台账已按源码声明口径统计。
- enet_test_extra_peers 中个别客户端 DISCONNECT_TIMEOUT 是 5000 客户端在 1000 轮
  握手窗口内的正常超时路径输出，进程以 0 退出，测试完成。
- 本地 W3 首次 full 全仓扫描误报 main 基线 util-linux-login/.ci-trigger 残留；
  本地提交后 W3 以 incremental 模式（仅 enet 8 文件）通过（boolean-lite 等先例同）。
