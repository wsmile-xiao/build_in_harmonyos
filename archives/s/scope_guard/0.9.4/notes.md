# scope_guard 0.9.4 适配笔记

## 编译环境
- 构建系统: cmake (header-only INTERFACE)
- 编译日期: 2026-09-03
- 编译器: clang/clang++ (15.0.4, aarch64-linux-ohos)
- 状态: published

## 编译步骤
1. 官方源: https://github.com/Neargye/scope_guard/archive/refs/tags/v0.9.4.tar.gz
   SHA-256: 702d6a926f707286fccb2af751b9e87f6c2344ac61889d0888c6d70070ec98fc
2. init-build 拉取官方 tag tarball（源码 26 文件，header-only 单头 include/scope_guard.hpp）
3. 上游测试按 test/CMakeLists 自动生成 C++11/14/17/20 多标准目标，ctest 12/12 全通过
   （13 个独立 TEST_CASE × 4 标准 + 2 个 config 测试 + 6 个 compile_fail 负向用例）
4. 鸿蒙专项 test_package：test_scope_guard_ohos.cpp 用 OHOS aarch64 工具链编译运行 12/12 通过
5. conan create (ohos-aarch64 profile, 干净构建) 通过；conan-verify G0-G4 + L2/L4/L5 全 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 GitHub 时 SSL 证书校验失败 | Python urllib 缺信任链 | 设置 SSL_CERT_FILE=/etc/ssl/certs/cacert.pem |
| 2 | conan-init 生成 autotools 模板 | 模板按 URL 后缀猜测构建系统，未识别 header-only | 按既有 header-only 配方模式重写 conanfile.py (package_type=header-library) |
| 3 | test_package 初始模板为 test.c 空壳 | 模板默认 C 项目 | 改写为 C++ 鸿蒙专项消费者测试 test_scope_guard_ohos.cpp |
| 4 | 鸿蒙专项测试第 10 组断言失败 | 测试自身复用 count 变量被前序反转序用例改写 | 改用独立计数器 fail_fired 修正断言 |
| 5 | conan create 下载源码超时（网络抖动） | 临时连接受限 | 提高重试（retry=6/retry_wait=10），重试后成功；conan-verify 自动注入 ghfast.top 镜像并恢复原始 conandata.yml |

## 源码修改
无（零补丁）

## 依赖版本
无运行时/编译依赖（header-only, 无 requires）

## 验证结果
```bash
# 上游测试（work 目录，clang 原生编译）
ctest: 12/12 passed, 100% (upstream_test_run.log)
# 鸿蒙 aarch64 专项测试
test_scope_guard_ohos: 12 checks, 0 failures, exit 0
# conan 干净构建
conan create . (ohos-aarch64) → test_package Passed 1/1
# 配方验证
conan-verify: G0-G4 + L2/L4/L5 全 PASS
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方 |
| conandata.yml | 官方 URL + SHA-256 |
| test_package/test_scope_guard_ohos.cpp | 鸿蒙专项消费者测试 |
| test_package/CMakeLists.txt / conanfile.py / MANIFEST.yml | test_package 结构 |
| reports/ | source_audit/bootstrap_audit/测试台账/日志/conan-verify 报告/知识候选台账 |

## 注意事项
- header-only 库无 bin/lib 产物，G3 系统同名库隔离无冲突
- 知识候选四范围查重全部命中已有 header-only 知识（E257/E307/E321/E322 等），路径 A【依赖项】
---

**编译结束**: 2026-09-03 03:43
**最终状态**: published
