# refl-cpp 0.9.1 适配笔记

## 编译环境
- 构建系统: custom（header-only 单头文件库，无 configure/make/cmake）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15.0.4（aarch64-linux-ohos）
- 状态: built

## 编译步骤

refl-cpp 为 C++17 编译期反射库，官方打包为单头文件 `refl.hpp`（根目录），
无构建系统，Conan 配方采用 header-only 模板：

1. 核验官方来源：GitHub tag v0.9.1（commit 5ea0fedc3c75b721b9a4e6db56bd00b9fc30f72e），
   tarball SHA-256 = 361a0ca5d7ad3820e95fc4d6088d8f8552746f701a13b21f0a3cc7638b57c23b
2. conan-init 生成骨架后重写为 header-only 配方：
   - package_type = "header-library"
   - source() 下载官方 tarball；无 build() 编译（no-op + apply_conandata_patches）
   - package() copy refl.hpp → include/、LICENSE → licenses/
   - package_info() 声明 cmake_file_name/cmake_target_name，清空 bindirs/libdirs
3. conan create（ohos-aarch64 profile）通过，G1-G4 全 PASS，test_package 1/1 通过
4. 上游测试：test/refl.tests.cpp（281 行、111 处 assert）clang++ -std=c++17 编译运行通过
5. HarmonyOS 专项：/data/service/hnp/bin/clang++ --target=aarch64-linux-ohos 编译消费者测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 误判 nodejs 93% | lang_detect _SKIP_DIRS 不含 docs/，Doxygen 生成的 199 html + 126 js 被计入主体统计 | 人工核验：排除 docs/ 后 100% C++（8 cpp + 1 hpp），真实语言 cpp，按任务语言继续 |
| 2 | W3 本地 CI 模拟 JC5 拦截 | 本地无 diff 走 full 模式（git ls-files 全仓扫描），命中 main 中 util-linux-login/2.42.2/.ci-trigger（其他库 tracked 空文件，不在 JC5 白名单） | 无关历史基线：临时 index 隔离 → 复验 W3 通过 → 无条件恢复（blob e69de29b 还原），详见隔离审计 |
| 3 | G1 配方完整性 FAIL | header-only 配方缺 build()/export_sources()/apply_conandata_patches | 补 no-op build() 等方法（E257 等价知识命中） |

## 源码修改

无（header-only 库零补丁，patches/ 为空）

## 依赖版本

无第三方依赖（header-only，requires 为空）

## 验证结果

```bash
# 上游测试（111 处 assert）
clang++ -std=c++17 -I. test/refl.tests.cpp -o refl_tests && ./refl_tests   # exit 0

# 消费者测试（test_package，实际调用反射 API）
clang++ -std=c++17 -I. test.cpp -o test_refl_cpp && ./test_refl_cpp        # exit 0

# HarmonyOS 交叉编译（aarch64-linux-ohos）
/data/service/hnp/bin/clang++ --target=aarch64-linux-ohos -std=c++17 test.cpp -o test_ohos  # exit 0

# Conan 完整验证
conan create archives/r/refl-cpp/0.9.1 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable  # G1-G4 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only Conan 配方 |
| conandata.yml | 官方源 URL + SHA-256 |
| test_package/ | 消费者测试（test.cpp 真实调用 refl::reflect/for_each/debug_str/invoke） |
| MANIFEST.yml | 上游测试申报（111 assert + 消费者 3 断言） |

## 注意事项

- 本库属 header-only 无编译，CI 的 L2 smoke（无 bin/）与 L5 产物基线（无 lib/）为 skip/warn 属预期
- 知识路径：A（等价命中 E257 + DRAFT-ctre-3.10.0-header-only-recipe-test-package），未创建新草稿
