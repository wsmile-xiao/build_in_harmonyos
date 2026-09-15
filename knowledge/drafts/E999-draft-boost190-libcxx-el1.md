# E999（草稿）: OHOS 本机会话 el1 bundle 路径污染 LD_LIBRARY_PATH 导致交叉测试产物 rc=127/符号缺失

## 现象

在 OHOS 设备本机（交互 shell）运行 `conan create`，上游测试与 test_package 的 ctest 阶段报：

```
Error loading shared library libc++_shared.so
Error relocating ./test_boost: _ZNKSt9bad_alloc4whatEv: symbol not found
```

而同一二进制在干净环境（`env -i`）或手动指定 toolchain lib 路径下 rc=0 正常运行。

## 根因

本机会话的 `LD_LIBRARY_PATH` 被某 el1 应用沙箱注入 `/data/storage/el1/bundle/libs/arm64`（含旧版 libc++_shared.so）。musl loader 命中旧库 → 新 toolchain 编译产物缺符号。conan 的 conanbuildenv 按 profile `[buildenv]` 拼接"当前 shell 的 LD_LIBRARY_PATH"，污染传导至 ctest。CI worker 独立 shell 无此问题。

## 修复/验证方法

```bash
# 1. 检查污染
env | grep el1
# 2. 干净环境重跑（判定配方是否真有问题）
nohup env -i HOME=$HOME \
  PATH=/data/storage/el2/base/files/interpreters/pip-global/bin:/data/service/hnp/bin:/usr/local/bin:/usr/bin:/bin \
  TMPDIR=$HOME/tmp \
  bash -c 'conan create ...' > create.log 2>&1 &
# 3. 二分定位污染段：逐段拼接 LD_LIBRARY_PATH 跑产物看 rc
```

判定标准：干净环境过 = 会话污染（配方正确，CI 可过）；干净环境也挂 = 配方问题。

## 实证

boost1.90 1.90.0（任务 #6080）：`/data/storage/el1/bundle/libs/arm64` 单段注入即复现 rc=127；剔除后 32 项上游测试 31 过、test_package ctest 100% 过。

- 关联：E002（/tmp 只读）、E068（b2 不兼容）
