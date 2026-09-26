# chkboot

## 简介
检测未加密 `/boot` 分区是否被篡改的 shell 工具：以 root 对 `BOOTDIR` 下每个文件计算
sha512 基线并 `diff` 出变更，产生告警文件；`chkboot-check` 在有未确认变更时以
`rc=1` 告警，并可经 `/etc/issue`、`/etc/profile.d`、桌面通知（zenity/xmessage）提示。
上游工程为纯 shell 脚本 + 配置数据（`Architecture: all`，零编译、零第三方库依赖）。

## OHOS 适配
- **配置路径可覆盖（补丁 5 处，每处一行）**：OHOS 的 `/etc` 是只读文件系统
  （实测 `mkdir /etc/default` → `Read-only file system`），上游硬编码的
  `source /etc/default/chkboot.conf` 不可用；变量未定义时
  `${CHKBOOT_DATA}/${CHANGES_ALERT}` 会塌缩成 `/`，使 `chkboot-check` 对任意目录
  误报 `CHKBOOT ALERT`。补丁改为 `source "${CHKBOOT_CONF:-/etc/default/chkboot.conf}"`
  ——未设置时与上游逐字一致；OHOS 上用 `CHKBOOT_CONF` 指向包内配置。
- **构建期 install(1) 缺失（零源码改动）**：OHOS 未把 `install(1)` 暴露为独立命令
  （coreutils 缺失；busybox 内含 `install` applet 但无同名入口），上游 `make install`
  直接 `Error 127`。recipe 在 `build()` 生成指向平台 busybox 的 install shim 并前置
  `PATH`，上游 Makefile 原样可用。
- **runenv 注入配置路径**：`package_info()` 把 `CHKBOOT_CONF` 指向包内
  `res/default/chkboot.conf`，使 Conan 环境内开箱可用。
- systemd / pacman / mkinitcpio 三类开机集成资产在 OHOS 无对应子系统，随包安装到
  `res/` 作为参考数据。

## 依赖
- 无（`conan download chkboot/1.3 -r=ohpcd` → rc=1：目标库自身尚未发布，
  非依赖缺口；无任何第三方 require）

## 功能验证
```bash
# 消费端用例套件（10 用例：包布局 + Debian autopkgtest 4 用例等价移植 + 鸿蒙特有用例）
bash archives/c/chkboot/1.3/test_package/test_chkboot.sh <package_folder>
```

## 参考
- 上游: https://github.com/grazzolini/chkboot
- 版本: 1.3（git tag `v1.3` → `33ea87521dcb1d72c5e9e6417f7882b3f3227d73`）
