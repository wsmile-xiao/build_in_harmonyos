# ForkUnion 3.0.2 Conan 适配笔记

## 源码与版本

- 官方仓库: https://github.com/ashvardanian/ForkUnion
- 源码提交: `7f52520ea00a6bf8e7a1f46348dad345ba361096`
- `VERSION`: `3.0.2`
- 下载校验: `5cc9c9dc0ad3815df8349760b2b9df649d5aafcfee92ba39a8f6717d9f0e3ec4`
- 该提交是 StringZilla 5.1.2 的 `forkunion` gitlink；因此适配为独立的 `forkunion/3.0.2` 包。

## 适配内容

1. 上游在 benchmark 配置路径中无条件获取 Taskflow v4.1.0。配方关闭 `FORKUNION_BUILD_BENCHMARKS`，并用补丁将 Taskflow/benchmark 区域置于该开关下；核心 C/C++ 测试仍保持开启。
2. OHOS SDK 没有 `pthread_setaffinity_np`。配方在 OHOS 设置 `FORKUNION_WITH_PLACE_THREADS_BY_AFFINITY=OFF`，并由 `forkunion::header` Conan component 传递 `FU_WITH_PLACE_THREADS_BY_AFFINITY=0` 给消费者。
3. OHOS SDK 没有 `Block.h`。补丁增加 `check_include_file("Block.h")`；头文件不可用时只跳过 Clang Blocks 测试，并输出明确的 CMake 状态信息，不把它计为通过。

## 鸿蒙设备 W3 证据

设备: OHOS 6.0 aarch64，OHOS Clang 15.0.4，Conan 2.29.1。

命令:

```sh
conan create archives/f/forkunion/3.0.2 \
  --profile:host="$REMOTE_REPO/ci/conan/profiles/ohos-aarch64" \
  --profile:build="$REMOTE_REPO/ci/conan/profiles/ohos-aarch64" \
  --build="*" -c tools.build:jobs=1
```

结果:

- CMake 配置探测到 `Block.h` 不存在，并输出 `Skipping forkunion_test_c_clang_blocks: Block.h is unavailable`。
- 上游 CTest 注册 5 个目标，实际执行 4 个：`forkunion_test_cpp17`、`forkunion_test_cpp20`、`forkunion_test_cpp23`、`forkunion_test_c11`，结果 `4/4 passed`。
- `forkunion_test_c_clang_blocks`：`1` 个有据跳过，原因是 OHOS SDK 缺少 `Block.h`。
- Conan `test_package` 消费者 `forkunion_consumer` 编译并运行成功，结果 `1/1 passed`。
- Conan `conan create` 最终退出码 `0`；生成静态库、共享库、CMake package config 和 pkg-config 文件。

未执行项:

- benchmark 未执行：它们不是核心正确性测试，且只会引入 Taskflow 下载；配方明确关闭 benchmark，避免把测试依赖误当作生产依赖。
