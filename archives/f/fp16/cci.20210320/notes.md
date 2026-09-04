# fp16 cci.20210320 适配笔记

## 编译环境
- 构建系统: cmake（header-only，CMake INTERFACE library）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 / clang++ (aarch64-linux-ohos profile)
- 状态: built

## 编译步骤

1. `curl` 下载官方源码 zip（sha256=e66e65515fa09927b348d3d584c68be4215cfe664100d01c9dbc7655a5716d70，
   conan-center-index recipes/fp16/all/conandata.yml 声明值一致）
2. `ohc-run.py init-build fp16 cci.20210320`（GitHub 直连超时，复用已下载 tarball + EXPECTED_SHA256 校验）
3. CMake 配置（FP16_BUILD_TESTS=ON, FP16_BUILD_BENCHMARKS=OFF；
   `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`，CMake 4.1.2 与上游 googletest 1.8.0 声明 2.8.12 兼容）
4. 运行上游 ctest：7/7 通过；psimd 4 个测试源（上游 CMake 未注册）手动编译运行 22/22 通过
5. 新增 HarmonyOS 专项测试 `test/fp16-ohos-test.cc`（注册 fp16-ohos-test）：4/4 通过
   （IEEE/alt 已知值 + 65536 编码全扫往返一致性）
6. `conan-init` → header-only 配方（package_type=header-library，无编译，复制 include/）
7. `conan-verify`：G1-G4 PASS（G1 需显式 no-op build() 满足结构门禁，E257）
8. `finish`：W2 原子性 PASS、W3 本地 CI PASS、.ci-result.json exit_code=0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时（Errno 110） | 大陆网络无法直连 github.com | ghfast.top/gitcode 镜像前缀 + sha256 实测校验（E017） |
| 2 | CMake 4.1.2 configure 拒绝 googletest 1.8.0（min_required 2.8.12） | CMake 4.x 移除 <3.5 兼容策略 | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（DRAFT-E321） |
| 3 | conan-verify G1 FAIL：缺 build() 方法 | G1 结构门禁把 build() 列为必填 | header-only 配方补 no-op build()（E257） |
| 4 | 专项测试 alt_known_values 初版断言失败 | alt 格式无独立 inf/nan 位型（0x7C00=65536.0） | 修正测试期望为 alt 真实语义（64 位全双射） |

## 源码修改

- 补丁：`patches/0001-CMakeLists.txt.patch` —— 在 CMakeLists.txt 中注册
  `fp16-ohos-test` 目标（新增 HarmonyOS 专项测试入口）
- 专项测试源：`test/fp16-ohos-test.cc`（源 work 目录内，随补丁按 per-file difflib 归档）

## 依赖版本

- 无第三方 Conan 依赖（header-only）
- 测试框架：googletest 1.8.0（上游 CMake 声明，本地镜像下载）
- psimd（master，上游 SIMD 测试头，上游 CMake 自动下载）

## 验证结果

- 上游测试：86/86 = 100%（ctest 7 目标 64 用例 + psimd 4 目标 22 用例，全部 PASSED）
- HarmonyOS 专项测试：4/4 PASSED
- conan-verify：G1/G2/G3/G4 全部 PASS（ohos-aarch64 profile，header-only 无 L2/L4/L5 产物）
- W3 本地 CI 模拟：PASS（JC/L0/L1 绿，conan create 通过）
- test_package 消费者测试：真实调用 fp16 API，conan create L1 执行通过

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library） |
| conandata.yml | 官方源码 URL + sha256 |
| test_package/ | 消费者测试（test.c 真实 API 断言）+ MANIFEST.yml |
| patches/ | fp16-ohos-test 注册补丁 |
| reports/ | conan-verify-report.md、test-report.md、knowledge-candidate-ledger.md、w3-local-ci.log |

## 注意事项

- fp16 为依赖项任务（task_type=依赖项），PR 前缀【依赖项】
- 知识路径：路径 A（E257/E017/DRAFT-E321 复用；alt 格式语义为库自身文档范畴，无新增通用知识），
  台账见 reports/knowledge-candidate-ledger.md

---

**编译结束**: 2026-09-03 03:43
**最终状态**: built