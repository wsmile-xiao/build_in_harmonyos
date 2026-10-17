# brynet 1.12.2 适配笔记

## 编译环境
- 构建系统: cmake（header-only，无编译产物）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin/clang++）
- 目标平台: HarmonyOS PC aarch64（OHOS profile，C++17）
- 状态: built（本地 W3 门禁通过，待交付审批后发布）

## 源码信息
- 上游: https://github.com/IronsDu/brynet
- tag: v1.12.2（官方 release，已验证）
- 源码 SHA-256: b8b740cae39804d1e7037866046321065856c0ea9f565d26f67aeccc7ccd3d51
- 库形态: 官方 README 明确 "Header Only Cross platform high performance TCP network
  library using C++ 11"，全部实现位于 include/brynet/，无 src/ 编译产物；
  上游 CMakeLists.txt 仅 install include/brynet 头文件目录。

## 编译步骤
1. `ohc-run.py init-build brynet 1.12.2 --url=<官方 v1.12.2 tarball>` → 解压 + 骨架
2. 确认 header-only → 手工按 header-only 模板改写 conanfile.py（package_type=header-library，
   build() 留空，不伪造编译日志）
3. conandata.yml 填入官方 URL + 实测 SHA-256
4. test_package: 编写真实消费者测试 test_brynet_ohos.cpp（回环 TCP echo 服务 + 客户端
   收发 + Endian/WaitGroup 头文件验证），OHOS clang 编译运行通过
5. `ohc-run.py conan-verify brynet 1.12.2` → G1-G4 + L2/L4/L5 全部通过
6. `ohc-run.py finish brynet 1.12.2 built` → W3 本地 CI（setup.sh + build_and_test.sh）
   通过，.ci-result.json 已写入

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 误判构建系统为 autotools，生成 autotools 配方 | 骨架生成时默认模板匹配失败 | 按 header-only 模板改写 recipe，package_type=header-library |
| 2 | G1 配方完整性失败 | header-only 配方未定义 build() | 补空 build()（R34：不伪造编译日志），G1 通过 |
| 3 | W3 JC5 junk check 拦截 | 其他库 util-linux-login 的基线文件 .ci-trigger（main 分支遗留，非本任务改动）在 full 模式下被扫到 | 在任务分支本地提交本库归档，JC 走增量模式仅扫描本库文件 |

## 上游测试（R51 三步法）
- 清点: tests/ 目录 9 个 test_*.cpp + 内置 catch.hpp（单头测试框架），ctest 注册 9 个测试
- 实跑: OHOS clang 编译 9 个可执行文件，全部运行通过
  - 独立 TEST_CASE 共 10 个（test_timer 含 2 个），断言 126 条
  - 各可执行文件退出码 0，日志与 SHA-256 已留档（/storage/Users/currentUser/tmp/brynet-ut/logs/）
- 全量通过率: 10/10 (100%)；配置可执行集合: 9/9 (100%)

## 依赖版本
- 无强制依赖（header-only）。可选 OpenSSL 未安装时自动禁用 BRYNET_USE_OPENSSL，非阻塞。
- 运行时仅依赖 pthread（测试/消费者使用）。

## 验证结果
```bash
# 上游测试 9/9 可执行文件全部通过（10 TEST_CASE / 126 断言）
./test_array && ./test_buffer && ./test_endian && ./test_http && ./test_packet \
  && ./test_stack && ./test_sync_connect && ./test_timer && ./test_wait_group
# HarmonyOS 专项消费者测试
./test_brynet_ohos   # PASS: brynet OHOS loopback echo OK (23 bytes)
# 配方验证
ohc-run.py conan-verify brynet 1.12.2   # G1-G4 PASS
```

## 注意事项
- brynet 为 header-only 库，任何下游仅需 include <brynet/...> 头文件，无链接库；
  使用网络 API（TcpService/AsyncConnector 等）时需链接 -pthread。
- 交付审批（delivery_approval_required: true）通过前仅生成本地提交与交付预览，不 push/建 PR。
---

**编译结束**: 2026-09-05 04:36
**最终状态**: built
