# DRAFT-include-form-driven-include-dir-mount：消费者源码以命名空间目录前缀 include 依赖头时，依赖 include 目录必须挂载到命名空间目录父级（或重排 vendor 布局/镜像公共头进命名空间目录），错层直接挂载即 fatal error: file not found

主题归属：消费者 include 形态驱动的依赖 include 目录挂载层级归一（构建系统域）

> Contributor: why6666666 | Status: Draft | Updated: 2026-09-28
> Source: kodi-game-libretro 21.0.10 适配（libretro-common @ 50c15a88 / rcheevos v9.2.0 vendor pin）；同型实证 feat/kodi-inputstream-rtmp-21.1.2（librtmp registry 包）
> 判定: Curator B1 主候选（L2 跨库工程模式）+ Auditor CONFIRMED（路径 A+B）
> 对应: `knowledge/drafts/DRAFT-include-form-driven-include-dir-mount.kv`
> 最终编号 Exxx 由知识库主编确认

## 现象

消费者源码以**命名空间目录前缀**包含依赖头（`#include "libretro-common/libretro.h"`、
`#include "rcheevos/rcheevos.h"`、`#include "librtmp/rtmp.h"`），而依赖供给方
（registry conan 包的 includedirs 或 vendor tarball 的实际布局）与该形态不一致：
includedirs 指进命名空间目录**内部**、头平铺在 include 根、或头在 include 根而
消费者带前缀。按依赖方 includedirs 直接挂载，编译必然失败：

```text
consumer_lc.c:1:10: fatal error: 'libretro-common/libretro.h' file not found
consumer_rc.c:1:10: fatal error: 'rcheevos/rcheevos.h' file not found
```

头文件**实际存在**（在挂载目录内），错的是挂载层级——fatal error 指向的不是
"缺文件"而是"路径拼接不中"。

自包含真机探针实证（`reports/curator/probe-include-form/`，设备实跑）：
naive 挂载两例均 exit 1 且 fatal error（`naive-error.log`、`rc_naive-error.log`）；
按形态归一后两例均 exit 0（`normalized.bin`、`rc_norm.bin`）。

## 根因（机理链）

1. **工具实现**：编译器引号 include 按"每个 include dir + 头相对路径"拼接解析；
   `#include "ns/header.h"` 要求某个 include dir 下存在 `ns/header.h`，即
   **include dir 必须指向命名空间目录的父级**。
2. **触发命令**：任何把依赖 includedirs 原样注入消费者编译（`target_include_directories`
   / `include_directories` / conan cpp_info 传递）的构建。
3. **失败点**：依赖实际布局不满足父级要求 → 相对路径拼不中 → `fatal error: file
   not found` → 构建阻塞。三种已实证变体：
   - **变体 A（父目录注入）**：registry 包 includedirs 指进命名空间目录内部 →
     取其**父目录**注入（inputstream-rtmp 21.1.2 配方 `RTMP_INCLUDE_PARENT` 先例）；
   - **变体 B（tarball 子树重排）**：vendor tarball 的 include/ 子树无命名空间层 →
     解包后重排为 `<部署目录>/<命名空间名>/`（本 run：libretro-common →
     `libretro-common-include/libretro-common/`）；
   - **变体 C（平铺头镜像）**：公共头平铺在 include 根 → 镜像为
     `<部署目录>/<命名空间名>/*.h`（本 run：rcheevos → `rcheevos-include/rcheevos/`，
     等价上游 depends 的 `include/<project>/` 安装布局）。
4. **归类**：build-system（编译 include 解析面）；阻塞面 = 构建失败（探针实证），
   非运行期、非边缘观察。

诚实边界：本 run 与 inputstream-rtmp run 均为**设计期预防**（无真实构建失败
日志，attempt2 一次通过）；阻塞面由自包含探针独立证实。

## 方案（配方层桥接，上游源码零修改）

主方案三变体按供给形态择一，判据统一为：**include dir 必须使
"<命名空间>/<header>.h" 相对路径可解析**。

- 变体 A（registry 包）：消费者侧取依赖 includedirs 的父目录注入；
- 变体 B（vendor tarball，include 子树无命名空间层）：解包时重排加命名空间层；
- 变体 C（vendor tarball，头平铺）：镜像公共头进命名空间目录。

**退路**（仅作兜底，不予自动化）：修改消费者源码 include 形态适配依赖布局——
污染上游 diff、随上游演进漂移。

**禁止项**：

- **禁止把命名空间头文件散拷至 include 根**：破坏命名空间、跨库头名碰撞风险，
  掩盖 kodi-addon-dev 缺失类真因（同 P012 精神）；
- **禁止逐子目录堆叠 -I / 罗列深层路径**：脆弱、掩埋"挂载层级"根因；
- **禁止用 C_INCLUDE_PATH 类环境变量兜底错层**（见下方 P-ENV-001 挂钩）。

## 判别（三行定位）

```sh
# 1) 消费者是否为命名空间前缀 include（非 <标准头> 且带目录斜杠）：
grep -rnE '#include\s+["<][a-z0-9_-]+/[A-Za-z0-9_.-]+\.h[">]' src | head

# 2) 依赖头实际布局（命名空间层是否存在、includedirs 指向哪层）：
find <dep-include-dir> -name '<header>.h' ; grep -n 'includedirs' <dep-recipe>/conanfile.py

# 3) 错配复现（最小 TU + clang -I 即可判生死，无需完整构建）：
printf '#include "ns/hdr.h"\nint main(void){return 0;}\n' > t.c && clang -I<dep-dir> t.c -o /dev/null
```

## 验证（真实证据）

- 自包含真机探针：`reports/curator/probe-include-form/run-probe.sh`（同目录
  `probe-transcript.txt` 为原始命令转录；任何有 tar/clang 的 shell 可独立复跑，
  不依赖本 run 日志路径）。naive 挂载 exit 1（两例 fatal error 日志在案），
  归一后 exit 0（`normalized.bin`、`rc_norm.bin`）。
- 工程实例：kodi-game-libretro 21.0.10 配方按变体 B/C 归一后，权威 CI FULL
  （`ci/conan/build_and_test.sh`，ohos-aarch64）attempt2 一次全绿（L0/L1/L1e/L4/L5
  pass，test_package dlopen 契约断言过）；第二实例 feat/kodi-inputstream-rtmp-21.1.2
  变体 A 同型通过。

## 适用边界

- **触发面**：任何消费者以命名空间前缀 include 依赖头、且依赖包（registry 包或
  vendor tarball）includedirs/布局与该形态不一致的项目；加载型插件与含命名空间
  头布局依赖的库（kodi 家族已 3 实例）高发。
- **非 OHOS 专有**：机理是编译器 include 解析语义，任何交叉/本地构建面同构。
- **反例**：消费者已用 `<header.h>` 平铺形态且依赖头在 include 根 → 直接挂载即
  可，无需归一；头确缺失（真 not-found）属依赖闭包断裂，另案处理。

## 关系

- **similar_to**：
  - `E277`（slug `build-vendored-to-staging`）：同为 "vendored 依赖供给形态与
    消费预期错配" 家族，但 E277 是 **build() 内子项目编译到 staging 的链接/
    配置面**（`Required library not found`/`undefined reference`），本条是
    **编译期 include 解析面**（`fatal error: file not found`）；E277 不处理
    命名空间消费者形态下的挂载层级归一；
  - `DRAFT-KODI01`（kodi 二进制插件配方 SDK 头自 xbmc tarball 选择性提取）：
    同为 "依赖供给形态重整"，但 KODI01 解决的是 kodi-addon-dev 缺失时的 SDK
    头**来源**问题，不处理挂载层级归一；本条三变体与其在同一配方内正交共存。
- **adjacent（相邻不重叠，逐项差异——均不处理命名空间消费者形态下的挂载层级归一）**：
  - `E447`（conan-recipe cache-variable bridge，SDL2 系）：桥接传递依赖 include
    路径到 CMake cache 变量，解决的是**跨 CMake 项目的变量传递**，不改变挂载层级
    判定本身；
  - `E322`（header-only-cmake-interface-recipe）：header-only 依赖的 INTERFACE
    target 配方形态，解决**包类型/导出面**，其 includedirs 语义不涉及命名空间
    前缀 include 的父级挂载；
  - `DRAFT-EA-headeronly-dependency-chain`（EA 家族 header-only 依赖链干净构建）：
    解决 header-only 依赖链在 conan 下的**干净构建闭环**，不涉及挂载层级归一。
- **误引更正**：Curator 初稿曾引 `E215` 作 similar_to；经 Auditor 核对，E215 为
  LuaRocks/Busted 测试域条目（path-b-with-consumer-validation），与本条机理无关，
  已删除该引用。

## 查重（权威口径）

检索范围 = **权威 graph（worktree HEAD）：`knowledge/graph/index.tsv` E 系列
541 条**（实测 `E*.kv` 文件数 = index.tsv 行数 = 541）+ `knowledge/drafts/`
全目录 + 经验仓 `ophs_ci_review` 全目录。检索词：`include 形态|include form|
namespaced|挂载层级|mount|includedirs|libretro-common|rcheevos|librtmp` 等。
命中仅 E277/E322/E447/DRAFT-KODI01/DRAFT-EA-headeronly-dependency-chain，均为
上述相邻不重叠项；无覆盖性重复。注：Curator 报告去重节所引 "310 条" 为陈旧
计数，权威口径为 541（本条按 Auditor 修正）。

## principles 挂钩与缺口

挂钩 `P-ENV-001`（P014，实名**"环境变量与构建系统语义冲突陷阱"**）：本条遵循其
"优先构建系统原生机制、勿用 C_INCLUDE_PATH 类环境变量兜底"——挂载层级归一正是
include 解析域的构建系统原生机制方案；差异在于 P-ENV-001 只覆盖"环境变量与
pkg-config/make 等构建工具的语义冲突"，**不提供**"消费者 include 形态决定依赖
include 目录挂载层级"的判定规则。**显式声明 principles 缺口**：principles 现无
include 挂载层级专属 P 条目，建议主编评估新增（暂由本条承载该规则）。

## 元数据

- 配额：本 run 仅此 1 条 primary（未超限）
- 来源 run：kodi-game-libretro-21.0.10（candidate fff237bc1，权威 CI FULL PASS）
- 投递：随 feat/kodi-game-libretro-21.0.10 分支交付；promote 由知识库主编执行
