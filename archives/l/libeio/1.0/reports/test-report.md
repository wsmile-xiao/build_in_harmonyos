# Test Report — libeio 1.0

## 编译验证
- 编译器: clang 15.0.4 (aarch64-linux-ohos, OHOS SDK 26.0.0.18)
- 构建系统: Autotools（官方 master tarball 无预生成 configure，配方以
  tool_requires automake/1.18 + libtool/2.5.4 经 autoreconf 生成）
- 编译状态: ✅ 成功（make -j1 rc=0）
- 构建命令: autoreconf --install --symlink --force && ./configure --prefix=... &&
  make -j1 && make check（check 无测试目标，rc=0）

## 平台修复
| 问题 | 修复方式 |
|------|----------|
| 旧版 ecb.h 在 C11 下 ecb_noreturn 展开为 _Noreturn 且置于函数声明尾，clang 15 报错 | patches/0001-ecb.h.patch：统一改 `ecb_attribute((__noreturn__))` |
| OHOS config.guess 无法识别 HarmonyOS kernel，configure 报 cannot guess build type | 配方显式 `--build/--host=aarch64-unknown-linux-gnu`（ABI 等价 Linux-ELF，libeio.m4 无 AC_RUN_IFELSE） |

## 上游测试说明
上游 libeio 1.0（scunningham/libeio master）**无任何官方测试**：源码树无
tests/ 目录，Makefile.am 无 TESTS/check_PROGRAMS/XFAIL 声明，`make check`
无测试目标（rc=0 但无测试执行）。官方唯一可执行样例 demo.c 为示例（非独立
测试用例），其自带 res_cb 对负结果 abort，不作为测试计数。
双口径统计：`source_declared_total=0`、`configured_executable_total=0`、
`executed_passed_total=0`，全量通过率 0/0（无测试可计数）。完整枚举见
../notes.md 上游测试台账。

## 鸿蒙专项测试（自研，tests/ohos_test.c）
真实异步 I/O 功能测试：eio_init → eio_set_min_parallel(2) → eio_busy →
eio_nthreads>0 线程池启动 → eio_readdir 枚举真实目录（result=2）→
eio_stat → eio_unlink×2 → eio_rmdir，6 个请求全部完成（requests_done=6），
实测 rc=0。

```bash
clang -O2 -I. -o libeio-ohos-test tests/ohos_test.c libeio.a -lpthread && ./libeio-ohos-test
# === PASS: libeio OHOS 专项测试全部通过 === (rc=0)
```

## 消费者验证（test_package，经 conan create 实跑）
test_package/test.c 调用公开 API：eio_init / eio_nthreads /
eio_wd_open_sync / eio_wd_close_sync / eio_nop / eio_npending / eio_poll，
随 `conan create` 的 test() 阶段实际编译链接运行，1/1 通过。

## Conan Verify (G0-G4)
| 门禁 | 结果 |
|------|------|
| G0 预构建风险评估 | ✅ PASS |
| G1 配方完整性 | ✅ PASS |
| G2 conan create（干净构建） | ✅ PASS |
| G3 系统同名库隔离 (R26) | ✅ PASS |
| G4 产物完整性 | ✅ PASS |
| L2/L4/L5 | 跳过（本地无 checksec/cache 基线路径，CI 侧执行） |

## W3 本地 CI 模拟
`finish` Step 5/10 W3 门禁通过：`.ci-result.json` exit_code=0，
log_sha256=f49b5cdf5ddeedfa2ebddf79bf84d37e03658b57e022262c2be568eba11d76ce