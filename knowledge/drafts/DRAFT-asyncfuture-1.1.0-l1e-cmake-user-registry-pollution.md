# DRAFT-asyncfuture-1.1.0-l1e-cmake-user-registry-pollution — W3/L1e 破坏性反测被 CMake 用户包注册表污染误判 fake test

- 触发事件：asyncfuture 1.1.0 适配，W3 L1e 把包内 lib/、include/ 移走后 `conan test` 仍 RC=0 → 误报 `fake test detected (R34)`
- 路径：Path B（知识库扩展）
- 编号：DRAFT-asyncfuture-1.1.0-l1e-cmake-user-registry-pollution

## 现象

W3 本地 CI 的 L1e 破坏性反测（build_and_test.sh）：

```
[sabotage] lib/ moved away
[sabotage] include/ moved away
[fail] L1e: test passed WITHOUT package artifacts — fake test detected (R34)
```

即：把被测包缓存目录的 bin/lib/include 移走后重跑 conan test，理论上
重建必然失败（config/头文件缺失），实测却照常通过 → CI 判定 test 不依赖
被测包（假测试）。

## 根因

上游 CMakeLists 含 `export(PACKAGE asyncfuture)`（INTERFACE target + 安装
EXPORT 的标准写法）。本机曾在 /tmp/af-test-build/upstream-build 手工跑过
一次 cmake 配置，`export(PACKAGE)` 把该旧构建树写入
`~/.cmake/packages/asyncfuture/<hash>`（用户包注册表，内容为旧树路径）。

之后 find_package(asyncfuture) 的查找顺序包含用户包注册表并**优先命中**
旧构建树——旧树里 asyncfutureConfig.cmake 与 asyncfuture.h 都完好。因此：

1. L1e 只 sabotage conan 缓存包目录（PKG_CACHE），管不到 `~/.cmake/packages/`；
2. conan test 重建时 find_package 经注册表解析到未破坏的旧树；
3. 测试照常编译/链接/运行 → 通过 → 误判 fake test。

与 E225（test_package `build_folder="$TMP"`）是**两个独立污染源**：
E225 管 conan 自身的构建目录缓存复用；本条管 CMake 跨进程的用户级
包注册表残留。CI 干净环境不出现，仅本机/worker 曾手工 cmake 配置该库
源码时触发。

## 修复与验证

1. 确认注册表残留：`ls ~/.cmake/packages/asyncfuture/` → 条目内容指向
   `/tmp/...` 非 conan 缓存路径。
2. 清除陈旧条目：`rm -rf ~/.cmake/packages/asyncfuture`。
3. 组合 E225 双保险：test_package `cmake_layout(build_folder="$TMP")`
   强制 conan test 每次全新临时构建目录。
4. 重跑 `zsh ci/conan/build_and_test.sh archives/a/asyncfuture/1.1.0`：
   L1e 显示 `[ok] Negative test confirmed`，Build Summary 1/1，EXIT:0
   （日志：archives/a/asyncfuture/1.1.0/reports/w3-local-ci.log）。

## 适用范围

- 上游 CMakeLists 含 `export(PACKAGE)`/`install(EXPORT)` 的库；
- 本机/worker 曾手工 cmake 配置过该库源码（/tmp 或任意构建树）；
- W3/L1e 反测可信性受影响的所有适配任务。
- 反例边界：CI 干净环境无注册表污染，不会触发；仅有 $TMP 优化而无
  注册表清理时仍可能误判。

## 查重

- similar_to: E225（test_package 临时布局——同族"缓存致反测失真"，机制不同）
- caused_by: `export(PACKAGE)` 手工构建残留用户包注册表
- prerequisite_of: W3/L1e 反测可信性
- conflicts_with: 无