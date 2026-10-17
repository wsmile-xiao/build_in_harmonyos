# skypat - C++ 性能分析与单元测试框架

## 简介
skypat 是一个 C++ 测试框架，把 perf_events 性能计数与普通单元测试结合：
测试用例通过 `SKYPAT_F` / `SKYPAT_C` 注册，断言使用 `EXPECT_*` / `ASSERT_*`，
`PERFORM(event)` 块测量代码段的时间与（可选）硬件/软件 perf 事件计数，
支持 Pretty 控制台与 CSV 两种结果输出（`skypat::Test::Initialize(argc, argv)`）。

## OHOS 适配
- 构建系统：GNU Autotools（上游 GitHub 发布包为 git snapshot，需 `autogen.sh` 引导）；
  配方以 `tool_requires(automake/1.18, libtool/2.5.4)` 补齐 CI 缺失的 aclocal/automake/libtoolize
- 显式 `--build/--host=aarch64-unknown-linux-gnu`（config.guess 不识 HarmonyOS）；
  HMDFS 下用构建目录私有 mktemp wrapper 规避 `config.status` 临时目录不可写
- **运行期 perf 降级**：OHOS 内核对 `perf_event_open` 返回 `EACCES`（HW/SW 均拒绝），
  补丁将计数路径改为运行期 fd 探测（不可用=0）、计时回退到 `clock_gettime`，
  并在 stderr 一次性报告；`PERFORM()` 始终可运行且时长真实
- 补丁 0003 修复 `Mutex::tryLock()` 缺失 `throw()` 异常规范（profile cppstd=17 硬错误）
- 交付产物：`lib/libskypat.so.3.0.1`（soname `libskypat.so.3`）+ `include/skypat/*.h`
  + `lib/pkgconfig/skypat.pc`；无运行时依赖（zlib 未被使用，`--without-zlib`）
- 上游无自动化测试套件（无 tests/ 目录、无 check/TESTS 注册、`--enable-unittest`
  条件在 Makefile.am 中无引用），`test_package/test_skypat.cpp` 自建消费者测试
  （2 用例 6 断言 + 6 项运行期校验，含 PERFORM() 计时契约回归）

## 功能
- 单元测试：`SKYPAT_F`（函数式）/ `SKYPAT_C`（fixture 式），`EXPECT_*` / `ASSERT_*` 断言族
- 性能测试：`PERFORM(event)` 测量代码段时间/perf 事件；支持 HW/SW 事件枚举
- 结果输出：Pretty 控制台（彩色、PASSED/FAILED 汇总）与 CSV（`-c <file>`）
- 监听器扩展：`skypat::Listener`（OnTestPartResult / OnPerfPartResult / OnTestEnd 等）
- 多线程辅助：Mutex / ScopedLock / WaitCondition

## 依赖关系
```
skypat/3.2.0 (autotools, C++11+)
└─ 无运行时依赖（构建期 tool_requires: automake/1.18, libtool/2.5.4）
```

## 参考资料
- 上游仓库：https://github.com/skymizer/SkyPat
- 源码包：https://github.com/skymizer/skypat/archive/refs/tags/v3.2.0.tar.gz
- 适配记录：`3.2.0/notes.md`

## 许可证
BSD-3-Clause（New BSD License，见 `LICENSE`）
