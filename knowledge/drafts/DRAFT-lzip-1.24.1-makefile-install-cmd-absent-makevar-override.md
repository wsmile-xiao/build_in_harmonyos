# DRAFT（通用机制）: 上游 Makefile 硬编码 `INSTALL = install` —— OHOS 用户态无 `install` 命令，package 阶段 `Error 127`，用 make 命令行变量覆盖为 `cp/mkdir` 等价语义

> 来自 lzip 1.24.1（裸 Makefile + 自研 configure）的设备实测。复制为
> `DRAFT-<你的包>-<你的版本>-makefile-install-cmd-absent-makevar-override.{kv,md}`，
> 证据字段换成本包实测值；**只有真在本包 package() 阶段撞出该签名才配这条**。

## 基本信息
- **严重度**: 2
- **类别**: platform, makefile, packaging, installation
- **阶段**: package（编译与链接均已成功）
- **作者**: QC-10
- **来源 PR**: (本 PR) ／ **来源 commit**: (待提交后回填)

## 错误特征
```
if [ ! -d ".../usr/bin" ] ; then install -d -m 755 ".../usr/bin" ; fi
/bin/sh: install: inaccessible or not found
make: *** [Makefile:87: install-bin] Error 127
```
关键指纹：**失败只在安装 recipe 那一行**，`make`/`make check` 都已通过；报错文案是
`inaccessible or not found`（hishell/toybox sh 对"命令不存在"的措辞，不是 `Permission denied`）；
上游 Makefile 里能看到 `INSTALL = install` 与 `INSTALL_PROGRAM = $(INSTALL) -m 755` 这类变量把手。

## 根因分析
OHOS PC 的用户态环境 **没有 GNU coreutils 的 `install`**（设备实测：`command -v install` 为空，
`/usr/bin/install` 不存在），而"自研 configure + 裸 Makefile"这一类上游项目习惯把安装工具写成
**变量**再在 recipe 里引用：

```make
INSTALL       = install
INSTALL_PROGRAM = $(INSTALL) -m 755
INSTALL_DATA    = $(INSTALL) -m 644
INSTALL_DIR     = $(INSTALL) -d -m 755
```

GNU make 的规则是**命令行变量优先于 makefile 内的 `=` / `:=` 赋值**，因此这些把手可以在不改一行
上游代码的情况下被整体替换成用户态一定存在的等价命令：`cp -f` 顶替 install 的复制职责、
`mkdir -p` 顶替 `install -d`。上游 `if [ ! -d ] ; then $(INSTALL_DIR) ; fi` 与
`$(INSTALL_PROGRAM) src dst` 的两段结构原样保留 ⇒ **DESTDIR / prefix 语义、目录创建、落点布局都不丢**，
不需要把打包逻辑改写成 Python 复制，也不需要补丁。

## 推荐方案
**方法**: `make-var-install-override`（优先级 1，配方侧，零补丁）

**验证/命令**（同一构建目录三步探针，本包实测）:
```
# P1 环境事实
command -v install                     # → 空
ls -l /usr/bin/install                 # → No such file or directory

# P2 复现失败
make install-bin DESTDIR=<t>           # → install: inaccessible or not found / Error 127

# P3 修后通过
make install-bin DESTDIR=<t> INSTALL="cp -f" INSTALL_PROGRAM="cp -f" \
     INSTALL_DATA="cp -f" INSTALL_DIR="mkdir -p"
```
在 conan 配方里即 `self.run('make install-bin INSTALL="cp -f" ... ', env="conanbuild")`。

## 适用边界 / 反例 / 解除条件
- **适用**：上游 Makefile 把安装工具做成**可覆盖变量**、且在 recipe 中以 `$(INSTALL_*)` 引用；
  典型是 lzip 家族（lzip/lzlib/plzip/pdlzip）与同类手写 Makefile 的 C/C++ 小工具。
- **反例 1（覆盖无效）**：上游写 `override INSTALL := ...` ⇒ make 命令行不再起作用，只能打补丁。
- **反例 2（没有把手）**：安装命令是内联字面量（recipe 里直接 `install -m 755 ...`）⇒ 无可覆盖变量，
  走 fallback（配方侧 `shutil.copyfile` + `chmod`，或给上游 Makefile 打补丁）。
- **反例 3（模式位）**：`cp -f` 沿用源文件模式位、不再执行 `-m 755/644`；若上游依赖安装时的模式收敛，
  需在配方内补一次 `chmod`，否则可能交付权限过宽或不可执行的文件。
- **禁忌**：不得用本机制掩盖真正的交叉编译失败——只在 install 这一步失败、编译链接已成功时使用。
- **解除条件**：环境提供 `install`（CI worker 或后续系统镜像补齐 coreutils）后，覆盖仍无害，
  但不再是必需；此时应回退为直接 `make install`。

## 关键词
裸 Makefile, 自研 configure, install 命令缺失, inaccessible or not found, Error 127,
INSTALL_PROGRAM/INSTALL_DATA/INSTALL_DIR, GNU make 命令行变量优先级, cp -f, mkdir -p,
DESTDIR 语义保留, 免补丁打包, OHOS 用户态

---
*与相近条目的区分（诚实申报：**症状层面知识库已覆盖，本条的新增在解法路径**，依 AGENTS §6.2 判 hit
条件 2 按 create 申报）：**E098**（`cp-chmod-replace`）签名与本条**完全相同**
（`install: command not found|sh: install: inaccessible or not found`）、根因相同（toybox 无 install）、
适用范围相同；但它的解法是**放弃上游 install 目标、自己手写** `mkdir -p && cp && chmod`。
本条在上游把安装工具做成变量时**不动 install 目标**，只在 make 命令行替换工具变量
⇒ 保留上游目录判断、DESTDIR 前缀展开与安装清单语义，上游以后加装 man/info 不必逐条重写。
边界=必须有变量把手（`override INSTALL :=` 或内联字面量时无处覆盖 ⇒ 退回 E098）。
**E108**（`patch-makefile-in-ginstall`）是同症状族第三条解法：按 R6 改上游 `Makefile.in` 换 ginstall；
本机实测 ginstall 可得（`~/usr/local/bin/ginstall` = GNU coreutils 9.10、在 conan buildenv PATH 内），
代价是按版本维护补丁 + 引入设备侧 coreutils 依赖（CI worker 不保证有）⇒ 有把手时优先本条。
**DRAFT-8958**（clthreads）签名是 `install: Permission denied`（被不可执行的 `~/usr/local/bin/install`
遮蔽）+ HMDFS 拒绝 symlink，解法是配方侧 Python 复制，与本条签名与修法均不同。
**E312/E313** 亦出现 `/usr/bin/install` 缺失，但绑定 Ruby gem/grntest 工具链。
**DRAFT-heatshrink-…-make-cflags-commandline-override** 讨论同一"make 命令行变量"技术的 CFLAGS 追加语义，
与本条的安装工具替换语义是不同机制。
`draft-review` 实测 TOP3（2026-09-22）：E108 0.30 / E098 0.28 / E307 0.27 ⇒ 灰区 review-similar
（未触及 merge-into 阈值 0.55）。*

*实测来源：lzip 1.24.1（任务 13807）。修后 `conan-verify` G1/G2/G3/G4 全 PASS；
`build()` 内 `make check -j1` 真实执行上游 `testsuite/check.sh` 的 220 个断言块
（复算：`grep -c 'test_failed $LINENO' testsuite/check.sh` = 220），日志末行
`tests completed successfully.`。*

## 关联 Issue
- Issue：#3229 — https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3229
- 关联 PR：(本 PR，合并前由正文双向互链)
