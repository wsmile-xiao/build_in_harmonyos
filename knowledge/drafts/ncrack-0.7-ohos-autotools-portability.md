# ncrack-0.7-ohos-autotools-portability — OHOS 上 autotools 适配的三个可复用要点

> 路径 B 知识草稿（与 ncrack 0.7 归档同 PR 交付）。来源：ncrack 0.7 设备实机适配（PR #9808）。
> 三个要点彼此独立，均可迁移到其它 autotools 项目。

## 要点 1：autoconf 的 `exec 7<&0` 在 OHOS 上跑不起来

- 现象：`./configure` 立即失败，报 `./configure[557]: 7<&0 : bad file descriptor`；
  换成 zsh 后变成 `./configure:557: 0: bad file descriptor`。
- 根因：autoconf 2.69 生成的 configure 第 557 行是
  `test -n "$DJDIR" || exec 7<&0 </dev/null`（保存 stdin）。OHOS 的 `/system/bin/sh`
  是 toybox，**不支持多位数 fd 重定向**；而 worker/CI 执行 job 时 **fd 0 是关闭的**，
  所以即便换成支持 fd>9 的 shell，这一行仍会因为 fd 0 无效而失败。
- 修法：①`CONFIG_SHELL`/`SHELL` 指向 `/usr/bin/zsh`（系统镜像自带，`zsh 5.9`，musl 构建；
  autoconf 的 shell 自举块在 fd-7 行**之前**，会自动 re-exec 成 zsh，`AC_CONFIG_SUBDIRS`
  递归同样继承）；②调用 configure 时显式 `< /dev/null` 提供有效 fd 0。
- 边界：不要用 `/data/service/hnp/bin/bash` 作为唯一依赖——它属于应用层挂载的工具链
  （`installs` 用户），CI worker 上未必存在；`/usr/bin/zsh` 与 `/system/bin/sh` 同批属于系统镜像。

## 要点 2：hmdfs 按「组」判目录通行，`umask 077` 的临时目录会 EACCES

- 现象：configure 跑到 `config.status` 阶段报
  `permission denied: ./confXXXXXX/subs1.awk` → `could not setup config files machinery`；
  若只改顶层 configure，子目录递归会接着报 `configure: error: ./configure failed for nbase`。
- 根因：configure 与 config.status 都用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，
  得到的是 **2700（`drwx--S---`）**；而 hmdfs 的目录通行是按**组**判的（本机所有目录都是
  `drwxrws--x`），组无 x → 目录不可穿越 → 其内一切读写全部 EACCES。
- 修法：把**所有** configure（顶层 + 每个 `AC_CONFIG_SUBDIRS` 子目录）的 `umask 077` 改写为
  `umask 022`（022 下得到 `drwxr-s--x`，可穿越）。实测 `chmod g+rx` **无效**（hmdfs 不落实 Unix
  权限位），所以只能从 umask 入手。建议以「每份 configure 恰含 2 处 `umask 077`」为契约断言，
  上游改版后能立刻发现。
- 边界：本要点与 packetq/libxrandr 的历史做法同源；本文补充了两点：①子目录也必须改；
  ②真实机制是 hmdfs 的组通行语义（而非"防止 DESTDIR 产物权限 600"）。

## 要点 3：同一源码编两个 TU → tentative definition 重复符号（且 `-fcommon` 在 CI 可能不生效）

- 现象：链接期 `ld.lld: error: duplicate symbol: umac_ctx`，`umac.o` 与 `umac128.o` 各定义一次。
- 根因：opensshlib 的 Makefile 用**同一份** `umac.c` 加 `-DUMAC_128` 再编出 `umac128.o`；
  而 `umac.c` 里有 `struct umac_ctx { ... } umac_ctx;`——无初值的文件作用域变量，即 C 的
  tentative definition。GCC≤9 / 显式 `-fcommon` 下它是 COMMON symbol（可合并），
  clang≥11 默认 `-fno-common` 下就是两个强定义 → 重复符号。
- 修法（关键经验）：**别只加 `-fcommon`**。本项目实测：设备侧加 `-fcommon` 通过，但同一配方在
  CI worker 上仍复现该重复符号（两侧的编译标志传播路径不同）。可靠做法是**结构性消除**——
  确认该全局**从未被使用**（grep 区分「类型使用 `struct umac_ctx`」与「变量定义」），
  用补丁删掉它的声明符（`} umac_ctx;` → `};`）。删掉后两个 TU 只剩各自 TU 内的类型名，
  重复符号在任何 `-fcommon` 设置下都不可能再出现；`-fcommon` 可保留作为年代语义兜底。
- 验证：`patch -p1 --dry-run` 通过；CI 覆盖后确认链接通过。

## 附：本包其余五项（见 `archives/n/ncrack/0.7/notes.md`）

显式双三元组（2019 版 config.sub 不认 ohos）、openssl 为硬依赖（`ntlmssp.cc` 无条件 include）、
opensshlib 自有 OpenSSL 检查需 `--with-ssl-dir`、`-std=gnu++14`（C++17 移除 `register`）、
E549 ELF 自签名与 `$NCRACKDIR` 数据目录定位。
