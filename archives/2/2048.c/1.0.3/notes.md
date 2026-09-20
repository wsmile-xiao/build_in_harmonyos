# 2048.c 1.0.3 适配笔记

## 编译环境
- 构建系统: makefile（单文件 C，无 configure/cmake/meson）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（OHOS aarch64 profile）
- 状态: built

## 编译步骤

1. init-build: 官方 GitHub 标签归档 v1.0.3（SHA-256
   f26b2af87c03e30139e6a509ef9512203f4e5647f3225b969b112841a9967087）。
   GitHub 直连超时，经 ghfast.top 镜像预下载 tarball 到 ~/tmp/builds/ 后重跑，
   内容与官方一致（E017 use-ghfast）。
2. lang-preflight: detected=c，任务语言 cpp 兼容族，通过（R47）。
3. 探索性编译: `make CC=clang -j1` → 生成 `2048` 可执行文件；
   `make install DESTDIR=...` staging 验证；`make test`（`./2048 test`）→
   "All 13 tests executed successfully"，exit 0。
4. conan-init 生成配方后改写为纯 Makefile 应用型配方（参考 E392
   raw-makefile-conan-recipe-pattern：compiler_executables 字典获取 +
   cwd=source_folder + copy 二进制到 bin/）。
5. conan-verify G1-G4/L2/L4/L5 全通过；finish W3 本地 CI 通过（prdiff 单包口径）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 GitHub tag 归档超时 | GitHub 直连超时（Connection timed out） | ghfast.top 镜像预下载官方 tarball 到 ~/tmp/builds/，重跑 init-build 复用缓存（E017） |
| 2 | conan-init 生成 autotools 模板配方 | 构建系统探测将纯 Makefile 误判为 autotools | 改写为 makefile 型应用配方（E392 三要素） |
| 3 | finish W3 junk_check 拦截 | JC full 模式误扫其他库基线垃圾（cloog/kics .staging-verified） | 生成 pr.diff + JUNK_PR_DIFF=pr.diff 单包口径重跑（既有草稿 libjpeg-turbo 同案） |
| 4 | conandata.yml.ghfast-bak 残留 | conan-verify G2 镜像注入备份未删除 | rm 残留并核验 conandata 已恢复官方 URL（DRAFT-E323 同案） |

## 依赖版本

无第三方依赖（仅 libc/libm，系统自带）。

## 验证结果

```bash
# 上游自测（内置于二进制）
$ ./2048 test
All 13 tests executed successfully   # exit 0

# package_info: 13/13 (100%)，双口径一致

# test_package 消费者（conan create G2 实证）
PASS 1: --version -> 2048.c version 1.0.3
PASS 2: self-test -> All 13 tests executed successfully

# 鸿蒙专项 test_ohos（4/4）
T1 aarch64 ELF / T2 无宿主路径泄漏 / T3 termios 管道驱动 / T4 --version

# conan-verify G1-G4 + W3 本地 CI
JC_RESULT=pass, L0_RESULT=pass: all checks passed, Pass rate: 100.0% (1/1)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | application 型配方（make + copy bin） |
| conandata.yml | 官方 URL + SHA-256 |
| test_package/ | 消费者测试（test.sh 调用已安装二进制） |
| test_ohos/run_ohos_test.sh | 鸿蒙专项 4 项验证 |
| commands.json | CLI 工具声明（R38，软件级） |
| reports/ | conan-verify/test-report/ohos-specific/knowledge-candidate-ledger |

## 注意事项

- 纯 Makefile 工程，配方 build() 必须 `cwd=self.source_folder`（E392）。
- W3 本地 CI 必须用 JUNK_PR_DIFF=pr.diff 单包口径，避免 full 模式误扫其他库基线垃圾。
- conan-verify 后归档目录会残留 conandata.yml.ghfast-bak，提交前须清理。

---

**编译结束**: 2026-09-19 23:01
**最终状态**: built