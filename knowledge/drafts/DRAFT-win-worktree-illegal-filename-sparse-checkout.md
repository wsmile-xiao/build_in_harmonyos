# DRAFT — 远端 main 含 Windows 非法路径时 worktree add 失败：CR 结尾文件名/大小写冲突目录的 sparse-checkout 绕行法

> 通用环境条目。来源：radioclk 适配时创建 worktree 连续 3 次失败的诊断过程。

## 使用说明

在 Windows 主机上执行 `git worktree add -b feat/... <path> origin/main`，
检出 100% 完成后报：

```
error: unable to create file archives/g/gama/2.29/patches/0002-dataparser-ungated.patch??: Invalid argument
fatal: Could not reset index file to revision 'HEAD'.
fatal: cannot change to '<worktree路径>': No such file or directory
```

且失败后 worktree 目录被 git 自动回滚删除。这不是网络/超时问题（加大
timeout 无用），是**远端 main 上存在 Windows 文件系统无法表达的路径**。
按本条目识别类型并用 sparse-checkout 排除后重建。

## 适用范围

- 平台：Windows 开发机（NTFS/大小写不敏感 + 文件名禁 `\r`）
- 阶段：一库一分支工作流 §3.2 创建 worktree 时
- 两类非法路径：
  1. **CR 结尾文件名**：`<文件名>.patch\r\r`（多见于跨平台脚本/管道写入
     产生的提交），Windows 报 `Invalid argument`
  2. **大小写冲突目录**：`archives/l/libXext/` 与 `archives/l/libxext/`
     并存，Windows 检出时两路径写同一磁盘目录、互相覆盖，留两个永久 M
     （后者不阻断 worktree，只污染 status；若与前者叠加需一起排除）

## 输入输出定义

输入：主仓库路径、目标 worktree 路径、分支名、非法路径 pattern

诊断命令：

```powershell
# 确认非法路径存在于远端 main（而非本地脏改动）
git -C <主仓库> ls-tree origin/main <可疑目录>/ | Select-String "<可疑文件名>"
# 大小写冲突：同名不同大小写目录各返回一个 tree
git -C <主仓库> ls-tree origin/main archives/l/ | Select-String -CaseSensitive:"libxext"
```

输出：可用 worktree（缺被排除的个别文件；这些文件不属于你的适配边界，
不影响 `archives/<你的库>/` 工作）

修复命令（在主仓库执行）：

```powershell
git -C <repo> worktree add --no-checkout -b feat/<库名>-<版本>-codex <wt> origin/main
$info = "<repo>\.git\worktrees\<库名>\info"
New-Item -ItemType Directory -Force $info
# /* 全保留 + ! 精确排除非法路径（non-cone 语法）
Set-Content "$info\sparse-checkout" "/*`n!archives/g/gama/2.29/patches/0002-dataparser-ungated.patch*"
git -C <wt> -c core.sparseCheckout=true checkout
```

## 示例

radioclk（2026-10-02 实录）：

```
排除规则： /*  +  !archives/g/gama/2.29/patches/0002-dataparser-ungated.patch*
结果： 111097 文件检出成功，分支 feat/radioclk-1.0.pristine-codex 可用；
       libXext/libxext 大小写冲突仅留 2 个 M 假象（不 add 即不进提交），
       radioclk 包目录不受影响，后续 5 commit + 真机 shadow CI 全绿。
```

注意事项：
- 排除 pattern 用 `*` 通配以覆盖 CR 后缀（无法在规则里字面写出 `\r`）
- 被排除文件恢复的正确途径：上游仓库修掉非法路径提交（基础设施侧），
  本绕行只是开发期止损；**不要**为绕过它改公共基础设施（工作流 §14）
- 提交前 `git status` 里出现 libXext 两个 M 属该问题假象，勿 `git add -A`

## 验证

- radioclk worktree 以此法建立后完成全流程（5 commits、真机 r3 全绿）
- 对照实验：不用 sparse-checkout 直接 add → 100% 检出后必定回滚（3 次复现）

## 关联条目

- 工作流文档 §3.2（worktree 创建标准步骤，本条目是其异常分支）
- E101（git safe.directory / HMDFS 上的 git 权限问题——不同因：那是设备端）
- dmc_unrar 的 HMDFS inode ENOSPC sparse-checkout：同为 sparse-checkout
  手段但根因相反（磁盘 inode 耗尽 vs Windows 路径非法）
