# jwt-cpp 0.7.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: built（conan-verify G0-G5 全部通过，待 finish/submit 提升为 published）

## 编译步骤

```bash
# 1. bootstrap（init-build，官方 v0.7.1 归档，SHA-256 实测验证）
python3 scripts/ohc-run.py init-build jwt-cpp 0.7.1 \
  --url=https://github.com/Thalhammer/jwt-cpp/archive/refs/tags/v0.7.1.tar.gz

# 2. 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight jwt-cpp 0.7.1 --src $BUILD_SRC_DIR
# → detected=cpp，匹配通过

# 3. 重写 Conan 配方（模板生成的是 autotools，jwt-cpp 实为 CMake header-only INTERFACE）
#    conanfile.py: header-library + requires openssl/3.5.6.1 + CMakeToolchain(OHOS aarch64)
#    conandata.yml: 官方 URL + 真实 SHA-256(e52f247d...5375a4)
#    test_package/: C++ HS256 sign+verify 消费者测试（替代模板的 C 伪测试）

# 4. 配方验证（8 道门禁）
python3 scripts/ohc-run.py conan-verify jwt-cpp 0.7.1
# → G0/G1/G2/G3/G4 全过；conan create 在 ohos-aarch64 profile 下干净构建成功
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 conan create 失败 `NameError: name 'os' is not defined` | 重写配方时 package() 使用了 os.path.join 但漏掉 `import os` | 补上 `import os` 后 conan-verify 通过 |
| 2 | 模板生成 autotools 配方的 conandata.yml sha256 为占位符，build_system 误判 | jwt-cpp 无 configure.ac，模板按默认 autotools 生成 | 按上游 CMakeLists 手工重写 header-only CMake 配方并实测 SHA-256 |
| 3 | conan-verify 临时注入 ghfast.top 镜像（E017 预防） | GitHub 直连不稳定 | 工具自动恢复官方 URL；复核 conandata.yml 无镜像/本地路径残留 |

## 依赖版本

- openssl/3.5.6.1（ohpcd 制品仓，R36 依赖检查通过）

## 验证结果

```bash
conan create ... -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing
# 成功；G3 系统同名库隔离 PASS（系统无 libjwt* 同名库，非 R26 系统同名情况）
# G4 产物完整性 PASS；L2/L4/L5 记录于 reports/conan-verify-report.md
```
---

**编译结束**: 2026-09-03 00:21
**最终状态**: built
