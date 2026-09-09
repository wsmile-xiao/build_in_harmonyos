# E544 — config.guess/config.sub 平台识别成对补丁模式（HarmonyOS）

## 错误特征
- `configure: error: cannot guess build type; you must specify one`（config.guess 不认识 HarmonyOS）
- `config.sub: invalid configuration aarch64-unknown-linux-ohos`（config.sub 不认 ohos）
- `configure: error: Kernel 'linux' not known to work with OS 'ohos'`（config.sub 第三处白名单缺失）

## 触发条件
- 构建系统: autotools（tarball 内嵌 config.guess/config.sub）
- 阶段: configuration
- 平台: HarmonyOS PC (aarch64)，目标三元组 aarch64-unknown-linux-ohos / aarch64-linux-ohos

## 根因分析
release tarball 打包的 config.guess/config.sub 版本旧于 OHOS 出现时间。两个脚本职责不同：
- config.guess 负责"猜"（uname -s = HarmonyOS → 需要专门识别分支，E007）
- config.sub 负责"验"（三处白名单缺一不可，E072）：
  1. `ohos-linux)` → `basic_os=linux-ohos` 映射（加在 android-linux 分支后）
  2. OS 白名单：`case $os in` 的 `gnu* | android* | ...` 行加 `ohos*`
  3. kernel-os 白名单：`case $kernel-$os in` 的 `linux-gnu* | ... | linux-musl*` 后加 `linux-ohos*`

只改其一会从一种报错切换到另一种。pmix 5.0.11（config.* 2021-01-25 版）实测：
guess+sub 成对修复后 `./config.guess` → `aarch64-unknown-linux-ohos`，
`./config.sub aarch64-linux-ohos` 与 `aarch64-unknown-linux-ohos` 均验证通过，configure 无需
--build/--host。

## 解决方案

### 推荐方案
1. 解 tarball 出 `.orig` 副本，`.work` 副本上手工修改
2. config.guess：加 `HarmonyOS:*) echo "${machine}-unknown-linux-ohos"; exit ;;`（置于 Linux 分支前）；
   同文件所有 `umask 077` 一并改 022（E543，pmix 实测 ×3 处）
3. config.sub：按上述三处白名单修改
4. per-file difflib 生成补丁 → conandata.yml `patches:` 列表固化
5. 验证：`./config/config.guess` 与 `./config/config.sub <guess 输出>` 均通过

### 回退方案
从已成功适配包（hwloc/pmix 归档）拷贝同年代补丁成果或整文件替换后叠加 umask 修复。

### 禁止做法
- ❌ `--build=aarch64-linux-ohos --host=...` 绕过（AC_RUN_IFELSE 失真，CI 同样失败）

## 验证
```bash
./config/config.guess                          # → aarch64-unknown-linux-ohos
./config/config.sub aarch64-unknown-linux-ohos # → aarch64-unknown-linux-ohos
grep -n "ohos" config/config.sub | head        # → 三处
```

## 关联条目
- 相关: E007（config.guess 识别）、E072（config.sub 白名单三处）、E543（umask 077 属主不可写）
