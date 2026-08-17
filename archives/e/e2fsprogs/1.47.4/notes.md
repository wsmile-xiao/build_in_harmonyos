# e2fsprogs 1.47.4 适配笔记（HarmonyOS PC · Conan autotools）

## 产物
静态库 `libext2fs.a` / `libcom_err.a` / `libe2p.a` / `libss.a` / `libuuid.a` / `libblkid.a`
+ 全套工具 `bin/`、`sbin/`（mke2fs / e2fsck / tune2fs / debugfs / dumpe2fs / resize2fs …）。

## 版本说明
1.47.4 为按需新增版本；与仓内已有 1.47.0 并存、互不影响。配方沿用 1.47.0
（AutotoolsToolchain + LN→cp -a 的 HMDFS 硬链接规避 + components 声明），仅更新补丁集。

## 与 1.47.0 的补丁差异
| 补丁 | 1.47.0 | 1.47.4 |
|---|---|---|
| 0001 config.guess 加 HarmonyOS 识别 | ✔ | **删除**——改在 `generate()` 显式 `--build/--host=aarch64-unknown-linux-ohos`，config.guess 完全不跑（它至 2025-07-10 仍不认 HarmonyOS） |
| 0002 config.sub 加 ohos 支持 | ✔ | **删除**——1.47.4 自带 config.sub（2025-07-10）已原生支持 `ohos*` / `linux-ohos*`，显式三元组由它纯 shell 规范化 |
| 0003 configure mktemp umask 077→022（HMDFS 权限） | ✔ | ✔（按 1.47.4 行号重生成，内容不变） |
| 0004 misc/fsmap.h inline 移出 FS_IOC_GETFSMAP 守卫 | ✔ | ✔（原样适用） |

> 三轮真机试错的教训：
> ① conan 的 patch-ng 不吃 GNU patch 的 offset/fuzz，0001 直接被拦（第 1 轮败因）；
> ② GNU patch 干跑"offset 成功"污染了 mac 验证树，让我误以为上游 config.guess 已认
>   HarmonyOS 而删掉 0001，设备上纯净 config.guess `cannot guess build type`（第 2 轮败因）；
> ③ 正解是显式 `--build/--host` 三元组跳过 config.guess（同 1.47.0 手工构建的
>   build_alias/host_alias 做法、也是 conan-packager SKILL autotools 三件套第 1 条）。

## 历史坑（沿袭 1.47.0，详见该版本 notes.md）
- HMDFS 无硬链接：`build()` 里 sed 把所有 Makefile 的 `LN = ln` 改 `cp -a`
- configure 须 bash 跑（toybox sh 的 heredoc 问题）
- OHOS sysroot 的 `linux/fsmap.h` 与本地 `misc/fsmap.h` 冲突（0004 解）

## 状态
built —— 真机 `conan create` 通过；test_package 调 `com_err()` 验证 libcom_err 真实链接。
