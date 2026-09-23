# E543 — 手写 Makefile C99 库的 Conan 打包与参数化测试核算

## 错误特征
上游没有 CMake/autotools，仅有 Makefile；Greatest 测试中 `TEST` 函数数量少于 `RUN_TESTp` 实例数量。消费者若把 `loom_init()` 等带副作用调用放在 `assert()` 中，Release/NDEBUG 会删除调用，表现为入队失败或测试挂起。

## 触发条件
- 构建系统：手写 Makefile
- 阶段：Conan build/test_package 与测试统计
- 影响范围：无 CMake/autotools 的 C99/C 静态库及 Greatest 参数化测试工程

## 根因分析
配方若按 CMake 习惯构建会找不到入口；上游的 `RUN_TESTp` 每个参数组都是独立执行实例，按函数名统计会少报用例。消费者测试必须避免在 `assert()` 参数中放初始化、关闭等副作用；并发共享计数也必须使用原子操作。loom 另有 `loom_queue_size()` 返回容量、`loom_get_stats().backlog_size` 返回当前积压的语义差异。

## 解决方案
### 推荐方案
固定源码 tarball SHA-256，在 `source_folder` 执行 `make CC=clang AR=llvm-ar ci`，手工复制 `libloom.a` 与公开头文件，声明 pthread 系统库。逐项盘点 `RUN_TEST/RUN_TESTp` 并将有据跳过单独记为 skipped；消费者测试使用显式错误处理、原子计数和正确的 backlog API。

### 禁止做法
- ❌ 把 `TEST` 函数定义数当作实际执行用例数。
- ❌ 把带副作用的初始化/关闭调用写在 `assert()` 中。
- ❌ 将容量 API 的返回值当作当前队列积压，或把未执行项虚报为通过。

## 验证
```bash
make CC=clang AR=llvm-ar ci
conan create archives/l/loom/0.1.1 --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=loom/*
```

设备实测：上游 10/10 Greatest 实例通过（2154 assertions），benchmarks 入口完成；消费者 1/1 通过。

## 关联条目
- 相关：无，拟由主编查重后确定最终编号
