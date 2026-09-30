# DRAFT-10005: musl 的 strtol() 对无数字串置 errno=EINVAL，破坏 "errno != 0" 解析判据

- **来源**：memstat 1.2 适配（2026-09-29）
- **领域**：libc 差异（glibc → musl/OHOS）
- **邻近但不同**：E493（glibc 专有符号 `program_invocation_name`）、E032（musl 需 `_BSD_SOURCE`/`_GNU_SOURCE` 才暴露 dirent API）—— 均为 musl 主题但根因不同，本条未被图谱命中

## 现象

照 glibc 写的 C 代码迁到 OHOS 的 musl libc，三个"glibc 上看不见"的点同时出现在
读 `/proc` 的诊断类小工具上：

1. `memstat.c:67:39: error: use of undeclared identifier 'PATH_MAX'`
   —— 随后 `buff`/`path`/`perm` **级联出 20 条** `undeclared identifier`，
   `fatal error: too many errors emitted`，真实根因只有 1 条。
2. `warning: 'sscanf' may overflow; destination buffer in argument 5 has size 4,
   but the corresponding specifier may require size 5 [-Wfortify-source]`
3. `strtol: Invalid argument` + `exit 1` —— **编译干净，但一跑就死，一个字节都输出不出来**

## 根因

**(1)** glibc 下 `PATH_MAX` 由其它头文件传递引入（`sys/stat.h` → `bits/posix1_lim.h`），
musl 不传递引入。源码缺 `#include <limits.h>`，第一行缓冲区声明就挂。

**(2)** `sscanf` 的 `%4s` 写入 `char perm[4]`：4 个字符还需要结尾 NUL，共需 5 字节，
实际每次解析都越界写 1 字节。

**(3) 最隐蔽也最致命。** `readdir("/proc")` 的第一个条目是 `"."`。上游常见写法把
`errno` 当作"解析成功"的判据：

```c
errno = 0;
pid = strtol(ent->d_name, NULL, 10);
if (errno != 0) { perror("strtol"); exit(1); }
```

- **glibc**：`strtol` 无转换发生时**不碰 `errno`** → 该分支恒不触发，一切正常；
- **musl**：`strtol()` 对无数字字符串**显式 `errno = EINVAL`** → 循环第一次迭代
  就 `strtol: Invalid argument` + `exit(1)`。

在 glibc 开发机上**完全无法复现**，编译也无任何警告。

## 修复（三处均为纯 C，不引入任何平台宏，glibc 下行为不变）

1. 显式 `#include <limits.h>`
2. `perm[4]` → `perm[5]`（按 `%Ns` 的 N+1 定长）
   —— 不要改成 `%3s`，那会静默截断第 4 个权限字符
   （`/proc/<pid>/maps` 的权限位恰好是 4 字符 `rwxp`/`r--s`，截断会改变 shared 判定）
3. 用 `endptr` 区分"没发生转换"与"真的溢出"，保留上游溢出检测语义：

```c
char *endp;
errno = 0;
pid = strtol(ent->d_name, &endp, 10);
if (endp == ent->d_name) { continue; }   /* "." ".." "self" "sys" 等非数字条目 */
if (errno != 0) { perror("strtol"); exit(1); }   /* 仅数值溢出才致命 */
```

## 排查口诀

> 读 `/proc` 的程序在 musl 上"编译干净但一跑就 `strtol: Invalid argument`"，
> 几乎一定是这一条。先在 musl 上单独验证 `strtol` 行为，别在 glibc 上复现。

**附带结论**：`%ms`（scanf 的 glibc 分配修饰符扩展）在 OHOS musl 上是**支持**的，
实测 `sscanf("hello", "%ms", &p)` 编译与运行均正常，**不需要**为它打补丁 ——
不要凭"glibc 扩展"就预判要改。

## 三段式证据链（本条已实测）

| 步骤 | 状态 | 结果 |
|------|------|------|
| 不打补丁 | 编译期失败 | `use of undeclared identifier 'PATH_MAX'` 级联 20 条 |
| 只打 `limits.h` 一段 | 编译通过，**运行即死** | `memstat -n -p 1` → `strtol: Invalid argument` exit 1 —— 证明 (3) 是独立的第三个缺陷 |
| 三段全打 | 通过 | `conan create` rc=0，test_package **5/5 PASS**；用例 3/4/5（`-p <self>` 真扫 `/proc`、独占过滤、不存在 pid）即 (3) 的回归测试 |

反向验证：删除补丁后前两行复现，确认测试对补丁敏感、**非空壳**。

## 适用范围

- 读 `/proc/<pid>/maps`、`/proc/meminfo` 的诊断/统计类 C 工具（memstat/pmap/smaps 类）
- 1990–2010 年代手写 Makefile 的小 C 项目（无 autotools/cmake）
- 任何用 `readdir()` 遍历目录再用 `strtol`/`atol` 解析条目名的程序
- 任何在 `scanf` 家族用 `%Ns` 写定长 `char buf[N]` 的解析代码

## 关联文件

- `archives/m/memstat/1.2/patches/0001-memstat-c-musl-strtol-errno-and-path-max.patch`
- `archives/m/memstat/1.2/notes.md`（OHOS 适配要点 1/2/3 节）
- `archives/m/memstat/1.2/test_package/test_memstat.c`（用例 3/4/5 为回归测试）
