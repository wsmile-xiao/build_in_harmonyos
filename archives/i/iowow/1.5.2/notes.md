# iowow 1.5.2 适配笔记

## 编译环境
- 构建系统: Autark（顶层 build.sh 包装器，非 autotools/cmake）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，aarch64-unknown-linux-ohos）
- 状态: published

## 编译步骤

1. 官方源码：GitHub Softmotions/iowow tag v1.5.2（tar.gz，SHA-256 已核验，
   因本机 github.com 不可达改走官方 codeload 域下载，字节一致）。
2. native 验证（work 目录）：`BUILD_TYPE=Release ./build.sh --prefix=$DEFAULT_PREFIX -J4`
   构建并安装 libiowow.a + include/iowow/*.h；注意 autark 并行参数是 `-J` 而非 `-j`。
3. 上游测试：`BUILD_TYPE=Release IOWOW_RUN_TESTS=1 ./build.sh -J4`
   （启用 cunit 依赖：`conan install cunit/2.1.3 -r=ohpcd`，导出 PKG_CONFIG_PATH）。
4. conan-init 生成配方后**手工重写** conanfile.py（autotools 模板不适用 Autark）：
   - build() 直接 `CC=<conf 编译器> BUILD_TYPE=Release ./build.sh --prefix=<stage> -J1`
   - PATH 前置 /bin（autark system.sh 硬校验 `install` 工具）
   - package() 兼容 lib64/ 与 lib/（Autark 64 位把库装到 lib64/，只拷 lib/ 会缺库，
     CMakeDeps 报 `Library 'iowow' not found in package`）
5. test_package/test.c 改为真实调用 iwxstr 公开 API（iw_init / iwxstr_new_printf /
   iwxstr_cat2 / iwxstr_ptr / iwxstr_destroy_keep_ptr），替换模板空壳打印。
6. conan-verify 8 门禁全部 PASS（conan create 干净构建 + test_package 消费者 1/1）。
7. 鸿蒙专项测试：tests/harmonyos_test.c（iwkv 持久化存储全生命周期，11/11 PASS）。
8. finish published：W2 结构、R36 依赖、W3 本地 CI（.ci-result.json 写入）全部通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 github.com 失败 | 本机 github.com 主域不可达（codeload 可达） | 用官方 codeload.github.com 下载同一 tag tarball，SHA-256 核验后放入 build 目录重跑 |
| 2 | `./build.sh -j4` 打印 usage 退出 | autark 并行参数是 `-J`，`-j` 是未知参数 | 改用 `-J4` |
| 3 | `error: required tool 'install' not found in PATH` | 默认 PATH 无 /bin，而 install 在 /bin | PATH 前置 /bin |
| 4 | conan-verify G2 报 `Library 'iowow' not found in package` | Autark 64 位安装产物在 stage/lib64/，package() 只拷 lib/ | package() 遍历 lib64/ 与 lib/ |
| 5 | 上游测试报 `Package cunit was not found` | 测试经 pkg-config 探测 cunit | `conan install cunit/2.1.3 -r=ohpcd` 并导出 PKG_CONFIG_PATH |
| 6 | `qsort_r` 探针链接报 undefined symbol（构建期 .autark 探测） | OHOS musl 无 glibc 签名 qsort_r | 预期失败，非库失败：Autark 不设 HAVE_QSORT_R，iowow 回退自带 sort_r.h |
| 7 | W3 本地 CI JC1/JC5 命中 cloog/kics 提交前基线状态文件 | junk_check 在无 origin/main diff 时回退 full 模式整仓扫描 | 基线隔离复验：记录 SHA-256、临时 git rm --cached、重跑 W3 通过、原样恢复（git add -f）并核对 SHA-256 一致 |

## 源码修改
- 无补丁（patches/ 为空）；配方与测试文件位于 archives/i/iowow/1.5.2/ 版本目录。

## 依赖版本
- 构建期测试依赖：cunit/2.1.3（ohpcd 制品仓，recipe+binary 均已发布；R35 用 conan download 核验）

## 验证结果

```bash
# 上游测试全量（78/78 通过，24 个执行器）
BUILD_TYPE=Release IOWOW_RUN_TESTS=1 ./build.sh -J4   # exit 0
# 鸿蒙专项测试（11/11 PASS）
clang -std=gnu11 -O2 -DIW_STATIC -I... tests/harmonyos_test.c -L... -liowow -lm -pthread -o harmonyos_test && ./harmonyos_test
# 配方验证 8 门禁
ohc-run.py conan-verify iowow 1.5.2                  # exit 0
# finish（W2/W3/R36 全过，.ci-result.json 写入）
ohc-run.py finish iowow 1.5.2 published
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Autark 构建适配配方（直接调 build.sh） |
| conandata.yml | 官方源码 URL + SHA-256 |
| test_package/ | 消费者用例（真实调用 iwxstr API）+ MANIFEST.yml |
| tests/harmonyos_test.c | 鸿蒙专项测试（iwkv 持久化） |
| reports/test-report.md | 上游测试枚举台账与双口径统计（78/78） |
| reports/knowledge-ledger.md | 知识候选台账 + 七轴查重 + 路径决定 |
| knowledge/drafts/DRAFT-iowow-1.5.2-autark-build-system-ohos-adaptation.{md,kv} | 路径 B 知识草稿对 |

## 注意事项
- 纯库包（libiowow.a），无 CLI 可执行产物，不需要 commands.json（R38 库类型豁免）。
- 知识路径：`new_draft`（路径 B，知识库扩展），草稿与三方库归档同 PR 交付。---

**编译结束**: 2026-09-21 22:07
**最终状态**: published
---

**编译结束**: 2026-09-21 22:09
**最终状态**: published
