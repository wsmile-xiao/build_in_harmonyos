# webbench — OpenHarmony 编译档案

## 软件简介
WebBench（Radim Kolar, 1997-2004）是简单的 **fork 型 HTTP/代理服务器压测工具**：
`webbench -c <并发数> -t <秒数> <URL>` 会 fork 出 N 个客户端进程持续请求目标，
最后报告 `Speed=... pages/min` 与 `bytes/sec`。支持 HTTP/0.9–1.1、
GET/HEAD/OPTIONS/TRACE 方法、代理模式。许可证 GPL-2.0-or-later。

本次适配上游发布版 **1.5**（最后一次发布：2004-06-25）。

| 选项 | 说明 |
|------|------|
| `-c\|--clients <n>` | 并发客户端数（最多约 30000） |
| `-t\|--time <sec>` | 压测时长，默认 30 秒 |
| `-f\|--force` | 不等待服务器回复 |
| `-r\|--reload` | 发送 `Pragma: no-cache` |
| `-p\|--proxy <host:port>` | 通过代理压测 |
| `-9/-1/-2` | HTTP/0.9 / 1.0 / 1.1 |
| `--get/--head/--options/--trace` | 请求方法 |
| `-V\|--version` | 输出版本 |
| `-?\|-h\|--help` | 用法 |

## 上游源码获取
原始站点 `home.tiscali.cz` 已下线（HTTP 502），上游无 GitHub release、
无发行版 orig tarball、无其他权威镜像。本档案使用 Internet Archive 对
**原始上游 URL** 的逐字节快照（2011-07-27 捕获）。核查证据：

- 所有 200 状态的捕获（2011–2024）内容摘要一致，内容多年稳定
- 下载包 gzip mtime 为 `Fri Jun 25 10:01:59 2004`，与 `debian/changelog`
  中 1.5 的发布日期吻合
- 目录结构与上游自身 `make tar` 目标产物一致（上游自带 `debian/`）
- sha256 与 `/web/2020id_/` 端点下载副本逐字节一致，pin 可复现

源文件未做任何修改，sha256 即上游原始值。

## OHOS 适配要点
- **可移植性修复（关键）**：上游 `webbench.c` 包含残留的
  `#include <rpc/types.h>`（Sun RPC 头文件）。**glibc 2.26（2017）起把 Sun RPC
  移出 libc**，改由 libtirpc 提供，该头文件只在安装 `libtirpc-dev` 时存在；
  musl（因而 OHOS）从来没有提供过。因此该行在 **glibc≥2.26 与 OHOS 上都致命**：

  ```
  webbench.c:21:10: fatal error: rpc/types.h: No such file or directory
  ```

  这是**现代系统回归**，与 OHOS 无关——在当代 Debian/Ubuntu 上编译上游原始
  tarball 同样失败。该 include 是残留无用的：`MAXHOSTNAMELEN` 来自
  `<sys/param.h>`（OHOS 实测 = 64），`bzero`/`index` 来自 `<strings.h>`
  （OHOS 实测可用）。**删除该行即可，必要且充分。**
- **可移植性修复（关键，第二处）**：上游 1.5 **在 OHOS 上编译通过但运行结果全为 0**：

  ```
  Some of our childrens died.
  Speed=0 pages/min, 0 bytes/sec.
  Requests: 0 susceed, 0 failed.
  ```

  根因是 `bench()` 中父进程读取子进程结果前调用了
  `setvbuf(f,NULL,_IONBF,0);`。在 OHOS/musl 上，对**读流**做 `_IONBF` 之后，
  该流的 `fscanf` 返回 -1，且 `feof`/`ferror`/`errno` **全为 0**（无声失败），
  父进程遂走 `pid<2` 分支报 "Some of our childrens died."。

  OHOS 真机最小复现已逐项排除：**不带** `setvbuf` 的 `fscanf`、`fgets`+`sscanf`、
  `fread`、裸 `read()`、普通文件上的 `fscanf`、`sscanf` **全部正常**，
  只有 `setvbuf(_IONBF)` + `fscanf` 组合失败；glibc 上该组合亦正常。
  
  最小修复：删除该 `setvbuf` 调用（父进程循环次数固定为 `clients`，
  缓冲模式不影响解析结果）。修复后 OHOS 实测 `-c 20` 可达
  40340 pages/min、2017 请求全部成功、0 失败。
- **构建目标**：显式 `make webbench`，因为 `all` 目标还会调用 `ctags`。

## 依赖关系
- 无编译期/运行期第三方依赖（仅 C 运行时与 POSIX）
- 被依赖: 无（独立 CLI 工具）

## 上游测试
上游 **没有测试目标，也没有测试目录**：

- `Makefile` 目标：`all`、`tags`、`install`、`webbench`、`webbench.o`、`clean`、`tar`
- 无 `test` / `check` 目标；不存在 `tests/`、`test/`、`testing/`、`regression/`
- 仓库无 README / INSTALL / CONTRIBUTING

因此如实申报 **upstream_total = 0**。功能验证放在 `test_package/`：启动一个仅绑定
`127.0.0.1` 的本地 HTTP 服务（`python3 -m http.server`，OHOS 实测可用），对本地
服务执行真实压测并断言报告中失败请求数为 0——**不依赖任何公网站点**。

## 已知上游行为（如实记录）
`bench()` 以 `return i;` 结尾，而 `i` 是 `fscanf` 最后读入的子进程 pages 计数，
**不是状态码**。压测成功时退出码为任意 0-255 值（实测 223）。退出码仅在
`-V`（0）、无参数/`--help`（2）、连接失败（1）路径上有意义。

## 参考资料
- [WebBench 主页（已下线）](http://home.tiscali.cz/~cz210552/webbench.html)
- [上游 tarball 的 Internet Archive 快照](https://web.archive.org/web/20110727141838id_/http://home.tiscali.cz/~cz210552/distfiles/webbench-1.5.tar.gz)
