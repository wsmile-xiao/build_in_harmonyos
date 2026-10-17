# bptree 0.5.0 适配笔记

## 编译环境
- 构建系统: makefile（单头文件库，BPTREE_IMPLEMENTATION 模式；无 configure）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（OHOS SDK，aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

bptree 是纯 C 单头文件 B+ tree 库（include/bptree.h），无编译产物，
Conan 配方按 header-only 打包：

```bash
# 上游测试（原生 + OHOS 工具链双跑）
clang -std=c11 -g -O0 -Iinclude -o bin/test_bptree test/test_bptree.c
./bin/test_bptree                      # 29 tests run, 0 failures
/data/service/hnp/bin/clang -std=c11 -Iinclude -o bin/test_bptree_ohos test/test_bptree.c
./bin/test_bptree_ohos                 # 29 tests run, 0 failures

# 鸿蒙专项测试（独立新增，见 tests/test_bptree_ohos_specific.c）
/data/service/hnp/bin/clang -std=c11 -O2 -Iinclude -o test_bptree_ohos_specific test_bptree_ohos_specific.c
./test_bptree_ohos_specific            # PASSED: iterations=3000 removed=1206 seen=361 range_n=50

# 配方验证
python3 scripts/ohc-run.py conan-verify bptree 0.5.0    # G1-G4/L2/L4/L5 全过
python3 scripts/ohc-run.py finish bptree 0.5.0 built     # W3 单包口径通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 mixed → env_unsupported | pyproject.toml（dev-tooling，无 [build-system]、零 .py）被 _manifest_scan 误判为 python | 人工复核（0 .py + 无 build-system + 统计 c 100%）判 c（cpp 兼容族）继续适配；记录草稿 DRAFT-bptree-lang-preflight-pyproject-tooling-false-positive |
| 2 | G2: "Package type is 'library', but no 'shared' option declared" | header-only 库误用 package_type=library | 改 package_type=header-library（无 shared 需求） |
| 3 | test_package CMake 报 "Imported target includes non-existent path .../p/include" | copy() 相对路径解析到 build 目录，头文件未进 package 目录 | copy() 用 os.path.join(source_folder/package_folder) 绝对路径（boost-te 前例同款） |
| 4 | W3 JC 拦截 2 个 .staging-verified | full 模式扫到 main 上其他库（cloog/kics）历史基线文件 | JUNK_PR_DIFF=pr.diff 单包口径重跑 W3 |

## 源码修改

无（未修改任何上游源码，patches: {}）

## 依赖版本

无第三方依赖（仅 libc：stdlib/stdbool/stdint/stdio/string/assert/math/time）

## 验证结果

```bash
# 上游测试（test_bptree.c，29 个 RUN_TEST）
原生:   29 tests run, 0 failures（exit 0）
OHOS:   29 tests run, 0 failures（exit 0）
# 鸿蒙专项 tests/test_bptree_ohos_specific.c
PASSED: iterations=3000 removed=1206 seen=361 range_n=50 final_count=361 ordered=1（exit 0）
# 消费者 test_package/test.c（conan create 内执行）
1/1 Test #1: test_bptree  Passed
# conan-verify / finish
G1-G4/L2/L4/L5 全过；W3 本地 CI 通过（.ci-result.json exit_code=0）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library） |
| conandata.yml | 官方源 https://github.com/habedi/bptree/archive/refs/tags/v0.5.0.tar.gz，sha256=e0d696d3... |
| test_package/ | 消费者测试（真实调用 create/put/get/contains/remove/check_invariants） |
| tests/test_bptree_ohos_specific.c | 鸿蒙专项测试（随机压力 + 迭代器顺序 + 范围查询 + 不变量） |

## 注意事项

- 官方 tarball 顶层目录名（codeload: bptree-0.5.0/ vs api.github.com: habedi-bptree-e27e682/）
  导致字节哈希不同（e0d696... vs b22dc7...），内容树逐文件哈希一致（79b7f0c7...）；
  conandata.yml 的 sha256 必须以官方 archive URL 字节为准（E406 多路径交叉验证）。
- 任务为【知识库扩展】路径 B：新增草稿
  knowledge/drafts/DRAFT-bptree-lang-preflight-pyproject-tooling-false-positive.{kv,md}。
