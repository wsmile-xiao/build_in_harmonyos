# cloud-initramfs-tools 0.18.debian14 适配笔记

## 编译环境
- 构建系统: makefile（上游顶层 Makefile，`build:` 为空目标，无编译步骤）
- 编译日期: 2026-09-26
- 编译器: 无（纯 POSIX shell 包，Architecture: all，无 .c/.h/.rs/.go/.py 源码）
- 平台: HarmonyOS PC aarch64（Toybox 用户态，`/bin/sh` = Toybox sh）
- 状态: built（本地 conan create / test_package / W3 全绿，未上传制品仓）

## 编译步骤

```bash
# 1. 源码（Debian 原生包：权威上游 VCS = Debian 打包仓库，取标签 debian/0.18.debian14 的官方归档）
curl -sSL -o cloud-initramfs-tools-debian-0.18.debian14.tar.gz \
  https://salsa.debian.org/cloud-team/cloud-initramfs-tools/-/archive/debian/0.18.debian14/cloud-initramfs-tools-debian-0.18.debian14.tar.gz
sha256sum cloud-initramfs-tools-debian-0.18.debian14.tar.gz
# b746cdd93d35ac48318051eb09c1c21eb350f4b5a9477798ee6a29b446999e02   (HTTP 200, 38800B)

# 内容等价性核验：与同版本 .dsc Checksums-Sha256 校验的 Debian 官方 pool tarball
# 解包后逐文件字节一致 → 40/40 文件 sha256 全等，文件集 diff rc=0
# （证据 evidence/91-salsa-equivalence.log）

# 2. 构建（真实构建 = 上游 install: 目标，纯文件拷贝）
make install DESTDIR=<staging>          # 见下方「问题 1」
```

落地产物（14 个文件，实测清单见 `reports/test-report.md` §2）：
`usr/share/initramfs-tools/hooks/{overlayroot,growroot,rescuevol,cloud-initramfs-dyn-netconf}`、
`usr/share/initramfs-tools/scripts/{init-bottom,init-top,local-bottom,local-premount}/…`、
`usr/share/initramfs-tools/conf-hooks.d/overlayroot`、`etc/overlayroot.conf`、
`etc/update-motd.d/97-overlayroot`、`usr/sbin/overlayroot-chroot`、
`usr/share/man/man8/overlayroot-chroot.8`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make install` → `/bin/sh: install: inaccessible or not found`，`make: *** [Makefile:10: install] Error 127`（rc=2） | OHOS 用户态由 Toybox 提供，且**命令可见性取决于 PATH 组成**：默认进程 PATH 首段是 `/system/bin`（其中确有 `install`，但该目录对普通用户不可 `ls`，仅 PATH 查找时可执行）；本机交互 shell 的 PATH 被裁剪掉 `/system/bin`，于是 `install` 不可解析，上游 Makefile 的 `install:` 目标整体失败 | `build()` 中条件化生成 install shim：仅当 `shutil.which("install")` 为空时，用平台 busybox 的 `install` applet 建同名入口并前置 PATH（无源码改动；平台已有 install(1) 时不启用）。实测 shim 在裁剪 PATH 下使 `make install` rc=0，落地 14 文件 |
| 2 | 打包的 CLI `overlayroot-chroot` 依赖 `umount(1)`/`chroot(1)`，二者在 PATH 被裁剪的环境下不可解析（busybox 1.37 含同名 applet 但无同名入口） | 同问题 1 的「多调用用户态 applet 与同名入口不一致」 | 补丁 `0001`：在 `overlayroot-chroot` 内新增 `xcmd()`——优先按原名调用（在完整系统上与上游行为逐字一致），原名缺失时回退 `busybox <applet>`；调用点仅 `umount`（clean_exit）与 `chroot` 各 1 处。无平台宏、无条件编译 |
| 3 | 真实执行 `umount` / `chroot <args>` 时进程以 `Signal 31 (core dumped)` rc=159 结束 | OHOS 沙箱/内核未放行 mount 族 syscall（E051：未实现 syscall → SIGSYS）。`mountpoint`（stat 实现）与 `mount`（只读查询）正常 | 不修：属平台能力限制，非本包缺陷。已在 `notes`/`manifest.knowledge_gained`/测试用例 C2 观测项记录；CLI 的改挂载与 chroot 能力需特权/initramfs 环境方能行使 |
| 4 | 配置与 motd 片段无法落 `/etc` | 实测 OHOS 的 `/etc` 与 `/tmp` 均为只读（`echo x > /etc/...` → Read-only file system） | 包内落 `res/etc/overlayroot.conf`、`res/etc/update-motd.d/97-overlayroot`，并由 `runenv_info` 导出 `OVERLAYROOT_CONF` 指向包内配置 |
| 5 | `install -m 755` 落地后权限实测为 770、`-m 644` 为 660 | HMDFS 权限归一化（chmod 语义受限，E046） | 不修：测试断言以「可执行位 + 内容字节一致」为准，不比对精确 mode |

## 源码修改

补丁 1 个（`patches/0001-overlayroot-usr-sbin-overlayroot-chroot.patch`，+21/-2，单文件）：

```diff
+# Resolve and run a command portably.
+# ... (multi-call/Toybox 用户态可能无同名入口)
+xcmd() {
+	local _cmd="$1"
+	shift
+	if command -v "${_cmd}" >/dev/null 2>&1; then
+		"${_cmd}" "$@"
+	elif command -v busybox >/dev/null 2>&1; then
+		busybox "${_cmd}" "$@"
+	else
+		fail "Required command not available: ${_cmd}"
+	fi
+}
...
-			umount ${d} || rc=1
+			xcmd umount ${d} || rc=1
...
-chroot ${lowerdir} "$@"
+xcmd chroot ${lowerdir} "$@"
```

默认分支（`command -v` 命中）与上游逐字一致；仅当平台未暴露同名命令时才走 busybox applet。补丁由 `ohc-run.py refresh-patch --auto` 生成（R3）。

## 依赖版本

强制第三方依赖 = 0（W0 实测）。上游 `debian/control` 的 Build-Depends 仅 `debhelper-compat (= 13)`（Debian 打包框架，本适配不使用 dh，改用 upstream Makefile）；运行期 `Depends` 全部是 OS/发行版工具（initramfs-tools、cloud-utils、util-linux、e2fsprogs、cryptsetup、systemd/udev 等），非可 require 的 Conan 三方库。

W0 实测（`conan download … -r=ohpcd --only-recipe`，rc 单独取）：

| 目标 | rc | 结论 |
|---|---|---|
| `cloud-utils/0.33`（growroot 运行期 growpart 供应方） | 0 | 可消费 |
| `debhelper/13.3.4`（构建工具） | 0 | 可消费 |
| `cloud-initramfs-tools/0.18.debian14`（目标库自身） | 1 | 尚未适配（本任务对象） |

## 验证结果

```bash
# conan create（含 test_package）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# rc=0 ；Package '6b129b068851896169fae42d399fa922d239ce8a' created
# test_package: 用例 总计=16 通过=16 失败=0 跳过=0 断言=59

# 上游入口（9 个）prereqs 协议真实执行：全部 rc=0
#   overlayroot hook → cryptsetup ；dyn-netconf init-top → udev ；其余为空
```

## 交付物

| 文件 | 说明 |
|------|------|
| `share/initramfs-tools/hooks/*`（4） | 上游 initramfs hooks（overlayroot/growroot/rescuevol/dyn-netconf） |
| `share/initramfs-tools/scripts/*/*`（5） | 上游 initramfs 阶段脚本 |
| `share/initramfs-tools/conf-hooks.d/overlayroot` | `export CRYPTSETUP=y` |
| `bin/overlayroot-chroot` | 唯一可执行件（含 xcmd 适配） |
| `share/man/man8/overlayroot-chroot.8` | man 手册 |
| `res/etc/overlayroot.conf` | OHOS 只读 /etc 场景下的包内配置（`OVERLAYROOT_CONF` 指向） |
| `res/etc/update-motd.d/97-overlayroot` | 包内 motd 片段 |
| `licenses/COPYING` | GPL-3.0-or-later 许可证 |

## 注意事项

1. **initramfs 语义**：本包交付物设计为在 initramfs 构建/启动环境（initramfs-tools + 特权）中运行；OHOS PC 上无 initramfs-tools，hook 主体逻辑只覆盖到「协议层真实执行（`prereqs`）+ Toybox sh 语法自洽 + 布局契约」。
2. **源 URL 口径（R39/PF7 已彻底规避，无例外）**：Debian 原生包无独立上游 tarball，其权威上游 VCS 即 Debian 打包仓库（`debian/control` 的 `Vcs-Git`）。因此源直接取该仓库标签 `debian/0.18.debian14` 的 salsa GitLab 官方归档端点——salsa.debian.org 不在 PF7 任何黑名单内，且权限高于 mirror；同时以「与 `.dsc` 校验一致的 pool tarball 逐文件字节相等（40/40）」完成内容等价性核验，故**不需要任何 `--no-preflight` 例外登记**。仓内同款先例：`archives/a/astromatic/1.3`、`archives/b/boost-defaults/1.90.0.2`（均以 salsa archive 为源）。
3. **构建期 shim 只影响本包**：`install-shim` 目录位于 build_folder，前置 PATH 仅作用于本 recipe 的 `make install` 调用。
---

**编译结束**: 2026-09-26 10:36
**最终状态**: built
