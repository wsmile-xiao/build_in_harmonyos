# DRAFT: install 期 strip 缺失与 STRIPPROG 约定（X11 install-sh 血统脚本）

- **id**: `DRAFT-ohos-install-sh-stripprog-strip-missing`
- **软件事件源**: mkc（mk-configure）0.27.0 适配（任务 contrib-14942）
- **查重**（2026-10-08）：`STRIPPROG` 0 / `llvm-strip` 0；`strip` 命中的
  E012/E077/DRAFT-E703 均为不同子族（边界见 §4）
- **状态**: draft（`draft: true`、`contributor_id: frj__`）

## 1. 一句话机理

install-sh 血统脚本（X11R5 `mit/util/scripts/install.sh` 后裔）以自己的协议变量
`stripprog="${STRIPPROG-strip}"` 解析 strip，不看 make 的 `STRIP`；OHOS 无裸 strip
→ `-s` 安装在 `set -e` 下 Error 127 中断、产物不落地，bmake 摘要行 `1 error`
常被输出重定向吞掉——表象是「构建全绿、安装段莫名失败」。

## 2. 单变量对照实验（mkc 0.27.0 源树，examples/hello_world，2026-10-08 真机）

| 组 | 环境（其他条件完全相同） | 结果 |
|---|---|---|
| A | `AR=llvm-ar RANLIB=llvm-ranlib LD=ld.lld`，**无 STRIPPROG** | 失败，日志 `1 error`（strip 报错被重定向吞掉） |
| B | A + **`STRIPPROG=llvm-strip`**（唯一变量） | **`succeeded`（rc=0）** |
| C | A + `STRIP=llvm-strip`（**E012 的处方**，无 STRIPPROG） | **仍失败（rc≠0）** |

C 组是子族判定的关键：E012 的 `STRIP=` 处方传不进 install-sh 血统脚本。

现场错误原文（补 STRIPPROG 前，从构建日志挖出）：

```
/storage/.../scripts/mkc_install[208]: strip: inaccessible or not found
*** [/storage/.../destdir/.../bin/hello_world] Error code 127
bmake: stopped in ...
1 error
```

影响面（当轮矩阵）：AR/RANLIB 修好后仍整批挂的 mkinstall/hello_* 安装段，
补 STRIPPROG 后矩阵从 26 PASS → 48 PASS（65 例）。

## 3. 适用范围（一类）

- autotools 全系（`install-sh` 是 automake `--add-missing` 标配）
- mk-configure（`mkc_install`，本例）
- libtool `--mode=install`、各类手抄 X11 install.sh 的项目
- 触发条件：安装命令带 `-s`（mkc 对 PROG 的默认安装即 `-c -s -m 755`）

## 4. 边界（为何不是 E012/E077）

| 条目 | 机制 | 与本条的分界 |
|---|---|---|
| E012 | make **构建期**工具变量（AR/RANLIB/NM/**STRIP**） | 变量协议不同：install-sh 只读 **STRIPPROG**；C 组实测 E012 处方无效 |
| E077 / DRAFT-E703 | strip **成功执行**但打掉 `.codesign` → 加载器拒绝 | 本条是 strip **根本不存在**、安装中断——发生段（运行 vs 安装）与修法（重签名 vs 供给工具）都不同 |

## 5. 修法

```sh
export STRIPPROG=llvm-strip    # 不是 STRIP=（E012）——那传不进 install-sh
```

禁用项：设 `STRIP=`（假修复，C 组证伪）；私造 `/usr/bin/strip` 符号链接（污染共享环境）。

## 6. 关联

- 软件 PR：【知识库扩展】mkc 0.27.0 适配完成（配方 test/矩阵环境即本条修法实例）
- issue：【知识库扩展】mkc 0.27.0：install-sh 血统脚本的 STRIPPROG 约定（本 PR 关联）
