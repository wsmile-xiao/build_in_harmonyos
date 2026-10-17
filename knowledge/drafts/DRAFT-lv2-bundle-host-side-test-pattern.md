# DRAFT-lv2-bundle-host-side-test-pattern — LV2 插件 bundle 的宿主侧实测范式

**severity**: 2 ｜ **phase**: testing ｜ **类别**: test, audio, headers, portability, ohos

为 LV2 插件包写消费者测试（test_package）时踩到的四类陷阱，以及 OHOS 平台上的取证替代方案。

## 1. 端口表：`lv2:port` 是多元素列表，元素内可嵌套

```turtle
lv2:port [
        a lv2:InputPort, lv2:ControlPort ;
        lv2:index  2 ;
        lv2:portProperty lv2:enumeration ;
        lv2:scalePoints [ … ] ;        # ← 元素内还能嵌套列表
        lv2:default 0 ;
], [
        lv2:index 3 ;
        …
], [ … ] ;
```

**症状**：按「第一个 `]`」截断 → 只解析出前几个端口 → 未连接端口指针为 NULL → 插件 `run()` 解引用
→ `Signal 11 (core dumped)`。实测 casynth 共 23 个端口，错误解析只得到 3 个（索引 0..2）。

**修法**：从每个 `lv2:port` 起用**括号深度**匹配元素边界：

```c
for (char *q = open; *q; q++) {
    if (*q == '[') depth++;
    else if (*q == ']' && --depth == 0) { close = q; break; }
}
```

再逐元素解析（元素间 `,` 分隔、列表以 `;` 结束），取 `lv2:index`、`InputPort/OutputPort`、
`AudioPort/ControlPort/CVPort/AtomPort`、`lv2:default`（控制端口实测用 default，避免 0 值触发除零/NaN）。

> 自检：解析出的端口数应与 `grep -c 'lv2:index' <bundle>/<plug>.ttl` 一致（多 descriptor 取 max index + 1）。

## 2. `activate` / `deactivate` 是可选回调

LV2 规范里 descriptor 的 `activate` / `deactivate` 可以为 **NULL**（casynth 就没有实现）。
宿主无条件调用 → 测试自身 SIGSEGV，还会掩盖真正的插件问题：

```c
if (desc->activate)   desc->activate(instance);
… run() …
if (desc->deactivate) desc->deactivate(instance);
```

## 3. 端口连接策略：连 0..max，而不是「只连自己的」

运行时无法从 `LV2_Descriptor` 得知端口数；最稳妥的是按 `.ttl` 的 max index 连接 `0..max`
（每个 index 给一块足够大的清零缓冲：音频/CV/控制用 float，atom 用零字节序列）。
插件会忽略不属于自己的 index（octolo 打印 `UNKNOWN PORT YO!!`，无害）。

音频输入喂 440 Hz 正弦、控制端口写 `lv2:default`、音频输出断言 `isfinite()`，
这样测试真正跑了 DSP（满足 R34），而不是只 dlopen 一下。

## 4. OHOS 平台取证：`/proc/self/maps` 不可读

本机 OHOS 上读 `/proc/self/maps` 直接失败（SELinux），因此：

| 目标 | ❌ 不可用 | ✅ 替代 |
|------|----------|--------|
| 插件镜像来自本次包路径 | 在 `/proc/self/maps` 里找 so 路径 | `dladdr(dlsym(h,"lv2_descriptor"), &info)` → `info.dli_fname` 与 dlopen 路径比对 |
| DT_NEEDED 依赖链已解析 | 同上 | `dlopen(soname, RTLD_NOW \| RTLD_NOLOAD)` 非 NULL（**必须在 `dlclose` 之前**） |

另：ELF 身份（`ELFCLASS64`/`EM_AARCH64`/`ET_DYN`）与「二进制里无共享前缀字面量」可直接读文件字节判定，
无需平台接口，适合作为鸿蒙特有断言。

参考实现：`archives/i/infamousplugins/0.3.2/test_package/{test_lv2_plugins.c,ohos_specific_test.c}`
（实测 79 + 128 = 207 项断言全通过）。
