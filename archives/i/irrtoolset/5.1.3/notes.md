# irrtoolset 5.1.3 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac + Makefile.am)
- 编译日期: 2026-09-16
- 编译器: clang 15 / clang++ (aarch64, OHOS)
- 状态: published

## 编译步骤

```bash
# 1. 官方 tag 归档不携带 configure, 需 autoreconf 自举 (tool_requires automake/1.18 + libtool/2.5.4)
autoreconf -fiv
# 2. configure 显式指定 GNU 三元组 (HarmonyOS 内核无法被 config.guess 识别)
./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl
# 3. 生成 configure 后去掉 config.status 的 umask 077 (E114: HMDFS 临时目录权限)
# 4. 编译 (E074: HMDFS 下 make -j>1 jobserver fifo EPERM, 必须 -j1)
make -j1
make check        # 上游无测试注册, "Nothing to be done for 'check'"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | 网络环境 | 使用 ghfast.top 镜像 (E017) |
| 2 | autoreconf 报 aclocal 缺失 | 执行机无 automake/aclocal | tool_requires automake/1.18 + libtool/2.5.4 (同 argp-standalone 方案) |
| 3 | configure: cannot guess build type | HarmonyOS 内核 uname 无法识别 | --build/--host 显式指定 aarch64-unknown-linux-musl |
| 4 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | HMDFS 将 0700 临时目录投影为不可写 drwx--S--- (E114) | 生成 configure 后去掉 `umask 077` (同 abiword-plugin-clarisworks _drop_umask_077) |
| 5 | fatal error: 'dataset/Pix.h' file not found | 源码用相对包含 (#include "dataset/Pix.h"), out-of-source 构建树缺同级目录结构 | layout() 改 in-source 构建: basic_layout(src_folder=".") + folders.build="." (同 adjtimex) |
| 6 | conan create 强制重建超时 | -j1 单线程 + HMDFS 慢 | W3 超时预算充足 (3600s), 分步验证 |
| 7 | test_package peval 段错误 | peval 初始化强制连接 IRR whois 远端 (RADB), 无网络挂起 | test_package 排除 peval, 用 rpslcheck (本地解析) + rtconfig |

## 源码修改

无源码补丁 (仅配方层调整: autoreconf 自举 + umask 077 修复 + in-source 布局)。

## 依赖版本

- automake/1.18 (tool_requires)
- libtool/2.5.4 (tool_requires)

## 验证结果

```bash
# conan-verify: G1-G4/L2/L4/L5 全通过
python3 scripts/ohc-run.py conan-verify irrtoolset 5.1.3
# W3 本地 CI 模拟: Success 1/1 (100%)
ci/conan/build_and_test.sh archives/i/irrtoolset/5.1.3
# 消费者用例: CONSUMER-ALL-PASSED (rpslcheck 合法/非法对象 + rtconfig)
# 鸿蒙专项测试: OHOS-SPECIFIC-ALL-PASSED (aarch64 ELF + 真实 RPSL 数据)
```

上游测试统计 (双口径): source_declared_total=0 (官方 tag 无 TESTS/check_PROGRAMS 注册,
无测试框架源码, make check 无注册项), configured_executable_total=0,
executed_passed_total=0 — 如实申报, 不以空测充数。消费者用例 (test_package test.sh)
与鸿蒙专项测试独立计数, 均已实际运行通过。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方 (autoreconf 自举 + in-source 布局 + E114 修复) |
| conandata.yml | 官方 URL + SHA-256 |
| test_package/ | rpslcheck/rtconfig 实质功能测试 + MANIFEST |
| commands.json | CLI 工具声明 (peval/rpslcheck/rtconfig, R38) |
| reports/test-report.md | 测试台账 |
| reports/consumer-case.sh | 消费者用例 |
| reports/ohos-specific-test.sh | 鸿蒙专项测试 |
| reports/knowledge-candidate-ledger.md | 知识候选台账 + 七轴查重 |

## 注意事项

1. 本库为 CLI 工具集 (peval/rpslcheck/rtconfig) + 内部静态库 (libirrtoolset.a 不安装), 对外交付为 bin/ 下工具。
2. peval 依赖 IRR whois 远端 (RADB 等), 无网络环境不可用 — 库本身行为, 非适配缺陷。
3. 知识草稿 DRAFT-irrtoolset-5.1.3-relative-include-in-source (Path B: 相对包含 → in-source 构建) 随本 PR 交付。

---

**编译结束**: 2026-09-16 23:46
**最终状态**: published
