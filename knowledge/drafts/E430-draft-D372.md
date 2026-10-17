# E430 — OHOS 已落盘 ELF 任何 in-place 字节改动后不可执行（strip/objcopy/meson install RUNPATH 剥离）

## 错误特征
```
Permission denied (EACCES) / Operation not permitted (EPERM)
```
对"已生成过的 ELF 做过链接后处理"的二进制执行时报错；文件 mode 770/777 均无效，
ehdr/phdr 完整、SELinux context 与可执行文件完全一致——权限层面无任何异常，纯内核拒 exec。

## 触发条件
- 构建系统: 任意（clang/lld 产生 ELF 后）
- 阶段: 链接后处理 / 打包（package() 阶段 strip、llvm-objcopy、meson install 的 in-place RUNPATH 剥离）

## 根因分析
OHOS 内核/FS 对已落盘文件做完整性封印（推断与 lld 生成的 `.note.ohos.ident` 标识段相关，
与 SKILL gotchas「ELF 签名」机制同族）：落盘后**任何** in-place 字节改动破坏封印 → exec 拒绝。

两条证据链（mpd 0.24.12 适配期实测，2026-09-27）：
1. `llvm-objcopy --strip-unneeded`（乃至纯重序列化）输出 → EACCES/EPERM；4.6KB hello 对照实验同样复现（平台级行为，与 mpd 无关）
2. `meson install` 对 build 目录二进制做 in-place DT_RUNPATH 剥离（1195 字节改动、文件大小不变）→ 安装产物 stage 直接执行报 EPERM（cmp 证明 stage ≠ builddir 原件）

对照组：clang/lld 原始产物可执行；`cp` / `shutil.copy2` **全新文件写入**（内容不变）可执行。

## 解决方案

### 推荐方案
package() 禁止 meson install / strip / llvm-objcopy 等一切链接后重写，一律对 build 目录
原始产物做**全新拷贝**（conan copy / shutil.copy2 = 新文件写入，可执行实证）。
build 目录产物携带的 DT_RUNPATH（conan build-tree 绝对路径）异地为死路径、无害，
运行时库解析由 conanrunenv（LD_LIBRARY_PATH）承担；瘦身/签名需求走 CI sign.sh 签名链。
另：本机 `/data/service/hnp/bin/llvm-strip` 实为 llvm-objcopy 符号链接别名（无独立 llvm-strip）。

### 禁止做法
- ❌ 对已落盘 ELF 做任何 in-place 字节修改（strip / objcopy / 二进制 patch / in-place RUNPATH 剥离）
- ❌ 用 `meson install` 做 conan package() 的产物搬运（其对 builddir 原件做 in-place 修改）

## 验证
```bash
# 1) strip 产物不可执行（复现）：
cp $BUILDDIR/mpd /tmp/t1 && /data/service/hnp/bin/llvm-objcopy --strip-unneeded /tmp/t1 && /tmp/t1   # → EACCES/EPERM
# 2) 全新拷贝可执行（解法）：
cp $BUILDDIR/mpd /tmp/t2 && /tmp/t2 --version   # → Music Player Daemon 0.24.12
```

## 关联条目
- 相关: E429（同为 mpd 0.24.12 适配期发现）
