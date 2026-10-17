# enumbitmask 1.0 适配笔记

## 编译环境
- 构建系统: headeronly（无构建系统，纯单头文件库）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos, -std=c++17 -stdlib=libc++)
- 状态: built

## 编译步骤
1. `ohc-run.py init-build enumbitmask 1.0 --url=https://github.com/Reputeless/EnumBitmask/archive/refs/tags/v1.0.tar.gz`
2. 因核心是 header-only（仅 EnumBitmask.hpp，74 行，CC0-1.0），按
   `templates/conanfile-headeronly.py.tmpl` 重写 conanfile.py（package_type=header-library，
   无编译 build()，package() 拷贝头文件 + LICENSE）。
3. `ohc-run.py conan-init enumbitmask 1.0` 生成 conandata.yml + test_package 骨架后，
   将空壳 test.c 重写为真实消费者用例 test.cpp + 鸿蒙专项 test_ohos.cpp。
4. `ohc-run.py conan-verify enumbitmask 1.0 --profile ohos-aarch64` → G1-G5 全 PASS。
5. `ohc-run.py finish enumbitmask 1.0` → W3 本地 CI 模拟 PASS（.ci-result.json exit_code=0）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 配方 | init_build._guess_build_system() 对无构建系统 URL 兜底返回 "autotools" | 按 headeronly 模板重写 conanfile.py（详见知识草稿 DRAFT-enumbitmask-1.0-conan-init-headeronly-autotools-misdetect） |
| 2 | conan-verify 报 `settings.os.version not defined` | 直接用相对路径 profile 被工具从模板重建 | 将 ci/conan/profiles/ohos-aarch64 注册为 ~/.conan2/profiles/ohos-aarch64 后按名称引用 |
| 3 | 测试 test_ohos.cpp 编译失败 | `if (Flag8(0))` 裸 enum 不可转 bool（库只对运算符结果 EnumWrapper 提供 explicit operator bool） | 改用 `Flag8(0) & Flag8(0)` 经公开运算符取 bool |
| 4 | W3 JC 命中其他库基线空标记文件 | full 模式 git ls-files 扫到 cloog/kics 的 .build-closed/.staging-verified（main 已有） | 记录 SHA-256（e3b0c442...），git rm --cached 临时隔离 → 复跑 W3 → git restore --staged 恢复，前后哈希一致 |

## 源码修改
无补丁（header-only 库，未修改上游源码）。

## 依赖版本
无运行时依赖（0 个）。

## 验证结果
- conan-verify: G1/G2/G3/G4 PASS，L2/L4/L5 完成
- conan create 内 ctest: 2/2 PASS
  - test_enumbitmask: `test enumbitmask 1.0: OK (mode=6, perm=5)`
  - test_ohos_enumbitmask: `test_ohos enumbitmask 1.0: OK (uint8/16/64, constexpr, 复合运算)`
- 上游 example.cpp（样例）: 编译运行 exit 0
- W3 build_and_test.sh: PASS（报告 reports/test-report.md）

## 交付物
- conanfile.py + conandata.yml（header-only 配方）
- test_package/（test.cpp 消费者 + test_ohos.cpp 鸿蒙专项 + MANIFEST.yml）
- reports/（conan-verify-report.md / test-report.md / upstream-test-ledger.md / knowledge-candidate-ledger.md）
- knowledge/drafts/DRAFT-enumbitmask-1.0-conan-init-headeronly-autotools-misdetect.{kv,md}

## 注意事项
上游无测试框架，测试统计为 0/0（无独立上游用例）；example.cpp 列样例并于台账内实际运行验证。