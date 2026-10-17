# E544 — OHOS HMDFS 大小写不敏感下 autotools 目标名与源码目录同名冲突

## 错误特征

```text
rm: cannot remove 'linuxpba': Is a directory
make[1]: *** [Makefile:579: linuxpba] Error 1
```

- autotools 项目在 `make` 链接阶段失败，错误来自 Makefile 中 `@rm -f <目标名>` 的链接前置步骤
- 报错目标名是 `sbin_PROGRAMS`/`bin_PROGRAMS` 中声明的可执行文件名（本例 `linuxpba`）
- 同一源码树中存在与目标名**仅大小写不同**的源码子目录（本例 `LinuxPBA/`）

## 触发条件

- 构建系统: autotools（configure.ac + Makefile.am，`sbin_PROGRAMS`/`bin_PROGRAMS`）
- 阶段: make 链接（linking）
- 平台: HarmonyOS PC（HMDFS 文件系统，大小写不敏感 case-insensitive）
- 源码结构: 可执行目标名与源码子目录名存在大小写差异（linuxpba vs LinuxPBA）

## 根因分析

OHOS 的 HMDFS 文件系统是**大小写不敏感**（case-insensitive）的：`touch CaseTest` 后 `ls casetest` 也能命中同一文件。因此：

1. 源码目录 `LinuxPBA/` 与 make 目标名 `linuxpba` 在 HMDFS 上被解析为**同一路径**（`stat -c %i` 显示 inode 相同）
2. autotools 生成的 Makefile 链接规则先执行 `@rm -f linuxpba`（删除可能存在的旧产物）
3. 由于 `linuxpba` 与 `LinuxPBA` 同一路径，`rm -f` 实际作用于目录，报 `Is a directory`
4. 链接无法继续，构建失败

在常规大小写敏感文件系统（ext4/xfs 等）上不存在该问题，属 OHOS HMDFS 平台特性。

## 解决方案

### 推荐方案

**重命名可执行目标，避开与源码目录的大小写冲突**（rec_approach: `rename-target-avoid-case-collision`）：

修改 `Makefile.am`：

```diff
-sbin_PROGRAMS = sedutil-cli linuxpba
+sbin_PROGRAMS = sedutil-cli sedutil-pba

-linuxpba_SOURCES = LinuxPBA/LinuxPBA.cpp ...
+sedutil_pba_SOURCES = LinuxPBA/LinuxPBA.cpp ...
```

同步修改 `conandata.yml` 补丁声明与配方 `package_info()`（bindirs 等），保持产物名全局一致。然后：

```bash
automake && ./config.status Makefile   # 重新生成 Makefile
make -j1                               # 链接不再与目录冲突
```

### 禁止做法

- ❌ 不重命名目标而试图 `rm -rf linuxpba`：`rm -rf` 会误删源码目录 `LinuxPBA/` 内容（同一路径），破坏源码树
- ❌ 不直接修改生成文件 `Makefile` 而不动 `Makefile.am`：改动会被 `automake`/`config.status` 覆盖，且违反 R6（只改源文件不改生成文件）
- ❌ 不试图 `ln -sf` 软链接绕开：HMDFS 软链接行为受限（R5 平台陷阱）

## 验证

```bash
# 1. 确认大小写冲突（inode 相同 = HMDFS 视为同一路径）
stat -c %i linuxpba LinuxPBA   # 输出相同 inode

# 2. 重命名目标后重新生成 Makefile 并编译
automake
./config.status Makefile
make -j1                        # 链接成功，无 "Is a directory" 错误

# 3. 验证产物
ls -la sedutil-cli sedutil-pba  # 两个可执行文件均生成
```

本任务实测：`sedutil 1.20.0` 将 `linuxpba` 目标改名为 `sedutil-pba` 后，`make` 链接成功，`conan-verify` G0-G4 + L2/L4/L5 全部通过。

## 关联条目

- similar_to: **E416**（同为 HMDFS 大小写不敏感场景，但 E416 是 conan slug 包目录双 case 并存问题，本条目是 autotools make 目标名与源码目录冲突；错误特征、解决方案均不同）
- 相关: E011（HMDFS umask/权限相关平台特性）
