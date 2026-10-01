# vlock

**vlock** — Linux 虚拟控制台（virtual console）锁定程序。可以只锁定当前终端，
也可以（`-a/--all`）锁住整台机器的所有虚拟控制台，解锁需要当前用户口令或 root 口令。
认证通过 PAM 完成，支持插件（module/script）扩展。

- 上游：Frank Benkstein 的 vlock 2.2.2
  （上游原站已下线，见 Debian #833843 "Upstream is dead"；本项目采用 Debian 官方打包
  仓库 `salsa.debian.org/debian/vlock` 的 pristine `upstream/2.2.2` 标签）
- 许可证：GPL-2.0-or-later
- 构建系统：自制 POSIX-sh `configure` + GNU make；生成 Conan 包 `vlock/2.2.2`

## 产物

| 路径 | 说明 |
|------|------|
| `bin/vlock` | sh 启动脚本：解析选项、按需加载插件，随后调用 `vlock-main` |
| `sbin/vlock-main` | 认证与锁屏进程（上游安装规则会置 setuid 4711 / owner root） |
| `lib/vlock/modules/all.so` | 插件：整机锁定（`-a`） |
| `lib/vlock/modules/new.so` | 插件：切换到新虚拟控制台后锁定 |
| `lib/vlock/modules/nosysrq.so` | 插件：锁屏期间关闭 SysRq |
| `lib/vlock/scripts/` | 脚本类插件目录（上游随源码提供示例脚本） |
| `share/man/man1/vlock.1`、`man5/vlock-plugins.5`、`man8/vlock-main.8` | 手册页 |

## 依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| `linux-pam/1.7.2` | 运行时 | PAM 认证（`libpam.so.0`，上游 configure 默认 `AUTH_METHOD=pam`） |
| `cunit/2.1-2` | 构建/测试 | 仅为构建并运行上游 CUnit 测试套件，**不进包** |

## 构建

```bash
conan create archives/v/vlock/2.2.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 测试

```bash
# 上游套件（recipe build() 内真实执行）：4 套件 / 14 用例
make -C tests check
# 消费者测试（test_package，8 用例，含 3 项鸿蒙特有）
python3 test_package/test_vlock.py <package_folder>
```

详见 [2.2.2/reports/test-report.md](2.2.2/reports/test-report.md)。

## HarmonyOS PC 平台限制

1. **无 Linux 虚拟控制台**：`VT_GETMODE`/`VT_SETMODE` 在 HarmonyOS PC 上不可用，
   控制台锁定（`-a/--all` 的整机锁定语义）无法生效；`vlock` 会打印
   `this terminal is not a virtual console` 并安全退出该路径（上游已处理）。
2. **`vlock-main` 需要 `/etc/passwd` 条目**：`getpwuid()` 失败时报
   `vlock: could not get username`；应用沙箱 uid 不在 passwd 中。
3. **属主/属组/SUID 不落盘**：HMDFS 上 `chown`/`chmod` 不生效，Conan 包亦不承载
   系统安装期语义；如需 setuid 安装，请由发行版安装脚本在目标系统上完成。
