# DRAFT-13577: 依赖包的 `DT_NEEDED` 记构建机绝对缓存路径 → 干净机器上装载失败

## 症状

同一条配方、同一个提交：

- 构建机（缓存目录恰好存在）上 `conan create` 全绿，上游 ctest 6/6；
- 干净 CI worker 上**任何用例都跑不起来**：

```
Error loading shared library /storage/Users/currentUser/.conan2/p/kcore5e32ca1a86bf8/p/lib/libKF6CoreAddons.so:
(needed by /storage/Users/currentUser/.cache/conan2/p/kcras79f184640262f/p/lib/libKF6Crash.so)
```

失败与用例内容无关（全部 N 项同时挂），CI 的门禁诊断通常归类成「编译失败」，容易
被误当成源码/补丁问题去修，实际编译阶段是成功的。

## 根因

链接时若被链接的共享库**自身没有 SONAME**，链接器会把命令行上给出的
**完整路径**（而不是库名）写进 `DT_NEEDED`。已发布的部分 KF6/Qt6 包属于这种情况：

```
readelf -d <某个用例二进制或依赖库> | grep NEEDED
  (NEEDED)  Shared library: [/storage/Users/currentUser/.conan2/p/kconf7325dff05dfef/p/lib/libKF6ConfigCore.so]
```

装载器对**含 `/` 的 `DT_NEEDED`** 不查 `LD_LIBRARY_PATH`、不查 `rpath`/`RUNPATH`，
而是直接按该路径 `open()`：

- 构建机上该缓存目录存在（就是本机）⇒ 一切正常；
- 干净 worker 上不存在 ⇒ `dlopen`/启动即失败。

所以「本地绿、CI 全挂」在依赖这类预编译包时是**必然**结果，而不是环境抖动。

## 最小复现

任意依赖「无 SONAME 的共享库」的包，在一台没有该构建机缓存目录的机器上运行
其产物：

```bash
# 在干净容器/另一台机器上（无 /home/<builder>/.conan2/p/... 目录）
readelf -d <bin> | grep NEEDED | grep '^\s*(NEEDED).*\[/'
# 有输出即为命中；直接运行该 ELF 会报 Error loading shared library <绝对路径>
```

判定命令（在能构建的机器上自查，避免带着问题去撞 CI）：

```bash
readelf -d <bin-or-lib> | grep NEEDED | grep -c '/'
```

非 0 即说明产物把绝对路径写进了依赖表。

## 已试过的失败方案

1. **只加 `LD_LIBRARY_PATH`**：对含 `/` 的 `DT_NEEDED` 完全不生效（装载器跳过库搜索路径）。
2. **只加 `-Wl,-rpath,...` / `RUNPATH`**：同样对含 `/` 的条目无效（只影响按名字查找的条目）。
3. **改上游源码/加 patch 重新链接**：能修掉本包的产物，但**修不了依赖包**——失败来自
   已发布的 KF6/Qt6 包，改本地源码无济于事，且引入与适配无关的补丁。
4. **把依赖包重新 `conan upload` 覆盖**：同一版本号在制品仓无法覆盖（R37 版本号策略），
   且属于改动他人包，越权。

## 最终方案（本次采用）

在**测试/运行环境构造**阶段做一次「陈旧绝对路径修复」，不动产物、不打包：

1. 收集候选 ELF：构建树产物 + 依赖包内 ELF（`lib`/`lib64`/`bin`）；
2. `readelf -d` 取出所有以 `/` 开头的 `DT_NEEDED` 条目；
3. 路径已不存在的条目 → 在依赖包里找**同名库** → `os.makedirs(os.path.dirname(entry), exist_ok=True)`
   + `os.symlink(real_lib, entry)` 原路径重建；
4. 迭代到不动点（新接上的库可能又暴露新的绝对条目）；
5. 找不到同名库时 `output.warning` 显式告警，绝不静默继续。

可行性前置检查（本次实测）：把依赖闭包内所有绝对 `DT_NEEDED` 条目按 basename 在依赖包内
找同名库，**210 条 100% 可解析**（0 条无来源）；再合成验证「路径缺失 → 重建为指向依赖包
同名库的软链」这一步。

## 适用边界

- **适用**：目标产物（自己的或依赖包的）存在含 `/` 的 `DT_NEEDED`，且在另一台机器上运行；
  典型于「OHOS/Qt/KF6 交叉编译 + 依赖预编译包 + 运行上游测试或消费者用例」的场景。
- **不适用**：全部依赖都带 SONAME（`DT_NEEDED` 只有库名）时不触发；纯静态链接产物不涉及。
- **更干净的替代**：让依赖包在链接时带上 SONAME（`-Wl,-soname,libX.so`）后重新发布——
  属制品仓侧修复，需要依赖包维护者配合；本方案是消费者侧可独立完成的自救。
- **注意**：修复只应发生在测试/运行环境准备阶段，**不得写进打包产物**，也不得注入
  `/usr/local` 等系统共享前缀（避免污染 CI worker 上其他任务的构建）。
