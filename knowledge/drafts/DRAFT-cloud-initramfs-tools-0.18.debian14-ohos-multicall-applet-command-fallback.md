# DRAFT-cloud-initramfs-tools-0.18.debian14-ohos-multicall-applet-command-fallback

> 草稿知识项 — OHOS 多调用用户态「applet 存在但无同名命令」的脚本级回退模式
> 来源：cloud-initramfs-tools 0.18.debian14 适配（feat/cloud-initramfs-tools-0.18.debian14，2026-09-26）
> 同 stem 配对：`knowledge/drafts/DRAFT-cloud-initramfs-tools-0.18.debian14-ohos-multicall-applet-command-fallback.kv`

## 问题（现象 / error_signature）

- 打包的 CLI `overlayroot-chroot` 直接裸调 `umount`、`chroot`；在 PATH 被裁剪的环境下报
  `umount: inaccessible or not found` / `chroot: ... not found`，功能中断。
- 在 Makefile 场景呈现为 `make: *** [Makefile:N: install] Error 127`（命令不可解析）。
- 与此同时 `busybox --list` 明明列出 `umount`、`chroot`、`install` 等 applet。
- 观测命令：
  ```
  $ command -v umount chroot ; echo rc=$?     # 无输出
  rc=1
  $ busybox --list | grep -xE 'umount|chroot'
  chroot
  umount
  $ python3 -c "import shutil; print(shutil.which('install'))"
  /system/bin/install                          # 默认进程 PATH 含 /system/bin 时可见
  ```

## 根因（root_cause）

1. OHOS 用户态由 Toybox / 多调用二进制提供，**命令可见性取决于 PATH 组成**：
   默认进程 PATH 首段为 `/system/bin`（提供 `install`/`umount`/`chroot`，该目录对普通用户不可
   `ls`，仅 PATH 查找时可执行）；交互 shell 与受限环境常裁剪掉该目录。
2. busybox 1.37 内含这些 applet，但**不保证**有同名命令入口。
3. 脚本按「完整 coreutils 命令集」假设裸调命令名，于是在裁剪 PATH 环境下整体失败。
   这是宿主用户态能力与脚本假设之间的落差，不是脚本逻辑缺陷。

## 可复用方案（rec_approach: in-script-command-v-with-busybox-applet-fallback）

在脚本内加入一个解析函数，并把裸调点改为经它调用：

```sh
# 优先按原名调用（在完整系统上与上游逐字一致），原名缺失时回退 busybox applet
xcmd() {
	local _cmd="$1"
	shift
	if command -v "${_cmd}" >/dev/null 2>&1; then
		"${_cmd}" "$@"
	elif command -v busybox >/dev/null 2>&1; then
		busybox "${_cmd}" "$@"
	else
		fail "Required command not available: ${_cmd}"
	fi
}
```

- **默认分支保持上游语义**：解析到同名命令时行为与改动前完全一致；
- **不引入平台宏**（无 `__OHOS__` 之类条件编译），靠能力探测即可移植；
- 构建期若可接受「仅本 recipe 生效」的方案，可等价地在 `build()` 中生成只含该 applet
  同名入口的 shim 目录并前置 PATH（见配套草稿 conditional-install-shim）。

## 适用条件

- OHOS（或其他多调用用户态）上运行、且裸调 coreutils/util-linux 命令名的 shell 脚本、
  打包 CLI、Makefile 目标；
- PATH 被裁剪或用户态仅由 busybox 提供的环境。

## 反例（不适用场景）

- 命令**仅在被测软件自身的私有 PATH / 私有目录**中调用（问题不成立）；
- 需要的是 syscall 级能力而非命令解析：即使解析成功，OHOS 沙箱可能不放行
  `umount2`/`chroot` 等 syscall，进程会以 `Signal 31 (SIGSYS)` / rc=159 结束
  （见知识条目 E051）。此时回退只解决「命令解析」，不解决「能力可用」；
- 静态链接的 C/C++ 程序内部直接 syscall 的场景（与本模式无关）。

## 验证证据（真实命令 + 结果）

- 回退分支确定性验证（测试替身）：PATH 仅含同名替身 → 走原名；PATH 仅含 `busybox` 替身
  → 输出 `BUSYBOX-CALL umount --probe`（test_package 用例 A4，两分支均 PASS）。
- 真实平台验证：`PATH=<仅含 busybox 软链的目录> sh -c 'xcmd umount --help'` → rc=0
  （busybox applet 真实回退成功，非 127；test_package 用例 C2/PASS）。
- 反面对照（记录）：真实 `xcmd umount /nonexistent` → rc=159（SIGSYS），说明解析成功但
  syscall 能力受限。
- 补丁随包产出：`archives/c/cloud-initramfs-tools/0.18.debian14/patches/0001-…patch`（+21/-2），
  `conan create` rc=0、test_package 16/16 通过。

## 限制与恢复条件

- 回退依赖平台存在 `busybox`；无 busybox 时应显式失败并给出清晰报错（函数内已处理）。
- 若未来 OHOS 用户态补齐同名入口，默认分支即生效，本模式无需回退，也无副作用。
