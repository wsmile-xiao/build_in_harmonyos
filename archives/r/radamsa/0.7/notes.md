# radamsa 0.7 适配笔记

任务：积分赛。上游 radamsa（Aki Helin / OUSPG），通用型黑盒模糊测试器，产物为
单文件 CLI `radamsa`（无外部运行时依赖）。

## 上游形态

- 版本锚点：`gitlab.com/akihe/radamsa` tag `v0.7`（annotated tag object
  `71125d380ee30a8d3555178454d7e79e73bf2250`，指向 commit
  `40d5dec416fb5277dbbd72c04b82ba2ae039778a`，2023-11-02 "made autofuzz
  nondeterministic"）。tag 归档 sha256 `d9a6981b…f622a2` 与 Homebrew
  homebrew-core `Formula/r/radamsa.rb` 声明值逐字符一致（双源交叉核验）。
- **任务卡上的 `gitlab.com/aoh/radamsa` 是同一上游的别名路径**：2026-09 实测
  匿名访问 302 → `users/sign_in`、API 404（`git ls-remote` 要求凭据），不可作
  源码锚点；akihe 仓库公开可取，Homebrew/livecheck 同样锚定 akihe。
- 构建形态为 **Scheme 自举两段式**（非 autotools / 非 cmake）：
  1. `cc -O3 -o bin/ol ol.c` —— ol.c 即上游 Makefile `OWLURL=
     https://haltp.org/files/ol-0.2.2.c.gz` 的 Owl Lisp 引导编译器（预编译 C）；
  2. `bin/ol -O1 -o radamsa.c rad/main.scm` —— Scheme → 单文件 C 生成；
  3. `cc -o bin/radamsa radamsa.c` —— 最终单二进制。
  其中 `radamsa.c: rad/*.scm lib/hex`——`(lib hex core)` 库由上游 Makefile 在
  构建期 `git clone https://gitlab.com/owl-lisp/hex` 取得（rad/digest.scm 的
  sha256 digest 依赖）。
- 本配方将三份输入全部以 conandata 预置（主 tarball + ol 引导源 + hex 归档），
  消除构建期网络行为。hex 仓库 main 分支 tip 即
  `e95ebd38e4f7ef8e3d4e653f432e43ce0a804ca6`（2021-01-12 后无新提交），pin tip
  与 `git clone` 默认分支等价且可复现。
- **生成物确定性**：radamsa.c 由 ol 确定性生成——两次独立构建 sha256 一致
  （`2d70a4ce2606a4801d1b0842449191d0fe361ca006caeb04f3e0ce22a4014095`），
  这是对生成物打补丁可稳定套用的前提。
- 上游测试：`tests/run`（Makefile `test:` 目标 → `.seal-of-quality`）。遍历
  `tests/*.sh` 共 28 项，每项**最多重试 40 次**（模糊断言是概率性的，失败重试
  是设计而非掩盖），并用 `bin/ol -e '(iota 0 1 40)'` 生成尝试序列。`*.sh_` 后缀
  是上游停用命名（blank 模板 + tcp-client/tcp-serve 网络守护形态，共 3 项）；
  `tests/pcapng/` 2 项未接入 runner；`tests/benchmark` 非性能断言。N=28 的四种
  口径中取「框架注册数」（runner 的 glob 结果），候选数法其余口径均 ≤28。

## OHOS 平台缺陷与补丁（patches/0001）

一手实测（探针源码与读数见 `reports/`）：**OHOS 上字符设备（/dev/null、
/dev/zero）的 poll(2)/select(2) 永不报告 POLLOUT**——零超时返回 0（不可写）、
有限超时超时返回 0、无限超时永不返回；而普通文件与管道（含 pipe write-end 的
无限等待）报告正确，/dev/null 的 POLLIN（读就绪）也正确。

Owl Lisp VM 向端口写入前以 `do_poll`（`select()`，写集，无限超时）等待写就绪，
因此 **stdout 重定向到 /dev/null 时 radamsa 永久挂起**。上游 README 的标准用法
`radamsa -n 100000 ... > /dev/null` 与上游测试套件（tests/1k.sh 等 14 项）全部
踩中。补丁在 `do_poll` 内对写集 fd 做 `fstat` 预检：字符设备直接判为可写立即
返回；管道/套接字/普通文件保持原生 select 路径（它们的写就绪报告正确，且管道
需要真实的背压语义）。

补丁应用点特殊：目标文件 radamsa.c 是**构建期生成物**，所以补丁由
conanfile.py `build()` 在生成步之后、最终编译之前显式 `patch -p1` 应用，
不能走构建前的常规源码补丁机制。补丁可对净生成物稳定套用（确定性见上）。

## 其它适配要点

1. R33：编译器从 `tools.build:compiler_executables` 取（CI 上 `$CC` 为空）。
2. man 页：上游 `install` 用 `gzip -9`（带时间戳不可复现），配方改为安装未压缩
   `doc/radamsa.1`（同 Homebrew 的处理理由）。
3. 上游 Makefile 的 `install` 还写 `share/man`；本配方 package() 等价安装
   `bin/radamsa` + `share/man/man1/radamsa.1` + `licenses/LICENCE`。
4. 性能口径：文件输入 n≥1000 的生成在设备上需数十秒（实测 n=1000 约 10s、
   n=5000 约 51s，超线性于样本大小）；上游 1k.sh（stdin 1 字节样本）约 3s。
   逐用例超时须给足（本任务验证用 90s），不能按普通 CLI 的秒级经验值。
5. `tests/run` 的重试语义（40 次）在验证脚本中逐字复刻； toybox `timeout` 实测
   不杀子进程树（子进程存活、命令不返回），验证脚本改用 python 子进程超时。
6. 层1 上游测试在构建树内执行并留档 `reports/upstream-tests.md`；
   test_package 承载 8 项断言（4 上游功能复验 + 4 鸿蒙特有，见
   `test_package/MANIFEST.yml`）。
7. 新包首版：`archives/r/radamsa` 在 upstream/main 不存在，属全新包
   （task_init.sh `--allow-unpublished` 放行）；软件级 `commands.json` 按 R38
   新建（type=tool，ref 对齐 radamsa/0.7）。
---

**编译结束**: 2026-09-22 01:10
**最终状态**: built
