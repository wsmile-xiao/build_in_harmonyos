# loom 0.1.1 适配笔记

## 来源与构建

- 上游：`https://github.com/silentbicycle/loom`，tag `v0.1.1`，commit `349b9f59457d383caf8b62cfc73352b1c898e441`。
- 源码包 SHA-256：`05f8cbd3e3099a16941accab5a6f5807514eabd67ff6c57c58f60fea74a6d1a0`。
- 上游是 C99 手写 Makefile 工程，无 CMake/autotools，无第三方依赖；运行时使用 POSIX pthread、pipe、poll 和 libc。
- Conan 配方保留上游源码，不修改测试；手工打包 `libloom.a` 与 `loom.h`，并通过 `loom::loom` CMake target 暴露 pthread 系统依赖。

## 测试口径

上游 `test_loom.c` 定义 5 个 `TEST` 函数，但 Greatest 的参数化注册展开为 10 个执行实例：1 个 init/free、2 个 join、5 个 run_tasks、1 个 idle、1 个取消清理。`NO_SLOW_TESTS=1` 会有据跳过 5 秒 idle 实例，因此不能把 5 个函数名误报为 5 个用例，也不能把跳过写成通过。

上游完整入口为 `make ci`（`make test` + `make bench`）；`benchmarks` 是独立 benchmark 运行入口，不计入 10 个 Greatest 测试实例。设备端若上游测试不通过，仅接受环境限制、OHOS 缺特性、工具未安装、据证跳过或日志链接定位等技术原因，并在此记录实际命令、退出码和首条真实错误。

## 验证结果

设备工具链：HarmonyOS HongMeng Kernel 1.12.0 aarch64，Conan 2.29.1，OHOS profile，Clang 15.0.4。

```text
make CC=clang ci
# 10 tests - 10 pass, 0 fail, 0 skipped; 2154 assertions
# benchmarks - no-op/pi/wakeup/multiprod 全部运行完成

conan create archives/l/loom/0.1.1 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=loom/*
# package build passed; test_package: loom consumer smoke test: 4 tasks passed
```

首次 Conan 试跑报 `settings.os.version value not defined`，技术原因是本仓 Conan 配方需显式移除 OHOS profile 的 `os.version`；加入 `configure(): self.settings.rm_safe("os.version")` 后重跑通过。消费者初版曾把初始化调用放在 `assert()` 中，Release/NDEBUG 删除了副作用导致入队失败；改为显式错误处理后通过。另修正 `loom_queue_size()` 是容量而非 backlog 的语义，改用 `loom_get_stats().backlog_size` 验证队列清空。上述均为适配测试问题，未将失败结果虚报为通过。CI #37976/#37979/#38795 均在 G0e 根目录白名单检查阶段被阻断，尚未进入 Conan 构建；其中 #38795 明确发现 `BUILD.gn`、`oh-package.json`，且现场 fetch 的官方 `upstream/main`（`884e47160b`）已跟踪这两个根文件；前两次发现的 `.ci-branch-marker-v6/.ci-marker-v7b` 也属于 CI checkout/base 环境内容。该失败不是 loom 源码或上游测试失败，不能通过修改软件配方绕过。后续审计又发现并修正：库类型按项目规范改为 `library`；等待计数改用 `__sync_add_and_fetch(&completed, 0)` 原子读取；失败清理先 shutdown 再 free；MANIFEST 逐项列出 10 个参数化实例，并删除无定义的 assertion_count 字段。
