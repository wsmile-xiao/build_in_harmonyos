# llhttp 9.4.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. init-build 下载 release tarball（GitHub release，sha256 校验通过）
2. lang-preflight：检测为 c（c↔cpp 兼容族），通过
3. 探索性编译：cmake 配置（Release，shared ON / static OFF）→ make -j2 → make install DESTDIR（staging 隔离）
4. conan-init 生成配方 → 手工修正为 CMake 模板（conan-init 误用 autotools 模板，llhttp 无 configure 脚本）
5. conan-verify：8 道门禁全过（G0-G4 + L2/L4/L5），conan create 干净构建成功

关键 cmake 变量：
- `LLHTTP_BUILD_SHARED_LIBS=ON`、`LLHTTP_BUILD_STATIC_LIBS=OFF`（历史版本一致口径）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 模板配方 | URL 无构建系统关键词，模板误判 | 依据源码 CMakeLists.txt 重写为 CMake 配方（cmake_layout + CMakeToolchain） |
| 2 | 产物 libllhttp.so 无 DT_SONAME | 上游 CMake 未设 SOVERSION（无版本化 .so 实体） | 沿 9.3.1.1 验证方案：patchelf 补 SONAME → 剥旧签名段 → 自签（package() 内 `_set_soname_and_resign`） |
| 3 | 测试用例 CONNECT 解析预期失败 | llhttp 对 CONNECT 按设计返回 HPE_PAUSED_UPGRADE（隧道升级暂停），非 HPE_OK | 测试预期改为 HPE_PAUSED_UPGRADE，与 RFC 7231 §4.3.6 语义一致；探针程序核实三种 CONNECT 目标格式均触发 pause-on-upgrade |

## 上游测试说明

- 上游 9.4.2 release tarball **无 native 测试套件**：tar -t 核实无 test/ 目录、无 CTest 目标；llhttp 官方测试在 Node.js 主仓（test/parallel/test-llhttp*.js），依赖 Node.js 运行器，无法在 CI 直接执行
- 按"上游无测试时补适配测试且不少报"原则，test_package/test.c 以消费者视角覆盖上游测试套件在 C API 层可等价验证的功能面：**6 个测试组共 53 项断言**（GET 基础解析与回调、全方法矩阵 8 方法 + method_name 往返、chunked body 三回调、错误报告三 API、pause/resume 控制流、响应解析含 on_status/llhttp_finish），实测 53/53 通过

## 源码修改

无补丁（conandata.yml patches 为空），源码完全兼容 OpenHarmony（与 9.3.1/9.3.1.1 历史一致）。

## 依赖版本

无外部依赖（零 requires）。

## 验证结果

```bash
# 探索性编译
cmake .. -DCMAKE_BUILD_TYPE=Release && make -j2   # ✅ libllhttp.so (84KB)
# 冒烟（staging 产物 + 小程序链接运行）
smoke: rc=0 method=GET major=1 minor=1            # ✅
# conan-verify G2: conan create（ohos-aarch64 profile，干净构建）
G2: PASS（test_package 实跑）
# 消费者全量测试
==== Test Summary: 53 passed, 0 failed ====        # ✅ 53/53
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libllhttp.so | 84KB | HTTP 解析共享库（补 SONAME + 自签） |
| llhttp.h | 31KB | C API 头文件 |
| libllhttp.pc / llhttpConfig.cmake | - | pkg-config / cmake 配置 |

## 注意事项

- 历史 9.3.1 notes 记录的 HMDFS fifo / cmake 平台警告 / SSL 证书问题在本机均未复现（本地环境已配置 CA 证书；make jobserver fifo 警告无害自动降级）
- CI 侧为干净环境：配方不依赖任何 shell 环境变量（R33），编译器/标志全部来自 ConanToolchain
- 下游引用：`self.requires("llhttp/9.4.2")`
---

**编译结束**: 2026-09-03 00:43
**最终状态**: built
