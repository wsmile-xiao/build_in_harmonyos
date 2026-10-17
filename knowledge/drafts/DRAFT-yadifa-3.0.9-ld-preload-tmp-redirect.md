# DRAFT-yadifa-3.0.9-ld-preload-tmp-redirect

## 症状（可复现）
OHOS 上运行把临时文件硬编码到 /tmp 的测试套件时，大量用例失败：
```
yadifa verify8 实测：860 用例中 145 处失败，错误均为
'Read-only file system'（/tmp 前缀路径；config 52 / fdtools 51 / filesystem 20 / ...）
```

## 根因
OHOS 对 /tmp 施加只读约束（HMDFS/沙箱），而上游测试套件的 main/框架把临时路径硬编码为 /tmp（yadifa 源码 56 处）。TMPDIR 类环境变量只对显式读取它的程序有效，对硬编码路径无效；逐处改上游源码成本高且污染适配 diff。

## 已尝试方案
- ❌ 逐组改上游源码路径：散落 56 处、跨多目录，diff 膨胀且升级困难。
- ✅ LD_PRELOAD 路径重定向 shim（yatest_tmpredir.c）：仅测试阶段注入，EROFS 失败 145 → 0（verify10 前 74 用例实测零 EROFS）。

## 最终方案
1. shim 拦截 11 个路径类 libc API（`dlsym(RTLD_NEXT)` 透传真实实现）：`open/openat/fopen/mkstemp/unlink/rename/mkdir/stat/access/remove/creat`；凡 `/tmp/` 前缀改写到 `$YADIFA_TEST_TMPDIR`。
2. 配方 `exports` shim 源码，`build()` 内 `cc -shared -fPIC` 编译为 .so。
3. `ctest` 阶段经 `test_env` 注入 `LD_PRELOAD=<shim.so>` 与 `YADIFA_TEST_TMPDIR=<可写目录>`；生产路径与打包产物不接触 shim。

## 适用范围 / 反例 / 解除条件
- 适用：OHOS 上硬编码 /tmp 的 C/C++ 动态链接测试套件（ctest/googletest/自研 main）。
- 反例：静态链接二进制（LD_PRELOAD 不生效）；仅查询 /tmp 后放弃的分支必须连 stat/access 一并重定向（已覆盖）。
- 解除条件：上游改造为 TMPDIR 感知后可移除；/tmp 恢复可写后 shim 自动成为无害透传。

## 查重与新增价值
- 同族在池草稿 `DRAFT-ohos-otmpfile-tmpdir-shim` 组分③：源码级 test_tmp_dir(TMPDIR 感知) 方案，要求上游有集中式临时目录配置点。
- 本条是 **LD_PRELOAD interposition** 通道：适用于路径硬编码散落多处、无法或不便改源码的套件。同症状（/tmp EROFS）、不同解法，按 §6.2「组合型知识不判重」独立成条（similar_to 组网互指）。

## 触发实例
- yadifa/3.0.9 @ HarmonyOS PC（conan 2.29.1 + clang 15 OHOS），2026-09-21；shim 探针与 verify10 前 74 用例实测通过。
