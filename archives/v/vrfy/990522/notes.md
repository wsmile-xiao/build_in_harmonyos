# vrfy 990522 — HarmonyOS PC 适配说明

## 概况

`vrfy` 校验邮件地址（SMTP VRFY/EXPN + DNS MX）。产物 `bin/vrfy` + man。

- 上游：Debian `vrfy`（1999）
- 形态：1998 年 K&R C + Makefile
- 依赖：无
- 许可证：BSD-3-Clause

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | K&R C | `-std=gnu89` + 放宽告警 |
| 2 | `sys_errlist`/`sys_nerr` | 补丁改 `strerror()` |
| 3 | bionic 无 `_res`/`_getshort` | `ohos_compat.c` 自备 |
| 4 | BSD `rindex` 缺失 | `-DSYSV_STRCHR` |
| 5 | 默认 `-lresolv` | `make RES= LIBS=` |
| 6 | 无上游测试 / CLI 门禁 | N=0；`commands.json` |

## 测试

### 上游

无测试套件。

### 消费者测试（test_package）

`test_package/test_vrfy.sh` **2** 条断言：`-V` 打印 Version、无参数打印 Usage。

## 已知限制

- 未对真实 SMTP 服务器端到端校验。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
