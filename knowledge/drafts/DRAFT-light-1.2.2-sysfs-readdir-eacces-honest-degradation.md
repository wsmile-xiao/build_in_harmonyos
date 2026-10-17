# sysfs 整树 readdir 对非特权进程返回 EACCES，而 stat 成功

## 场景

适配 `light`（背光/LED 调节 CLI）时，功能面全部落在 `/sys/class/backlight` 与
`/sys/class/leds` 的枚举上。构建面（autotools/编译）与此无关，必须先给能力面定性，
否则测试断言只能靠猜。

## 一手读数（同一进程、同一次实验，C 探针）

> 一手输出件（W4 r1 整改重跑，本棒亲跑）：`~/tmp/uc2/z32-light-fix1/probe-out.txt`（89 行），逐臂行号锚点见 `archives/l/light/1.2.2/notes.md` 的「能力面一手探针」节 [W4R1/P2-1d]。

| 路径 | stat | opendir |
|---|---|---|
| `/sys` | OK mode=0555 | **EACCES(13)** |
| `/sys/devices` | OK mode=0555 | **EACCES(13)** |
| `/sys/class` | OK mode=0555 | **EACCES(13)** |
| `/sys/class/net`（正对照臂） | OK mode=0755 | **EACCES(13)** |
| `/sys/class/backlight` | OK mode=0755 | **EACCES(13)** |
| `/sys/class/leds` | OK mode=0755 | **EACCES(13)** |
| `/sys/power` | OK mode=0755 | **EACCES(13)** |
| `/sys/bus/hid/drivers/razerkbd` | ENOENT(2) | ENOENT(2) |
| `/etc/udev`、`/run/udev` | ENOENT(2) | ENOENT(2) |

补充：`open("/sys/class", O_RDONLY|O_DIRECTORY)` 直接 `fd=-1 errno=EACCES(13)`；
`libudev` 三个 soname（`libudev.so`/`.so.1`/`.so.0`）`dlopen` 全部失败，
`dlsym(RTLD_DEFAULT,"udev_new")` NOT-FOUND，故"装载"与"枚举"两臂都没戏；
brightness 写入臂因父目录不可枚举而**未能执行**（记为缺证据，不记为失败）。

## 为什么这是新知识

- `stat` 报成功而 `opendir` 报 EACCES ⇒ 不能据 `ls`/`stat` 说"不存在"，也不能据
  0755 的 mode 位说"该能读"。拒点位于 mode 位之外（MAC/挂载策略层）。
- **正对照臂同症状**：一般 sysfs 面（`/sys/class/net`、`/sys/devices`）也 EACCES
  ⇒ 归因必须是"sysfs 整体 readdir 受限"，而不是"backlight 子系统未提供"。
- `ENOENT`（razerkbd / udev 目录）与 `EACCES`（sysfs）在同一台机器上一次实验内并列出现，
  正好构成"不存在 / 不给看"的判别对照。
- 与 E701（raw socket / 真实网卡缺失，用上游 `SKIP_ETHERNET` 跳过）只在"能力墙"这一层
  相似：机制不同（socket 能力 vs sysfs 目录枚举）、根因不同、处置面不同（跳过用例 vs
  改写断言口径）、作用域不同 ⇒ 不判重。E011/DRAFT-6507 是构建面（HMDFS 目录权限/uid 错位），
  与本条运行期面正交。
- 与 `archives/n/nload/0.7.4`（同机制同根因，其 `notes.md:60,106`：`stat` 探 `/sys/class/net` OK 而 `opendir` Permission denied）也**不判重**：nload 有 `/proc/net/dev` 替代后端、处置是改上游源码补 `opendir` 探测（`patches/0003-src-devreader-linux-sys.cpp.patch:19`）⇒ 处置面与作用域两条不满足 **[W4R1/P1-1e]**。
- 与 `knowledge/drafts/E547-draft-0114.kv`（id `E547`，udev 依赖缺失 + stub-libudev 模式）不判重：它是 configure/链接期 `undefined reference to udev_new` + 新增 stub 头改 CMakeLists；本条是运行期枚举被 MAC 拒 + 零补丁。本棒一手实测两面的臂各自独立：`libudev` 三 SONAME `dlopen` 全 FAIL、`dlsym udev_new` NOT-FOUND（输出件 57-61 行）属装载期；`/sys/class/*` 的 `opendir` EACCES（6-45 行）属运行期 **[W4R1/P1-1f]**。

## 可迁移结论

对任何以 sysfs 为功能面的包：先做**带正对照**的探针定性，再把消费者断言写成
"要么真列出、要么诚实降级（枚举为空 + 有诊断 + 不被信号杀死；退出码 0 与非 0 都可能，本包 light -L 实测 rc=0）"，
既不写"OHOS 不支持"，也不写"已验证可用"。缺证据的臂（如特权身份重探）要显式记为未执行。
