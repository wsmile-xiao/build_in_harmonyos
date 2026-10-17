# E566 — 公共头文件与 ELF 动态库导出符号契约漂移：双向审计与最小别名修复

> 对应 KV：`knowledge/drafts/E566-draft-header-export-symbol-contract-drift.kv`
> 触发事件：libdrawtext 0.6 HarmonyOS PC 适配（archives/l/libdrawtext/0.6）

## 问题概述

上游 C 库的公共头文件声明了某个 API，但库的二进制从未导出该符号——
实现只在另一个名字下存在。上游自家的 examples/tools 恰好不走这条
声明路径，所以上游构建与演示全绿、缺陷完全静默。任何按头文件编程的
外部消费者直接调用该 API 必然链接失败（undefined reference）。

这不是 OHOS 特有问题，是库自身的 ABI 契约缺陷；交叉打包时 test_package
按头文件直接调用公开 API 就会把它暴露出来。同一库还可能同时存在反向
漂移（库导出符号但公共头不声明），两个方向都要审。

## 典型错误

```
clang test.c -o test -I<pkg>/include -L<pkg>/lib -ldrawtext
ld.lld: error: undefined symbol: dtx_get_glyphmap_image
>>> referenced by test.c
>>>               test.o:(main)

# dlopen/dlsym 视角：
# dlsym(handle, "dtx_get_glyphmap_image") → NULL
```

触发条件：
- 构建系统：任意（本例为自定义 sh configure → Makefile）
- 阶段：消费者链接期（库自身构建永远不触发）

## 根因

1. 头文件演进与实现脱节：drawtext.h 自 0.6 起声明
   `dtx_get_glyphmap_image` 并注释其用途，但实现源码里该函数从未
   存在——功能在 `dtx_get_glyphmap_pixels`（font.c:721）名下。
2. 上游无声明-导出一致性检查：无 CI、无 ABI 测试、无
   check-symbols 目标，漂移无声累积。
3. 上游自身代码不走该路径：examples/tools 的像素访问全走
   `dtx_save_glyphmap` 序列化与 `dtx_target_user` 回调两条公共
   路径，从不直接调用声明 API，缺陷被自家用法掩盖。
4. 反向漂移并存：`dtx_get_glyphmap_pixels` 在 0.6 头文件中无声明
   （导出未声明），双向契约都不成立。

## 适用范围

- 任何"公共头声明集 ≠ ELF 导出符号集"的 C/C++ 共享库打包场景；
- 上游无 ABI/符号一致性 CI 的老库演进（实现改名未同步头文件）；
- version script / visibility 策略调整后头文件未同步的库；
- OHOS Conan 适配的 test_package 按头文件直接调用公开 API 的
  一切场合（这本身就是暴露漂移的最有效探测器）。

## 不适用范围

- 条件编译导致的"缺失"：符号在 `#ifndef NO_OPENGL` 等条件块内，
  构建配置选择不编译它，属于设计而非漂移（判为非真实差异，不处理）；
- 依赖库版本过旧缺 API（见 E548，那是依赖侧回移问题）；
- libc 级符号缺失/语义不可用（见 E245/E302/E320）；
- 测试目标没链接 fallback 对象（见 E229，那是构建目标链接问题）。

## 检测流程

1. 双向符号审计（在 Conan 包安装产物上，非构建树）：

```sh
# 导出集
nm -D --defined-only <pkg>/lib/libX.so | awk '$2 ~ /^[TtWwBbDd]$/{print $3}' | sort -u > exported.txt
# 头声明集（按项目公共头实际风格调整正则）
grep -oE '^[a-zA-Z_][a-zA-Z0-9_ *]+\b([a-z][a-zA-Z0-9_]*)\(' <pkg>/include/X.h \
  | grep -oE '[a-z][a-zA-Z0-9_]*\($' | tr -d '(' | sort -u > declared.txt
# 声明未导出
comm -23 declared.txt exported.txt
# 导出未声明
comm -13 declared.txt exported.txt
```

2. 对差集中每个符号做源码级核实：
   - `grep -rn "sym" src/`：找实现名、签名、所有权语义；
   - 检查条件编译块（`#ifndef XXX` / `#ifdef XXX`）归属；
   - 检查是否有 `#define` 宏映射或 version script 过滤。

3. 等价性判定（能否安全别名）：
   - 返回类型一致（声明 int vs 实现指针 → **不等价，禁止别名**）；
   - 参数列表一致；所有权语义一致（借用 vs 拷贝）。

## 修复流程（通用算法）

1. **声明未导出 + 存在等价实现**：库内加最小转发别名（保留原符号
   不动，不破坏既有消费者），公共头同步注释两符号等价关系：

```c
/* forwarding alias: header promises sym_image, implementation is
 * sym_pixels — same signature, same borrowed ownership */
unsigned char *dtx_get_glyphmap_image(struct dtx_glyphmap *gmap)
{
    return dtx_get_glyphmap_pixels(gmap);
}
```

2. **导出未声明**：公共头补齐声明（反向漂移修复），双向一致。
3. **声明返回类型与实现真实返回类型冲突**：禁止别名（int↔指针是
   ABI 错误），消费者改用头文件中真实存在的替代 API，fail-closed
   报告上游缺陷。libdrawtext 头注释写的是 int 返回，但实现返回
   `unsigned char *`——头注释本身是错的，以实现为准判定。
4. 补丁登记：`patches/0001-*.patch` + conandata.yml `patches:` 段
   （`patch_type: bugfix`）+ build() 首行 `apply_conandata_patches(self)`
   （a52dec/0.7.4 先例）。

## 验证流程

1. **无补丁反向验证**：不打补丁构建，消费者直接调用声明 API 必须
   链接失败（undefined reference to `dtx_get_glyphmap_image`）——
   证明缺陷真实存在且补丁是修复的必要条件。
2. **有补丁正向验证**：打补丁构建，消费者编译、链接、运行全通过；
   别名符号与实现符号运行时返回同一结果/指针（真别名而非桩）。
3. dlopen + dlsym 补充检查：别名符号在动态符号表可解析。
4. `nm -D` 复核：双向差集按白名单清零——声明未导出侧豁免条件编译
   符号（`#ifndef NO_OPENGL` 等块内）；导出未声明侧豁免内部头
   （src/ 内部 .h）声明的实现符号与链接器产物（`_fini`/`_init`，
   老库无 visibility 控制的常态，公共头从未承诺，非契约漂移）。
   豁免后两侧均为 ∅。

## 安全边界

- 别名修复必须源码级证明签名/所有权/语义等价，证明不了就不做；
- 只加别名不删原符号——既有消费者（可能已链接原符号）零影响；
- 补丁必须最小、独立、登记 conandata.yml，走标准 Conan 补丁生命
  周期（见 DRAFT-libstatgrab-0.92.1-conandata-patch-lifecycle：
  未登记的补丁不导出、不应用、不可审计）；
- 条件编译符号（NO_OPENGL 块内）不改、不补、不删——那是构建
  配置的选择，不是契约缺陷。

## 禁止方案

- **删头声明掩盖**：把 `dtx_get_glyphmap_image` 从头文件里删掉，
  缺陷"消失"但下游按旧头编程的程序依然链接失败，且丢失上游文档
  化的 API 承诺。
- **#define 静默替换**：`#define dtx_get_glyphmap_image dtx_get_glyphmap_pixels`
  改写消费者源码语义，掩盖契约缺陷且与 ABI 视图不一致。
- **全局放开导出**：为修一个符号把所有内部符号 visibility 改
  default，ABI 面膨胀、符号冲突风险。
- **测试绕行**：test_package 回避该 API 只测别的，漂移继续静默。

## libdrawtext 真实案例

| 项 | 内容 |
|---|---|
| 库 | libdrawtext 0.6（github.com/jtsiomb/libdrawtext） |
| 声明未导出 | `dtx_get_glyphmap_image`（drawtext.h:121，无条件声明） |
| 等价实现 | `dtx_get_glyphmap_pixels`（font.c:721，返回 `gmap->pixels` 借用指针） |
| 反向漂移 | `dtx_get_glyphmap_pixels` 0.6 头文件无声明 |
| 条件非真实 | `dtx_vertex_attribs`（drawgl.c `#ifndef NO_OPENGL` 块内） |
| 签名核实 | 两符号同为 `unsigned char *(struct dtx_glyphmap *)`，借用指针语义一致 → 等价可别名 |
| 补丁 | `patches/0001-glyphmap-image-export.patch`（别名 + 反向补声明，patch_type: bugfix） |
| 反向验证 | 无补丁：undefined reference to `dtx_get_glyphmap_image`；有补丁：链接+运行通过，image==pixels 指针相等断言通过 |

## 与相似条目的区别

- **E229**（fallback 对象未链接）：那是测试目标的链接对象缺失，
  库本身契约完好；本条是库自身的头↔导出契约漂移。
- **E104**（缺 version_script.ver 文件）：那是构建输入文件缺失
  导致链接失败；本条是符号名漂移，构建输入完整。
- **E530**（X11 无 server 测试方法）：那是消费者测试方法论；
  本条的双向符号审计可以并入其测试设计，但根因与修复不同。
- **E548**（依赖版本回移）：那是依赖库版本过旧缺 API，回移
  static inline 兼容层；本条是库自身声明与导出不一致。

## 跨库复用方式

1. 对任何无上游 ABI CI 的 C 库打包，test_package 前先跑双向审计
   （检测流程第 1 步两条 comm 命令，可直接照抄）；
2. 差集符号按"检测流程 2-3"做源码级核实与等价性判定；
3. 等价 → 最小别名补丁（修复流程 1-2）；不等价 → 替代 API +
   fail-closed 报告；
4. 验证流程四步（反向验证/正向验证/dlsym/nm 复核）全部执行。

## 关联条目

- E229、E104、E530、E548（similar_to）
- DRAFT-libstatgrab-0.92.1-conandata-patch-lifecycle（补丁生命周期
  登记，别名补丁必须遵守）
