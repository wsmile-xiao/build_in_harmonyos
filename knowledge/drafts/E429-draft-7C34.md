# E429 — 上游 xode XML 解析器对无属性元素的空指针解引用（expat atts[0]==NULL）

## 错误特征

运行时崩溃，典型症状（消费者进程/宿主进程中调用模块解析 XML 时）：

```
Signal 11 (core dumped)            # 或 shell 报 Segmentation fault
```

定位到崩溃 PC 落在 `_xode_put_expatattribs`（`ldrb w8, [x8]` 且 `x8 = 0`，即解引用空指针）。
常见于 kamailio `src/modules/xmpp`（内嵌 jabberd xode 解析器）解析任何**无属性元素**时。

## 触发条件

- 构建系统: makefile（kamailio 自带 Makefile 体系）
- 阶段: runtime（解析 XMPP stanza / XML 文档时，非编译期）
- 依赖: expat ≥ 2.x（实测 2.7.3 与 2.8.2 行为一致）
- 触发形态: 被解析文档中存在**无属性元素**（如 `<body>`、`<status>`、`<show>`、`<a/>`）

## 根因分析

expat 的 start 回调对「无属性元素」传入的 `atts` 是**非 NULL 的数组指针，且 `atts[0] == NULL`**
（实测探针：`XML_SetElementHandler` + `XML_Parse("<a/>")` → `atts=0x…88, atts[0]=0`；
有属性元素则为通常的 `name/value` 交替数组）。该语义跨 expat 版本一致，与平台无关。

kamailio xode 解析器（`src/modules/xmpp/xode_from.c`）的循环条件只判了 `atts` 本身：

```c
if(atts == NULL)
    return;
while(*(atts[i]) != '\0') {        /* ← 直接解引用 atts[i]，首次迭代 i=0 即解引用 NULL */
    xode_put_attrib(current, atts[i], atts[i + 1]);
    i += 2;
}
```

因此任何无属性元素都会命中 `*NULL` → SIGSEGV。

## 解决方案

### 推荐方案

在循环条件补 `atts[i]` 判空（最小改动，有属性元素行为完全不变）：

```c
while(atts[i] != NULL && *(atts[i]) != '\0') {
    xode_put_attrib(current, atts[i], atts[i + 1]);
    i += 2;
}
```

参考实现（本仓已落地）：`archives/k/kamailio-xmpp/6.0.6/patches/0001-src-modules-xmpp-xode_from.c.patch`

### 禁止做法

- ❌ 删除或跳过 `#include <linux/netlink.h>` 之类"绕开"动作（与本题无关，且会丢功能）
- ❌ 把 `atts == NULL` 之外的判断写成空壳 stub / 直接 `return`（会静默丢弃全部属性）
- ❌ 因崩溃而禁用 XML 解析路径（模块核心功能丧失）

## 验证

```bash
# 1) 纯 expat 探针：确认 expat 对无属性元素的回调入参
#    期望输出：START name=a atts=<非NULL> atts[0]=0 (数组首元素为 NULL)
# 2) 模块侧：装 SIGSEGV handler 调 xode_from_str("<a/>")，修复后应返回非 NULL 节点
# 3) 修复后消费者用例：xode_from_str 解析 <presence from="..."><status>online</status></presence>
#    并断言 xode_get_name / xode_get_attrib / xode_get_tagdata / xode_to_str 正确（12/12 PASS）
```

## 关联条目

- 相关: E091（OHOS `linux/socket.h` 与 musl `sys/socket.h` 的 `sockaddr_storage` 重定义；同属"平台头文件/运行时语义差异"类）
