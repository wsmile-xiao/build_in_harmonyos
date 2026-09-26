# libvarlink 24.0.1 适配笔记

## 编译环境
- 构建系统: meson（meson.build，meson >= 0.40，ninja 1.13.1）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- 状态: published（conan-verify G1-G4 + L2/L4/L5 全部通过，W3 通过）

## 编译步骤

```bash
# 环境：meson 子进程不按 PATH 解析工具，需显式注入全路径
CC=/data/service/hnp/bin/clang AR=/data/service/hnp/bin/llvm-ar \
RANLIB=/data/service/hnp/bin/llvm-ranlib LD=/data/service/hnp/bin/ld.lld \
meson setup /storage/Users/currentUser/tmp/lv-build \
  --prefix=/storage/Users/currentUser/tmp/lv-install
ninja -C /storage/Users/currentUser/tmp/lv-build          # 全量构建（12 目标）
DESTDIR=/storage/Users/currentUser/tmp/lv-stage meson install --no-rebuild
# 测试
cd /storage/Users/currentUser/tmp/lv-build
meson test --list                    # 326 项注册（8 C/脚本 + 103 y_ + 215 n_）
```

产物：libvarlink.so.0（SONAME 0）、varlink.h、libvarlink.pc、varlink CLI（tool/）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败（urllib 直连 github 超时 / HTML） | tag 是 `v24.0.1` 非 `24.0.1`；本机对 github 443 直连抖动 | 用 `archive/refs/tags/v24.0.1.tar.gz` 官方归档，curl 预下载放入 `~/tmp/builds/` 缓存后 init-build |
| 2 | meson 报 "Unknown compiler clang / llvm-ar" | meson 子进程不按 PATH 解析裸命令 | setup 时显式传 `CC=/data/service/hnp/bin/clang AR=... RANLIB=... LD=...` |
| 3 | test-json 103 个 y_ 用例全失败（rc=134 断言） | OHOS musl libc `open_memstream` 在 `fclose` 前必须显式 `fflush`，否则缓冲不终化（空输出，fclose 返 -9）；命中 scanner.c/interface.c/type.c/object.c/test-json.c | 5 处 `fclose(stream)` 前加 `fflush(stream)`（patches/0001~0005）；修复后 103/103 通过，test-interface/type/server-client 同根因转通过 |
| 4 | tool 编译失败：`program_invocation_short_name` 未声明 | GNU/glibc 扩展符号，OHOS musl libc 无声明也无链接符号（8 个 tool 文件 15 处引用） | cli.h extern 声明 + cli.c fallback 定义 + main.c 从 argv[0] basename 播种（patches/0006~0008） |
| 5 | test-object 失败：`setlocale(LC_NUMERIC,"de_DE.UTF-8")` 断言 | 设备无任何 locale 数据（/usr/lib/locale 等不存在），de_DE 候选返回 NULL | 平台阻塞，未改测试未伪造；计入分母不计通过（325/326），恢复条件=安装 locale 数据 |
| 6 | conan-verify G2 失败：test 运行时 "libvarlink.so.0 symbol not found" | test_package `cmake.test()` 不带运行期 LD_LIBRARY_PATH | 主配方 package_info 注入 runenv LD_LIBRARY_PATH；test() 改 `self.run(..., env="conanrun")` 直接运行二进制 |
| 7 | W3 失败 JC junk 检查（full 整仓扫描） | full 模式扫到 main 上其他库既有基线垃圾（cloog/kics 的 .staging-verified/.build-closed） | `JUNK_PR_DIFF=pr.diff` 单包口径重跑 finish；当前库自身 E017 镜像残留（conandata.yml.ghfast-bak/.orig）每次 verify 后清理 |

## 源码修改

patches/（8 个，全部 portability，平台 only）：
- 0001-lib-interface.c.patch / 0002-lib-object.c.patch / 0003-lib-scanner.c.patch（2 处）/ 0004-lib-test-json.c.patch / 0005-lib-type.c.patch：open_memstream 前加 fflush（OHOS libc 怪癖）
- 0006-tool-cli.c.patch：program_invocation_short_name fallback 定义
- 0007-tool-cli.h.patch：extern 声明
- 0008-tool-main.c.patch：argv[0] 播种

## 依赖版本

- 无第三方 Conan 依赖（仅系统 libm）
- tool_requires: meson/1.11.0

## 验证结果

```bash
# 上游测试（meson 注册 326 项；8 C/脚本测试 + 318 JSON 数据用例）
# test-array/test-error/test-avl/test-symbols/test-interface/test-type/test-server-client: PASS
# test-object: FAIL（de_DE.UTF-8 locale 缺失，平台阻塞）
# y_*.json 103/103 PASS（fflush 补丁后）；n_*.json 215/215 按预期失败
# 全量通过率 325/326 = 99.69%；实际执行通过率 325/325 = 100%
# 详见 reports/test-report.md（逐项台账 + 双口径）

# 鸿蒙专项测试（公开 API JSON 往返，覆盖 open_memstream 修复路径）
LD_LIBRARY_PATH=<staged>/lib ./test_ohos_varlink   # ALL HARMONYOS TESTS PASSED (rc=0)

# 消费者验证（unix socket Echo 端到端，仅用公开 API）
LD_LIBRARY_PATH=<staged>/lib ./consumer_varlink    # CONSUMER VALIDATION PASSED (rc=0)

# CLI（R38）
./tool/varlink --version   # 24.0.0
./tool/varlink --help      # Usage: varlink COMMAND ...

# conan-verify（G1-G4 + L2/L4/L5 全通过）
python3 scripts/ohc-run.py conan-verify libvarlink 24.0.1   # ✅ 配方验证通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | Conan 配方（Meson 构建，官方 v24.0.1 归档，SHA-256 ca3ecd...f73b3c） |
| test_package/ | 真实消费者测试（R34 防空壳，JSON 往返调用公开 API） |
| patches/ | 8 个 portability 补丁 |
| commands.json（软件级） | varlink CLI 工具声明（R38，type=tool，binary=true） |
| reports/test-report.md | 上游测试全量枚举台账 + 双口径统计 |
| reports/knowledge-candidate-ledger.md | 知识候选台账 + 七轴查重 + 路径判断 |
| reports/conan-verify-report.md | 配方验证报告 |

## 注意事项

- 知识路径：三候选（open_memstream fflush / program_invocation_short_name / de_DE locale）均被既有知识完整覆盖（DRAFT-13533 / DRAFT-ohos-open-memstream-runtime-defect / E302 / E493 / E203 / DRAFT-ohos-musl-glibc-specific-symbols / E023 / E265），决定 reuse_existing，无新建草稿（path_a_no_knowledge）
- OHOS libc `open_memstream` 怪癖是本库最大的平台适配点：凡"写 memstream → fclose → 读 buffer"的库函数都必须显式 fflush
