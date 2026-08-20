# E333 — OHOS toybox gzip 仅支持短选项，GNU 长选项 --force/--best 使安装失败

## 错误特征

`make install-no-strip` / package() 阶段报 gzip 长选项不支持，典型日志如下：

```
gzip: Unknown option 'force'
make: *** [Makefile:425: install-no-strip] Error 1
ConanException
```

`gzip --force --best` 均报 `gzip: Unknown option force`，`gzip -f -9` 则 rc=0。

## 触发条件

- 上游 Makefile 在 `GZIP_MAN=true` 分支执行 `$(GZIP) --force --best $(MAN_PAGES)`（Makefile 第 425 行）；
- OHOS `/usr/bin/gzip` 为 toybox 实现（`readlink -f /usr/bin/gzip` 指向 `/system/bin/toybox`），仅支持短选项 `[-19cdfkt]`；
- 设备端 `/data/service/hnp/bin` 亦无 GNU gzip。

## 根因分析

OHOS `/usr/bin/gzip` 为 toybox 实现（`readlink -f /usr/bin/gzip` 指向 `/system/bin/toybox`），仅支持短选项 `[-19cdfkt]`，不支持 GNU gzip 的长选项 `--force`/`--best`。上游 MLton Makefile 在 `GZIP_MAN=true` 分支执行 `"$(GZIP) --force --best $(MAN_PAGES)"`（Makefile 第 425 行），package() 的 `install-no-strip` 阶段报 `gzip: Unknown option force` → rc=1 → `make: *** [Makefile:425: install-no-strip] Error 1` → ConanException。

设备端 `/data/service/hnp/bin` 亦无 GNU gzip，无 infra 级零配方改动方案，属上游平台工具链能力差异（上游假定 GNU gzip）。

## 解决方案

### 推荐方案

配方补丁把 install-no-strip 的 gzip 长选项改为 toybox 兼容短选项：`$(GZIP) --force --best $(MAN_PAGES)` → `$(GZIP) -f -9 $(MAN_PAGES)`，并在 conandata.yml 注册补丁。保留 `GZIP_MAN=true` 语义（man 页仍压缩），不跳过安装、不关闭 man 压缩、不改上游默认交付物。

```bash
# patch 0003 将 Makefile 第 425 行
#   cd "$(TMAN)" && $(GZIP) --force --best $(MAN_PAGES);
# 改为
#   cd "$(TMAN)" && $(GZIP) -f -9 $(MAN_PAGES);
make install-no-strip
# 验证：5 个 .gz 生成且 gzip -t 全部通过，"gzip: Unknown option" 计数=0
```

### 回退方案

若无法改命令，可设 `GZIP_MAN=false` 跳过 man 压缩。但改变了上游默认打包产物（man 页不再 gzip），掩盖 toybox 兼容性而非修复，仅作退路。

### 禁止做法 ❌

- 禁止 `apt install gzip` / `yum install gzip` / `brew install gzip` / 在设备上安装 GNU gzip——为单个库安装 GNU gzip 扩大构建工具依赖面，官方 CI 环境不保证提供，且不符合"发行包构建不应要求额外工具链"，导致依赖面扩散、CI 可移植性下降。
- 禁止 `GZIP_MAN=false` 后不修复、直接跳过 man 压缩——会改变交付产物并掩盖真实平台差异，man 页未压缩，交付物与上游不一致。

## 验证

```bash
readlink -f /usr/bin/gzip
# 指向 /system/bin/toybox 且 gzip --help 仅输出 "usage: gzip [-19cdfkt] [FILE...]"
# 定向复现：
gzip --force --best x
# gzip: Unknown option 'force'
gzip -f -9 x
# rc=0
make install-no-strip
# 5 个 .gz 生成且 gzip -t 全部通过，"gzip: Unknown option" 计数=0
```

Round 16 patch 0003 改 `gzip -f -9` 后 5 个 .gz 生成且 `gzip -t` 全过，Round 17/18 完整 CI gzip 错误=0。

## 关联条目

- 原则：P005
- 状态：draft
- 正式文档：doc/E333.md
- 相似条目：E010（toybox sed/expr）、E098（toybox 缺 install）——同属 OHOS toybox 命令能力差异类
- 事件源：MLton 20241230 Round 15 package() 首次到达 install-no-strip，gzip --force --best 失败（Makefile 425 Error 1，ConanException）；Round 16 patch 0003 改 gzip -f -9 后 5 个 .gz 生成且 gzip -t 全过，Round 17/18 完整 CI gzip 错误=0

---
*draft/E333-draft-MLTN.md · knowledge graph draft · MLTN*
