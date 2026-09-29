# jailkit 2.23 — HarmonyOS PC 适配说明

## 概况

`jailkit` 是 chroot 监禁工具套件：把用户/进程限制在 chroot jail 内运行，
含 C 二进制（jk_socketd/jk_chrootsh/jk_chrootlaunch/jk_lsh/jk_uchroot）、
Python 运维脚本（jk_init/jk_cp/jk_check/jk_jailuser/jk_list/jk_update +
jk_lib.py）、/etc/jailkit 配置与 man 页。

- 上游：https://olivier.sessink.nl/jailkit/ （官网发布 tarball；GitHub
  solbu/jailkit 无 2.23 tag 归档，已实测 404）
- 形态：手写 Makefile 递归 src/py/man（configure 预生成，非 automake）
- 产物：`bin/jk_uchroot`、`sbin/` 下 4 个 C 二进制 + 6 个 Python 脚本、
  `share/jailkit/jk_lib.py`、`etc/jailkit/*.ini`、man7/man8 页
- 依赖：无外部 conan 库（iniparser/passwdparser/wordexp 随源码捆绑）；
  python3 为设备 HNP 自带运行时；libcap/procmail 可选自动跳过
- 许可证：BSD-3-Clause（主体）AND LGPL-2.0-or-later（捆绑 wordexp）

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | configure 硬依赖 `python`（找不到即报错），真机只有 HNP python3 | AC_ARG_VAR 覆盖 `PYTHONINTERPRETER=/data/service/hnp/bin/python3`，py 脚本 shebang 与 jk_lib.pyc 编译随之生效 |
| 2 | 顶层 make install 会向 /etc/shells 追加 jk_chrootsh 行 | package() 复刻 ini/src/py/man 四段子安装到 package_folder，跳过 /etc/shells 写段 |
| 3 | setuid 4755（jk_chrootsh/jk_uchroot）为上游语义 | 保留安装命令；HMDFS 忽略 chmod 不影响落包 |
| 4 | tarball 无 config.guess（无 AC_CANONICAL） | 无需 --build 三元组 |
| 5 | CONFIG_SHELL 缺陷（§12.38①）；HMHDFS umask 077；jobserver EPERM | `env -u CONFIG_SHELL SHELL=/bin/sh` + 绝对路径；生成脚本 umask 077→022 替换；`make -j1` |
| 6 | CLI 工具套件门禁 | 软件级 `commands.json`（R38） |

## 测试

### 上游（构建阶段，2 项自检）

src/iniparsertester 与 src/passwdparsertester（上游自带的解析器自检
程序，覆盖套件基础的 iniparser/passwdparser 组件；有 make 规则但不在
all，无 test/check 目标）：构建阶段显式构建运行，断言
passwdparsertester 输出 `found user jaja!`（uid 100 无换行解析分支）、
iniparsertester 非空输出。

### 消费者（test_package/test_jailkit.sh，6 项断言）

jk_uchroot -h / 缺参报错 / jk_chrootlaunch -h / jk_init Python 脚本链 /
jk_lib.py 纯函数 API（从包内 share/jailkit 真实导入，路径工具
roundtrip）/ 包内容完整性（14 个产物 + ini [netbasics] 节）。chroot
主功能需要 root，非交互面用 CLI 自检 + 安装库 API（R34）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.23 | prepared | 首次适配，待真机验证（Windows 阶段 2026-09-26 完成） |
