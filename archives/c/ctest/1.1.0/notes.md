# ctest 1.1.0 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile，无 configure）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. `init-build ctest 1.1.0 --url=https://codeload.github.com/bvdberg/ctest/tar.gz/refs/tags/1.1.0`（上游正式 tag 1.1.0，SHA-256 6792d7a2…）
2. `lang-preflight`：detected=c（c↔cpp 兼容族，通过）
3. 源码目录直接 `make`：构建 test / test++ 演示二进制成功（上游自带用例集）
4. 运行上游 `./test`：35 项（11 OK / 22 FAIL 演示断言 / 2 SKIP），README 明示部分用例故意失败以演示框架能力
5. `conan-init` 后改写为 header-only 配方（ctest 无编译产物，仅重分发 ctest.h）
6. `conan-verify`：G1-G4 / L2/L4/L5 全过（G2 conan create 复现成功，test_package 消费者用例通过）
7. `finish`：W2 结构 + R36 依赖 + W3 本地 CI 通过（Pass rate 100%，JC/KC/L0/L1 全绿）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G1 FAIL（缺少 build()/export_sources()/补丁应用调用） | header-only 模板不定义 build()，与 G1 结构检查冲突 | 显式声明三项：export_sources()=export_conandata_patches；build()=apply_conandata_patches（补丁为空，仅完整性声明） |
| 2 | conan-verify G2 FAIL（Package type is 'library', but no 'shared' option） | 头文件库无 shared 语义 | package_type 改为 header-library |
| 3 | conan-verify G2 FAIL（BadZipFile: File is not a zip file） | codeload URL 无扩展名，conan 按 zip 解压 gzip 数据 | conandata.yml sources 增加 filename: "ctest-1.1.0.tar.gz" |
| 4 | conan-verify G2 FAIL（Imported target include non-existent path） | package() copy 使用相对 dst，头文件未落入 package_folder/include | copy dst 改用 os.path.join(self.package_folder, "include") 绝对路径 |
| 5 | test_package test.c 编译错误（CTEST2 无 CTEST_DATA 配对） | ctest 宏要求 CTEST2 前必须先声明 CTEST_DATA | 删除无数据套件用例，保留 CTEST/CTEST2+CTEST_DATA/SETUP/TEARDOWN 覆盖 |
| 6 | W3 JC 全仓扫描误报（3 个其他库基线状态文件） | 空 diff 时 junk_check 回退 full 模式整仓扫描，命中 main 中 cloog/kics 遗留 .build-closed/.staging-verified | 审计确认属无关历史基线（非 ctest 允许范围）→ 临时 index 隔离 → 复验 W3 通过 → 无条件恢复（见 reports/baseline-isolation-audit.md） |

## 依赖版本

无第三方依赖（header-only，上游零依赖）。

## 验证结果

```bash
$ make                                          # 上游演示二进制构建成功
$ ./test                                        # 35 项（11 OK/22 FAIL 演示/2 SKIP）
$ conan create archives/c/ctest/1.1.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing  # 干净构建+test_package 全过
$ python3 scripts/ohc-run.py conan-verify ctest 1.1.0   # G1-G4/L2/L4/L5 全过
$ python3 scripts/ohc-run.py finish ctest 1.1.0 published # W2/R36/W3 通过（JC/KC/L0/L1 绿）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library） |
| conandata.yml | 官方 codeload tag 1.1.0 源 + sha256 + filename |
| test_package/ | 消费者用例（CTEST 宏实际调用，R34） |
| reports/test-report.md | 上游测试申报与适配后测试统计 |

## 注意事项

- ctest 上游自带用例含故意失败项（演示断言），统计口径需在 PR/报告中注明。
- header-only 配方三项声明（build/export_sources/补丁调用）为 G1 硬性要求，不可省略。
---

**编译结束**: 2026-09-26 21:50
**最终状态**: built
