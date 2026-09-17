# littlefs 2.11.2 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 CMake/configure）
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，OHOS aarch64）+ libc++
- 状态: published

## 编译步骤

1. 官方源码：https://github.com/littlefs-project/littlefs tag v2.11.2
   tarball SHA-256: 47048bf9b90fda041467ea581ae2f8bfc90aa233082d2ddedcfec5a5073cad47
   （GitHub 直连不稳定，本地经 gh-proxy.com 拉取；conandata.yml 保留官方 URL，
   conan-verify E017 自动注入 ghfast.top 镜像）
2. 库本体编译：`make CC=/data/service/hnp/bin/clang AR=llvm-ar` → `liblfs.a`
   （lfs.c + lfs_util.c，-std=c99 -Os，零依赖）
3. 上游测试运行器编译（需 -D_STDIO_H 守卫，见候选 1）：
   `CFLAGS="-fPIC -O2 -D_STDIO_H" make test-runner CC=... AR=...`
4. 全量上游测试：`./scripts/test.py ./runners/test_runner -b -k`
   → 20 套件 / 194 用例 / 11606 perms 全部通过（0 失败，28741 次掉电场景），
   耗时 187.22s；日志 reports/logs/04_test_run_full.log（SHA-256 402fc679…）
5. 鸿蒙专项测试：test_package/harmonyos_test.c（内存块设备上 format/mount/
   mkdir/write/read/重挂持久化/remove 全流程 + 平台识别，20 断言 ALL PASS）
6. conan-verify 8 道门禁全 PASS（G0-G4 + L2/L4/L5），conan create 干净构建成功
7. finish（W2 结构 + R36 依赖 + W3 本地 CI）→ .ci-result.json exit_code=0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 测试运行器编译报 `redefinition of enumerator 'FDSAN_ERROR_LEVEL_FATAL'` / `_G_fpos64_t` 重定义 | 上游 test_runner.h `#undef _STDIO_H`+`#undef _FEATURES_H` 后重包含 stdio.h，依赖 glibc 可重入头文件；OHOS sysroot（musl 风格）stdio.h 内联 fpos_t/fdsan 无按类型守卫 | 测试运行器编译加 `CFLAGS+=-D_STDIO_H`（经环境变量传，勿用命令行覆盖）；库本体不受影响 → DRAFT-littlefs-stdio-guard-undef-ohos |
| 2 | lang-preflight 误判 mixed（21 py : 7 c） | 框架 lang_detect.py 将 scripts/ 测试工具 python 计入主体，违反边界规则 D.4「辅助脚本不算主体」（同 edlib 案例） | 人工按边界规则复核判 cpp，c↔cpp 兼容族不迁移；证据 03_lang_preflight_misjudge.txt |
| 3 | GitHub 直连间歇不可达 | 网络环境 | gh-proxy.com 镜像拉取 tarball（SHA-256 与官方一致）；conan-verify E017 自动处理 |

## 源码修改

无补丁（patches: {}）。上游源码零修改，仅构建参数适配。

## 依赖版本

无外部依赖（零依赖库，requirements 为空）。

## 验证结果

- liblfs.a：OHOS aarch64 clang 15 构建成功，193306 字节
- 上游测试：194/194 用例、11606/11606 permutations 通过（100%），0 失败
- 鸿蒙专项测试 harmonyos_test.c：20 断言 ALL PASS，退出码 0
- conan create：G2 PASS（含 test_package 消费者验证）
- W3 本地 CI：L0/L1 pass，.ci-result.json exit_code=0

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（纯 Makefile：make → liblfs.a；R33 conf 注入 CC/AR；copy 打包） |
| conandata.yml | 官方 URL + SHA-256 |
| test_package/harmonyos_test.c | 鸿蒙专项测试（内存块设备全流程，20 断言） |
| reports/test-report.md | 上游测试双口径台账（194 用例 / 11606 perms 全通过） |
| reports/knowledge-candidate-ledger.md | 知识候选台账与七轴查重 |
| knowledge/drafts/DRAFT-littlefs-stdio-guard-undef-ohos.{md,kv} | 路径 B 新知识草稿 |

## 注意事项

- 路径 B（知识库扩展）：候选 1 new_draft（stdio.h 守卫重入），候选 2/3 复用既有知识
- PR 前缀：【知识库扩展】
- 上游 Makefile 默认目标即 liblfs.a；无 shared 目标，配方显式拒绝 shared=ON
- 该 worktree 创建时 archives/l/libXext/{README.md,manifest.yaml} 已有外部改动
  （非本任务产生，不纳入本库 commit/PR，原子性审计已排除）---

**编译结束**: 2026-09-08 00:08
**最终状态**: published
---

**编译结束**: 2026-09-08 00:43
**最终状态**: published
