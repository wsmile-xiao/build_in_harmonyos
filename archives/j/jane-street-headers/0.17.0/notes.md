# jane-street-headers 0.17.0 适配笔记

## 编译环境

- 构建系统: header-only（上游 Makefile/dune 仅为 OCaml 打包辅助，本包无需编译）
- 编译日期: 2026-09-26
- 编译器: clang 15（OHOS aarch64 profile，仅消费者 TU 编译）
- 状态: built

## 编译步骤

1. 取源三向同哈希: 官方 tag 归档 v0.17.0（SHA-256
   `78fa6084cd067b7a7d930d1fe1cb7eb9dcd1a90c73017e570213b47a3762eb4f`，4940 字节）。
   codeload.github.com 与 github.com/archive 两枚官方直链在 A 机各下载一份，
   与 SCT 开坑时独立自算共三方 sha256 逐字一致，无需镜像兜底（PF7: 禁
   Debian 池址与镜像域名）。
2. lang-preflight: 源码主体为 C 头文件（5 枚 .h，0 脚本），任务语言 cpp
   兼容族（R47 c↔cpp 不迁移），通过。
3. 结构件起草: recipe-search 首位 headeronly 骨架
   archives/d/dyld-headers/1378 为底稿，起草 archives/j/jane-street-headers/0.17.0/。
4. 消费者验证: test_jane_street_headers.cpp 真编译 + 真运行（3 断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 前任 worktree 落在 B 机且 B 机不可达 | 主理-71 交接棒为 B 机棒，本窗构建机为 A 机 | A 机新建 worktree（B 机旧树 0 提交、无资产损失，台账已注明弃用） |
| 2 | ocaml_utils.h / ocaml_utils_macros.h / unix_utils.h 依赖 caml/* 头 | 这 3 枚头是 OCaml 绑定模板，需 OCaml 运行时头方可编译 | 照 dyld-headers 先例: 整体打包 include/，消费者 TU 只用自包含的 core_params.h / jane_common.h；OCaml 依赖头不在 OHOS 声明可执行 |
| 3 | conan-verify 后残留 conandata.yml.ghfast-bak | 工具临时注入 ghfast.top 镜像的备份文件 | 提交前 rm 残留并核验 conandata.yml 已恢复官方 URL（E323/DRAFT 同案） |

## 依赖版本

无第三方依赖（纯头文件包；ocaml/dune 仅为上游 OCaml 打包辅助，OHOS 侧不引入）。

## 上游测试清点（R51）

- 静态清点 = 0: 源码包无 tests/ 目录、无 *_test.c；Makefile 仅 default /
  install / uninstall / reinstall / clean 五个 dune 辅助目标，无 test /
  check / runtest 目标（证据: 源码包 Makefile 全文；jane-street-headers.opam
  的 build 字段仅为 `dune build -p name -j jobs`）。
- 验证面 = 消费者用例（真编译 + 真运行，3 断言，见 test_package/MANIFEST.yml）。

## 验证结果

```bash
# 上游测试: 静态清点 0（无 tests/、无 check 目标，证据见上节）

# 消费者测试（conan create G2 实证，clang 15 armv8-aarch64 OHOS profile）
$ ./test_jane_street_headers
jane-street-headers consumer ok          # exit 0

# 断言明细（3 项）: THREAD_IO_CUTOFF==65536 编译期断言 /
# jane_common.h __unused shim 存在性守卫 / 运行期常量校验
# 五维账本: 静态 0 / 可执行 0 / 消费者实测 1/1 通过 / 跳过 0 / 失败 0

# conan-verify 门禁: 各节标题均显示 ✅ PASS，Verdict: PASS；子行实况为 G0=构建系统 unknown、跳过预查询，G1/G2/G3 通过，G4=无程序包 ID（header-library 工具限制，仅告警），L2/L4/L5=跳过（无 cache 路径）
# 报告: archives/j/jane-street-headers/0.17.0/reports/conan-verify-report.md（Verdict: PASS）
# finish W3 本地 CI: conan create exit 0，W2 结构 + R36 依赖 + PR 原子性（仅配方 13 文件）全过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 型配方（copy include + LICENSE.md） |
| conandata.yml | 官方 URL + SHA-256（三向同哈希） |
| test_package/ | 消费者测试（真编译 + 真运行，CMake find_package 链路） |
| manifest.yaml | 版本级元数据（finish 落 built） |
| notes.md | 本文件 |
| reports/test-report.md | 验证报告（五维账本） |
| reports/conan-verify-report.md | Conan verify 门禁子行与 Verdict 报告 |
| reports/audit-result.json | W4 第 3 轮独立审计判决件 |
| reports/conan-create.log | 未随 PR 入库（规则19）；A 机 主理-72 worktree 产出，随交接同相对路径复制到 B 机本 worktree；sha256 已由 W4 独立复算 |

## 注意事项

- 头文件包不建 commands.json（R38: 仅 CLI/可执行产物包必需）。
- conanfile.py 保留 export_sources / apply_conandata_patches 字面量
  （G1 判据，0 补丁也不能删）。
- OCaml 绑定头（ocaml_utils.h / ocaml_utils_macros.h / unix_utils.h）需
  caml/* 头，不在 OHOS 声明可执行（dyld-headers 对 Apple-only 头同口径）。

### 对话 #1

- 状态：built

---

**编译结束**: 2026-09-27 00:12
**最终状态**: built
