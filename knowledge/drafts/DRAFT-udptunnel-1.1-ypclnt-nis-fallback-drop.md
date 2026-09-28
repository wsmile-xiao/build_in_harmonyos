# DRAFT: 老网络工具的 NIS/YP 兜底在 OHOS/musl 必炸 —— 整段删除等价收敛

- 来源: udptunnel 1.1 适配（2026-09-27，主理-73 棒）
- 门禁证据: conan create G2 全绿；W3 本地 CI（setup.sh + build_and_test.sh）双过

## 错误面

```
host2ip.c:7:10: fatal error: 'rpcsvc/ypclnt.h' file not found
#include <rpcsvc/ypclnt.h>   /* YP */
```

## 根因

1996 年 ircd/talk 血统的 host2ip.c 把 NIS/YP 当 DNS 失败后的最后兜底：
无条件引入 `<rpcsvc/ypclnt.h>` 并调用 `yp_get_default_domain()`/`yp_match()`。
OHOS/musl 无 rpcsvc/ypclnt.h 与 yp_* 符号，头文件阶段即 fatal。

## 方案（平台无关、不带平台宏）

1. 删 `#include <rpcsvc/ypclnt.h>`；
2. 调 yp_* 的 else 兜底分支整体替换为 `in.s_addr = INADDR_ANY`
   （= 原分支的 Everything failed 路径，无 NIS 环境行为等价）；
3. 补丁说明写明等价依据。

## 预扫

```bash
grep -rn "ypclnt\|yp_match\|yp_get_default_domain" . --include="*.c" --include="*.h"
```

## 影响面

talk/ntalk/finger/rwho/rusers 等 BSD 系网络工具、内嵌 host2ip.c 的项目；
近年 glibc 发行版同样剥离了 rpcsvc 头，机制平台无关。

## KB 判定

- 全 KB（index.tsv 540 条 + drafts 1396 条 + doc/）grep ypclnt 零命中 → 无同层条目；
- 机制可跨库复用（BSD 网络工具族）→ B 判定升 create 的条件成立。
