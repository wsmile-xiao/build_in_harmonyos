# vrfy 990522 — HarmonyOS PC 适配说明

## 概况

`vrfy` 是邮件地址校验工具：解析地址后连接目标域的 SMTP 服务器执行 `VRFY`/`EXPN`，
并结合 DNS MX 查询与语法检查给出结论。

- 上游来源：Debian `vrfy`（orig tarball `vrfy_990522.orig.tar.gz`，1999 年）
- 形态：1998 年的 K&R 风格 C（`main.c`/`smtp.c`/`mxrr.c`…）+ 手写 Makefile
- 产物：`bin/vrfy`、`share/man/man1/vrfy.1`
- 依赖：无（系统解析器由 bionic libc 提供）
- 许可证：BSD-3-Clause（sendmail / UC Regents 风格）

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | K&R 风格 C | `-std=gnu89` + `-Wno-implicit-function-declaration`/`-Wno-implicit-int`/`-Wno-int-conversion`/`-Wno-deprecated-non-prototype` 等 |
| 2 | `stat.c` 用 glibc 专有 `sys_errlist`/`sys_nerr` | 补丁改用标准 `strerror()` |
| 3 | bionic 不导出 BIND 的 `_res` / `_getshort` | 新增 `ohos_compat.c` 提供 `struct __res_state _res` 与本地 `_getshort()`（大端 16 位）；`res_search`/`dn_expand`/`dn_skipname` 由 bionic libc 提供 |
| 4 | BSD `rindex()` 缺失 | `-DSYSV_STRCHR` 启用 `port.h` 的 `#define rindex strrchr` |
| 5 | Makefile 默认 `-lresolv`（OHOS 无） | `make RES= LIBS=` 覆盖 |
| 6 | 无上游测试 | N=0，rule4 不触发 |
| 7 | 无 `install(1)` / CLI 门禁 | `package()` 手工拷贝；软件级 `commands.json` |

## 测试

### 上游

上游无测试套件（Makefile 只有 all/install/man/clean/lint/dist）。

### 消费者测试（test_package）

`test_package/test_vrfy.sh` 共 **2** 条断言，真实运行安装后的 `vrfy`：

- `-V` 打印 `Version` 版本信息
- 不带地址运行时打印 `Usage` 用法

## 已知限制

- 未对真实 SMTP 服务器做端到端校验（CI 无外网/邮件环境）。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
