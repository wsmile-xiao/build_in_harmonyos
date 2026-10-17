# DRAFT-pktstat-185: musl 移除历史宏 `IPPORT_USERRESERVED`，老 C 网络工具编译失败

- **来源**：pktstat 1.8.5 适配（2026-10-01）
- **领域**：libc 差异（BSD/glibc → musl/OHOS）
- **邻近但不重复**：DRAFT-10005（musl `strtol()` 对无数字串置 `errno=EINVAL`，破坏 `errno != 0` 解析判据）——同为 musl 主题，但根因是"宏缺失"而非"函数行为差异"

## 现象

`tcp.c:121:19: error: use of undeclared identifier 'IPPORT_USERRESERVED'`
——**孤立的单行报错**，没有级联，随后 `make` 停在 `tcp.o`。

## 根因

OpenHarmony 的 libc 是 musl。musl 的 `<netinet/in.h>` 只定义 `IPPORT_RESERVED`（1024），
**删掉了历史宏 `IPPORT_USERRESERVED`**，而 BSD 与 glibc 一直把它定义为 1023（保留区之下的最高端口）。

1990-2010 年代写成的、按端口号决定是否去 `/etc/services` 查服务名的程序就会挂：

```c
/* pktstat tcp.c:120-126 */
else if (port > IPPORT_USERRESERVED)
    se = NULL;
else
    se = getservbyport(htons(port), "tcp");
```

实测 sysroot 佐证：

```
$ grep -n 'IPPORT_' <ohos-sysroot>/usr/include/netinet/in.h
73:#define IPPORT_RESERVED 1024          # IPPORT_USERRESERVED 不存在
```

## 处方

在使用该宏的源文件 include 区补一个**由 libc 宏集合驱动**的兜底定义，不引入任何平台宏：

```c
#ifndef IPPORT_USERRESERVED
# define IPPORT_USERRESERVED 1023
#endif
```

三条要点：

1. **守卫条件是"libc 有没有给这个宏"，不是"当前是不是 musl/OHOS"。**
   同一个补丁在 BSD/glibc 上是 no-op（宏存在，走 libc 自己的值），在 musl 上才生效。
   这正是 R8 要求的形态——不要写 `#ifdef __OHOS__`。
2. **取值必须是历史值 1023**，不要写成 `IPPORT_RESERVED - 1` 之类推导式：
   语义是"保留区之下的最高端口"，写死常量最不容易被上游宏改动带偏。
3. **不要改比较表达式**。`port > IPPORT_USERRESERVED` 的语义（≤1023 才查 `/etc/services`）
   必须逐字保留。把它换成 `port >= 1024` 或直接删掉 `getservbyport` 分支都属于"重写上游逻辑"，
   而且会**静默丢功能**——界面照常刷新，只是服务名从 `http`/`ssh` 退化成端口号，肉眼很难发现。

## 为什么这个错容易被漏掉

- 单行报错，不像 `PATH_MAX` 那样级联出 20 条，`conan create ... | tail -40` 很容易刚好把它截断掉；
- 报错行在函数体中间、离 include 区很远，容易被误判成"逻辑写错了"而去改比较逻辑或加 cast；
- 改完之后**功能表面看不出变化**（见要点 3），没有回归测试兜底就会一路带进制品。

## 排查口诀

> 老网络工具迁到 musl，只报 `IPPORT_USERRESERVED` 一个错 → 直接补宏，不要动逻辑。
> 同类兄弟宏一并检查：`IPPORT_HIGHSERVERS`。

## 验证

- **(a) 不打补丁**：`tcp.c` 编译期失败（单行 `use of undeclared identifier 'IPPORT_USERRESERVED'`），`tcp.o` 不生成。
- **(b) 打上补丁**：`conan create` rc=0，产出 `bin/pktstat`（aarch64 PIE，`DT_NEEDED` 仅 `libc.so` —— libpcap/ncurses 在仓内均为纯静态包）。
- **(c) 反向验证**：移除补丁后 (a) 精确复现，证明补丁必要且充分、测试对补丁敏感、非空壳。
- 行为不变：`tcp_lookup()` 仍只对端口 ≤ 1023 查 `/etc/services`。

## 适用面

- 任何用 `IPPORT_USERRESERVED` 判断是否解析服务名的 C 程序（pktstat / nmap / scan 类老工具）；
- 1990-2010 年代 BSD 血统的小 C 网络工具；
- 任何靠 BSD/glibc 隐含宏集合才能编译的老代码（同类兄弟：`IPPORT_HIGHSERVERS`）。
