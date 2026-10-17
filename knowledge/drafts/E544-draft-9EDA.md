# E544 — autotools config.sub 缺 linux-ohos 内核/OS 组合校验分支（E007 补丁脚本盲区）

## 错误特征
```
configure: error: /bin/sh ././config.sub aarch64-unknown-linux-ohos failed
Invalid configuration `aarch64-unknown-linux-ohos': Kernel `linux' not known to work with OS `ohos'.
```
上游日志：isl 0.28 configure（2026-09-16，task isl-0.28-r01-pc4-20），运行 `scripts/patch-autotools-ohos.pl config.guess config.sub`（E007 方案，评分 4/5）后，`./config.guess` 已能输出 `aarch64-unknown-linux-ohos`，但 `./config.sub` 拒绝该三元组。

## 触发条件
- 构建系统: autotools
- 阶段: configuration（config.sub 三元组校验）
- 平台: HarmonyOS PC（aarch64），运行 E007 patch-autotools-ohos.pl 之后

## 根因分析
E007 的 patch-autotools-ohos.pl 对 config.guess 与 config.sub 打了 OHOS 识别补丁（config.sub 加了 `ohos-linux` 三元组映射、`ohos*` OS 列表、`linux-ohos` os-基本映射），但**漏掉 config.sub 末尾的 `case $kernel-$os` 内核/OS 组合校验块**：合法组合列表 `linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* | linux-musl* | linux-relibc* | linux-uclibc*` 中没有 `linux-ohos*`，导致 `aarch64-unknown-linux-ohos` 落入 `*-*) echo "Invalid configuration ... Kernel \`linux' not known to work with OS \`ohos'"` 分支。
补丁脚本评分 4/5 说明其自检（`./config.sub aarch64-linux-ohos`）只验证了三元组映射路径，未覆盖 kernel/os 组合校验路径。

## 解决方案

### 推荐方案：config.sub 组合校验块加入 linux-ohos*
在 `case $kernel-$os in` 的合法组合列表末尾追加 `| linux-ohos*`（保持 case 头不变，仅追加分支；与 R02 实际修复一致）：
```bash
perl -0pi -e 's/(linux-uclibc\* )\)/$1| linux-ohos* )/' config.sub
```
验证：`./config.sub aarch64-unknown-linux-ohos` 返回 `aarch64-unknown-linux-ohos`。

### 备选方案
在 patch-autotools-ohos.pl 中补上该分支，使其自检覆盖 `aarch64-unknown-linux-ohos` 完整路径。

### 禁止做法
- ❌ 不要在 configure 命令行用 `--build=... --host=...` 绕过（E007 forbid_1：会导致 AC_RUN_IFELSE 全部按交叉编译跳过，生成的 config.h 与实际平台不匹配）。

## 验证
```bash
cd $BUILD_SRC_DIR && ./config.sub aarch64-unknown-linux-ohos   # 输出 aarch64-unknown-linux-ohos
./configure --prefix=$DEFAULT_PREFIX --with-int=imath          # 通过 build system type 检查
make -j4 && make check                                         # exit 0，16/16 PASS
```

## 关联条目
- 相关: E007（config.guess/config.sub OHOS 识别主条目，本条目为其组合校验盲区补充）
- 类似: E129（同为 autotools 配置期平台限制），E543（同为 clang/autoconf 探测兼容问题）
- 来源: isl 0.28 适配（isl-0.28-r01-pc4-20，2026-09-16）