# DRAFT-E5xx-gvariant-tuple-framing-offsets-reverse-order

## 现象

自研 GVariant 序列化器产出的二进制 **能过 magic 与总大小双校验**，但真实消费端
解析即崩。本 run 实证（gweather-locations Locations.bin 早期 shim，正序 framing）：

```
ok 1 /weather/radians-to-degrees_str
**
GWeather:ERROR:../libgweather/gweather-db.h:2129:db_world_get_timezones: assertion failed: (start <= end)
not ok /weather/no-code-serialize - GWeather:ERROR:../libgweather/gweather-db.h:2129:db_world_get_timezones: assertion failed: (start <= end)
Bail out!
Signal 6 (core dumped)
```

（libgweather TAP 全量日志：gw4-create4.log:409-413，关键行 :410。）

## 根因（GVariant 序列化语义三条易错规则）

1. **tuple/dict-entry 的 framing offsets 是逆序的**：每个非末尾变长子元素存一个
   offset，按子顺序【逆序】追加到容器尾；数组则是【正序】且每元素一个（含末
   元素）。两类容器方向相反，复刻实现极易写反（本 run 即栽在这里）。
2. **framing offset 字宽由容器序列化后总大小决定**：`<=255:1B / <=65535:2B /
   <=2^32-1:4B / 其余 8B`，序列化端按 `total = len(data) + offsize*len(ends)`
   迭代加倍定宽，反序列化端必须用同一规则（两端对称）。
3. **"magic + 总大小正确"不是正确性证据**：framing 写反产出的二进制能过
   magic/大小双校验，只有解析/参照 diff 才能暴露。

## 修复

序列化端对 tuple/dict-entry 的 offsets 逆序追加（数组保持正序），本 run 落点在
`shim/gi/repository.py:252-255`（候选分支 archives/g/gweather-locations/2026.2/ 内）：

```python
if offsets:
    # GVariant stores tuple framing offsets in REVERSE child order
    # (the first non-last child's offset is the last byte of the
    # container); array offsets stay in forward order.
    data = _append_offsets(data, offsets[::-1])
```

## 验证（两层，如实区分）

**第一层：112 字节缩小模型与真 GLib 参照逐字节 diff（判据所在）。**
附录 A（真 GLib 侧 `g_variant_new_parsed` 同型值 dump）+ 附录 B（复刻侧同型值）
编译运行后 sha256 对比：

| artifact | sha256 前缀 | 说明 |
|---|---|---|
| shim.bin | `ad63e3cd…` | 修复前复刻侧产物（正序 framing，122 字节，4B 字宽形态） |
| ref.bin | `222f25d1…` | 真 GLib 参照（122 字节）——两者字节发散，尾部 framing 字节 shim 正序 `07 0a 0d 23 26 32 3c 10 18 2e` vs ref 逆序 `38 26 23 0d 0a 07 46 2e 18 10` |
| shim2.bin | `e93f7904…` | 修复后复刻侧产物（112 字节） |
| ref2.bin | `e93f7904…` | 修复后真 GLib 参照——与 shim2.bin **逐字节相同**（twin-print.txt/twin2.txt 均 `size: 112`） |

**诚实边界**：字节一致的判定是在 112 字节缩小模型上做出的。

**第二层：全量制品反序列化。**
纯 python GVariant 反序列化器（17 项：magic、顶层 5 成员结构、规模下界、全部
children/parent/nearest/tz-hint/zones 索引界内、已知条目存在性）跑真实
Locations.bin（642680 字节）：17/17 PASS（test-locations-parse.log，
locations=8862/timezones=332/countries=245/metar=4004）。

两层职责不同：第一层给**字节级真值**（防自研反序列化器循环论证），第二层证明
**真实规模/嵌套深度下无坏 framing**（小模型 diff 挡不住规模相关错误）。两层全过
才算正确。

## 诊断次序与反例

- 推荐次序：magic → 全量反序列化（索引界内校验最先暴露坏 framing）→ 真 GLib
  参照逐字节 diff（缩小模型定位到具体规则）。
- 反例 1：只做消费端冒烟——漏掉仅在特定规模/嵌套深度触发的 framing 错误。
- 反例 2：只有自研反序列化器、无独立参照——循环论证（序列化器写反，解析器按
  同一错误理解解析，自洽但错误）。

## 附录 A：gvariant-ref.c（真 GLib 参照探针，31 行）

> 编译：`gcc $(pkg-config --cflags --libs glib-2.0) gvariant-ref.c -o gvariant-ref`
> （在任意有 GLib dev 的环境；本 run 在设备真机编译运行。）

```c
/* Reference serialiser: build the same world-DB-shaped GVariant with real
 * GLib (text-format parse) and dump the serialised bytes, so the
 * pure-python `gi` shim's output can be diffed byte-for-byte.
 * Debug tool only — not part of the package. */
#include <glib.h>
#include <stdio.h>

int
main (int argc, char *argv[])
{
  GVariant *world = g_variant_new_parsed (
    "(uint64 0x5747687442443130, "
    "{'AA': uint16 1}, "
    "{'BB': uint16 2}, "
    "{'tz1': (('n1', 'n2'), ['o1', 'o2'])}, "
    "[(('L1', 'z1'), 'r1', 'c1', (1.5, 2.5), 'i1', 'm1', "
    "uint16 3, byte 4, uint16 5, uint16 6, [uint16 7, uint16 8], [uint16 9, uint16 10])])");

  g_assert (world != NULL);

  world = g_variant_take_ref (world);
  GBytes *bytes = g_variant_get_data_as_bytes (world);
  gconstpointer data = g_bytes_get_data (bytes, NULL);
  gsize size = g_bytes_get_size (bytes);
  FILE *f = fopen (argv[1], "wb");
  fwrite (data, 1, size, f);
  fclose (f);
  gchar *printed = g_variant_print (world, TRUE);
  g_print ("printed: %s\nsize: %u\n", printed, (guint) size);
  return 0;
}
```

## 附录 B：shim-twin.py（复刻侧同型探针，33 行）

> `sys.path.insert` 的路径按待测 shim 所在检出目录调整（原始取自设备 deps tmp，
> 非持久位置）；运行必须用绝对路径 python3：
> `/storage/Users/currentUser/usr/local/bin/python3 shim-twin.py out.bin`。

```python
#!/usr/bin/env python3
"""Shim-side twin of gvariant-ref.c: same tiny world-DB value, same order.
Debug tool only — not part of any package."""
import sys

sys.path.insert(0, "/storage/Users/currentUser/tmp/oh-device-porting-v2/libgweather-4-4.6.0-deps/shimtest")
from gi.repository import GLib

INVALID_IDX = 0xffff

tz_val = GLib.Variant('((ss)as)', (("n1", "n2"), ["o1", "o2"]))
loc = GLib.Variant('((ss)ss(dd)ssqyqqaqaq)', (
    ("L1", "z1"),
    "r1", "c1",
    (1.5, 2.5),
    "i1", "m1",
    3, 4,
    5, 6,
    [7, 8],
    [9, 10],
))
world = GLib.Variant("(ta{sq}a{sq}a{s((ss)as)}a((ss)ss(dd)ssqyqqaqaq))", (
    0x5747687442443130,
    [("AA", 1)],
    [("BB", 2)],
    [("tz1", tz_val)],
    [loc],
))

data = world.get_data_as_bytes().get_data()
with open(sys.argv[1], "bw") as f:
    f.write(data)
print("size: %d" % len(data))
```

## 附录 C：第二层全量验证命令形态

```
/storage/Users/currentUser/usr/local/bin/python3 test_locations.py \
    <package_folder>/lib/gweather-locations/Locations.bin
```

（`test_locations.py` 为纯 python GVariant 反序列化器，17 项 check，随本 run
候选 archives/g/gweather-locations/2026.2/test_package/ 交付；对任意 GVariant
制品复用时按其顶层类型串改写 `TOP_TYPE`。）

## 参考

- 近邻条目：E243（生成器测试策略）、E281/E305（资源叶子包消费者验证）——均非
  同题（framing 语义本体），见 .kv similar_to。
- 环境注入类问题（ninja 绝对路径钉扎等）见
  DRAFT-E5xx-ohos-meson-detect-ninja-env-pin，与本条目互补不重叠。
- 本 run 姊妹条目：DRAFT-E5xx-ohos-buildhost-pygobject-gi-shim-pythonpath-bridge
  （shim 桥接方案本体）。
