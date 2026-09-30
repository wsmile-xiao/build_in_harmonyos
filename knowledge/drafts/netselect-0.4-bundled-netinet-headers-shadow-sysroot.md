# DRAFT: 老网络工具自带的 netinet fallback 头被 `-I.` 抬到 musl sysroot 头之前

> 草稿（DRAFT）。与同目录 `netselect-0.4-bundled-netinet-headers-shadow-sysroot.kv` 成对。
> 实证来源：netselect 0.4 真机 shadow CI（2026-09-29，r1/r2 两轮编译失败）。

## 现象

上世纪网络工具（traceroute 派生：netselect、ping 系）常在源码树里自带
`netinet/{ip,ip_icmp,udp}.h` 兜底（当年为非 BSD 系统准备的），且 Makefile
`CFLAGS` 带 `-I.`。交叉编译到 OHOS（musl sysroot）时爆出大量类型错误：

```
./netinet/ip.h:51:2: error: unknown type name 'u_char'; did you mean 'char'?
./netinet/ip.h:58:2: error: unknown type name 'u_short'; did you mean 'n_short'?
  (note: sysroot .../netinet/in_systm.h: typedef uint16_t n_short;)
... 20 errors generated
```

两段式错误，注意区分：

1. **错误路径是 `./netinet/...`** → 自带 fallback 头被 `-I.` 抬到了 sysroot
   头之前，`#include <netinet/ip.h>`（尖括号）解析到了源码树副本。
2. **错误路径是 `netselect.c:NNN` 自身**（源码里局部变量/字段用了
   `u_char`/`u_short`）→ musl 不提供这些遗留 BSD typedef（E113 族）。

## 根因

- musl/OHOS sysroot 的 `netinet/*.h` 用可移植类型（`n_short`/`uint8_t`），
  与 glibc 头同布局同成员名，**系统头本身就是正确答案**；
- 源码自带的 fallback 头是 90 年代 BSD 原版，依赖 `u_char/u_short`；
- `-I.`（尖括号 include 也搜 -I 目录且优先于系统目录）让旧头遮蔽新头。

## 解决方案（零补丁，配方层）

在配方 `build()` 里用命令行 CFLAGS 覆盖上游 Makefile 默认值，一次解决两段：

```python
cflags = "-O2 -Wall -g0 -Du_char=uint8_t -Du_short=uint16_t"
self.run(f"make CC={cc} CFLAGS={cflags!r} -j1", cwd=self.source_folder)
```

- **去掉 `-I.`**：`<netinet/...>` 回落到 sysroot 头（成员名兼容，无需改源码）；
- **`-D u_char/u_short`**：把源码自身残留的 BSD typedef 宏映射到 stdint 类型
  （E113 add-cflags 思路；先 `grep -c` 确认只用到的类型集合，netselect 只有
  u_char=9 处、u_short=4 处）。

比打补丁删自带头更优：不动源码、无 patch 维护成本、对 glibc 构建无影响
（glibc 下这些宏是等价重定义）。

## 复用要点

- 错误消息里看**头文件路径前缀**定分母：`./netinet/` → 遮蔽问题（去 `-I.`）；
  `xxx.c:` → 源码类型问题（`-D` 宏映射）。
- 适用对象：所有"源码树里带 netinet/、sys/ 兜底头 + Makefile -I."的老网络
  工具（traceroute 族、BSD 工具移植）。
- 验证：编译错误数应从 ~20 直接到 0；若仍有剩余错误再逐个看（可能有
  `struct icmp` 字段名等次生差异）。
