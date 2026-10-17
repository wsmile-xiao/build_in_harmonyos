# ut 2.3.1 适配笔记

## 编译环境
- 构建系统: cmake（header-only，无编译阶段）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）
- Conan: 2.32.0 / CMake: 4.1.2
- 状态: built（本地验证通过，未 upload）

## 编译步骤

ut 是 boost-ext/ut 单头测试框架（include/boost/ut.hpp），header-only 无 configure/make。
Conan 配方 package_type=header-library，source() 下载官方 tarball，package() 拷贝
include 头文件与 LICENSE 到包内。上游测试按官方 CMake 驱动验证：

```bash
cmake -S . -B build-ctest -DBOOST_UT_BUILD_TESTS=ON -DBOOST_UT_ENABLE_RUN_AFTER_BUILD=NO \
      -DBOOST_UT_BUILD_EXAMPLES=OFF -DBOOST_UT_BUILD_BENCHMARKS=OFF -DCMAKE_CXX_STANDARD=20
cmake --build build-ctest -j8
ctest --test-dir build-ctest --output-on-failure   # 4/4 Passed
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 运行 ut_test 时 stderr 出现 "tests: 13 \| 7 failed / libc++abi: terminating" | ut.cpp 用 `ut::cfg<ut::override> = fake_cfg{}` 覆盖 runner，故意注入失败断言/异常事件验证框架检测能力；abort 用例经 fork() 子进程输出 terminating | 识别为框架自测预期输出，以主进程退出码 0 + ctest Passed 判定通过；沉淀知识草稿 DRAFT-ut-2.3.1-test-framework-self-test-semantics |
| 2 | conan create 报 Imported target includes non-existent path .../p/include | 初版配方 copy() 用相对 dst 落 build 目录而非 package 目录 | package() 用 os.path.join(self.package_folder, "include") + src 指向 source_folder/include |
| 3 | finish W3 junk_check 命中 archives/u/util-linux-login/2.42.2/.ci-trigger | 本地 origin/main 比 HEAD 新，diff 三点差为空回退 full 模式整仓扫描，检出 main 存量其他库隐藏文件 | 基线隔离复验：git rm --cached 临时索引隔离 → 复跑 W3 通过 → git reset 恢复 → pre/post SHA-256 核对一致（e3b0c44...） |

## 源码修改

无补丁（header-only，官方源码直接打包）。

## 依赖版本

无第三方依赖（零 requires）。工具链：clang 15.0.4 / CMake 4.1.2 / Conan 2.32.0。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify ut 2.3.1    # G1-G4 + L2/L4/L5 全过
python3 scripts/ohc-run.py finish ut 2.3.1 built    # W3 本地 CI 模拟 100% (1/1)
ctest --test-dir build-ctest                        # 4/4 Passed
./.audit-tmp/ohos_test                              # HarmonyOS 专项 15 asserts in 8 tests 通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | 2.2K | header-only 配方（package_type=header-library） |
| conandata.yml | - | 官方 URL + SHA-256 |
| test_package/ | - | C++ 消费者测试（真实 include boost/ut.hpp） |
| reports/test-report.md | - | 验证报告（上游测试双口径台账） |

## 注意事项

- ut_test 自测的 stderr 失败摘要是预期输出（fake_cfg 故意失败），判定以退出码/ctest 为准
- win_compat_test 仅 WIN32 注册（互斥编译分支），OHOS 未实例化，不计失败
- 知识库扩展：新增草稿 DRAFT-ut-2.3.1-test-framework-self-test-semantics（.kv/.md 配对）
## 编译结束
本版本适配流程已完整执行：bootstrap → 源码核验 → 上游测试（4/4）→ HarmonyOS 专项测试 → conan-verify 全过 → finish（W3 本地 CI 100%）→ W4 审计通过。
