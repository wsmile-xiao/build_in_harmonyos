# yaku-ns 0.2 适配笔记

## 任务

- 三方库：`yaku-ns` 0.2（Salvatore Sanfilippo 的微型 DNS 服务器 + `yaku-getzone` AXFR 客户端）
- 目标平台：HarmonyOS PC / OpenHarmony `aarch64-linux-ohos`
- 分支：`feat/yaku-ns-0.2`

## 上游与源码来源

- 上游仓库 <https://github.com/antirez/yaku-ns> **没有 0.2 tag，也没有 release tarball**：
  其 master 至今仍是 `ENS_VERSION "0.1.6"`（tunable.h:9），最后一次提交是 2010-12-09。
- 0.2 这个发行版实际由 Debian 维护者发布，tag `0.2` 在 `alexmyczko/yaku-ns`。
- 实测两个来源字节一致：

  ```
  https://deb.debian.org/debian/pool/main/y/yaku-ns/yaku-ns_0.2.orig.tar.gz
  https://github.com/alexmyczko/yaku-ns/archive/refs/tags/0.2.tar.gz
  → 两者 sha256 均为 9ad94c49d399d7b3b19e9042dd7a9413082d90c1f8efedb68f60332ef59c3fe6
  ```

- conandata.yml 采用 Debian pool URL：它是该发行版的权威、不可变分发通道，且不依赖
  任何单一 Git 主机的可达性。sha256 即上述双源核对值。

内容与 antirez master 的差异集中在发行/打包层面：`getzone` 改名为 `yaku-getzone`、
`DESTDIR` 改为 `/usr/bin/`、新增两个 man page、`check` 规则被注释掉、删除 `RFCs/`
目录、`sign` 规则里 `MD5SUM.SIGNED*` 的拼写修正，以及 `tunable.h` 默认配置路径改为
`/etc/yaku-ns/yaku-ns.conf`。

## W0/W0b 前置核验

- **依赖发布检查（W0/R35）**：本包**零第三方依赖**——上游全部代码是纯 C + POSIX socket，
  Makefile 里没有任何 `-l`（不链 libm 也不链任何库）。因此无依赖需要探测，`requirements()`
  为空，L0i 无可解析项。
- **CI 能力矩阵（W0b）**：只需 clang/make，CI 全部具备，无需 `tool_requires` 补齐。
- **语言预检（R47）**：源码为 C（22 个 `.c`），与任务语言 cpp 兼容族一致 → 继续。

## 交付物

`bin/yaku-ns`（DNS 服务器）、`bin/yaku-getzone`（AXFR 客户端）、
`etc/yaku-ns.conf.example`（上游自带注释样例配置）、`licenses/COPYING`（GPL-2.0）。

## 配方机制

- `layout()` 用 `basic_layout()`，编译在 `source_folder` 内进行（上游 Makefile 就地编译），
  生成的版本头文件落在 `build_folder`。
- 编译器从 `self.conf.get("tools.build:compiler_executables")` 取，不依赖 shell 里的
  `${CC}`（R33 / L0h）。
- `CFLAGS` 在 make 命令行覆盖（上游 Makefile 内部是 `CFLAGS= ...` 赋值，命令行赋值优先级
  更高）：Release 为 `-O2 -Wall -I<build_folder>`，Debug 为 `-O0 -g -Wall`。用 `-Wall`
  取代上游那个早已废弃的裸 `-W`；Release 不带 `-g`，免得打包产物携带调试信息。
- `build_type` 参与 `package_id`，因此两种 build_type 必须真的给出不同的优化级别，
  不能产出字节相同却 `package_id` 不同的包。
- `package()` 对两个二进制都走 `copy()` + `os.chmod(0o755)`：HMDFS 上 install 出来的
  文件可执行位不可靠（知识库 E046 一族），重新拷贝并显式 chmod 才可靠。
- OHOS 下用 `binary-sign-tool` 签名；工具不可达时告警跳过而非报错（与本仓其他
  application 配方一致），因为签名是部署形态问题，不该让非 OHOS 构建失败。

## 补丁（2 个）

### 0001-nameser-portability.patch — 必须，否则整个包编不过

`nameser.h` 是 1993 年版 BSD `arpa/nameser.h` 的逐字拷贝。它使用
`__BEGIN_DECLS` / `__END_DECLS` / `__P()` 和 `u_char` / `u_int16_t`，却从未 include
定义它们的头文件。

- glibc：`<features.h>` 会间接拉进 `<sys/cdefs.h>`，所以恰好能编过（历史包袱）。
- musl（OHOS 的 libc）：`<features.h>` 不做这件事，于是**每个编译单元**都报：

  ```
  nameser.h:253:1: error: unknown type name '__BEGIN_DECLS'
  nameser.h:304:27: error: expected ';' after top level declarator
  ens.h:279:31: error: unknown type name 'HEADER'      ← 连带 HEADER 类型丢失
  ```

补丁只加两行 `#include <sys/cdefs.h>` + `<sys/types.h>`，让该头文件自包含。两种 libc
下都正确，**不改动任何上游逻辑**。

### 0002-cli-long-options.patch — 让打包冒烟与 CLI 惯例可用

上游两个命令都不支持 `--version`：选项解析是仅含短选项的 `getopt()`，而 `-h` 打印用法后
以 **1** 退出。CI 的 L2 冒烟（先试 `--version` 再试 `--help`）与常规 CLI 约定都期望这两项
成功。补丁改用 `getopt_long()` 并新增 `--version` / `--help`，**既有短选项行为逐条不变**
（`-h` 现在以 0 退出，这是唯一的行为变化，且是修正而非回归；未知选项仍以 1 退出，由
test_cli.py 第 5 项断言守住）。

版本号经 `-I` 注入的 `yaku-version.h`（`YAKUNS_PKG_VERSION`）提供。之所以不直接用
`tunable.h` 的 `ENS_VERSION`：上游发布 0.2 时忘了更新它，至今仍写着 `0.1.6`。非 Conan
构建下补丁自动回落到 `ENS_VERSION`，行为不变。

## 上游测试

**上游 0 个用例。** 0.2 的 Makefile 里 `check` 目标被注释掉了（只剩一行
`md5sum -vc MD5SUM.SIGNED.asc` 的历史残留，在该 tag 中同样被注释），源码树没有 `tests/`、
没有 `configure`、没有 automake。因此不存在"测试减少"的问题，全部验证由消费者测试承担。

## 本次新增的消费者测试（15 项断言，3 个测试程序）

全部执行**打包后**的 `bin/yaku-ns` / `bin/yaku-getzone`，无一是 echo/print 空壳
（R34 / L0c / L0d / PF3）。响应都在测试内自行解析 DNS 报文，不靠守护进程日志断言。

- `test_cli.py` — **5 项**：两者的 `--version` / `--help` 均 0 退出且输出正确；
  未知长选项在两者上均 1 退出。这一条专门防"选项解析被架空"——若配方吞掉全部参数，
  前四项照样能过。
- `test_elf_abi.py` — **3 项**：直接读 ELF 头，确认两个产物都是 ELFCLASS64，且
  `e_machine` 与小端序符合目标架构。期望值由调用方按 `settings.arch` 传入
  （OHOS CI profile 的 `armv8` → `EM_AARCH64` = 183）而非写死——这样配方
  `validate()` 承诺的 Linux/OHOS 平台集在非 aarch64 宿主上同样成立，不会出现
  "配方接受、测试拒绝"的自相矛盾。该测试只读磁盘字节，不需要可运行目标，
  排在 `can_run()` 闸之前执行。
- `test_dns_service.py` — **7 项（鸿蒙特有）**：用生成的 zone 在回环高位端口拉起**打包后的
  守护进程**，发真实 DNS 报文断言 A 记录解析（192.0.2.10）、区外名字 NXDOMAIN（rcode 3）、
  MX（preference 10 + mail.example.com）、TXT、NS，以及 TCP（2 字节长度前缀）SOA 查询。
  端口动态申请，避免与 CI 上其他任务撞端口。

`test()` 在目标不可运行时**明确失败而非跳过**：本包的交付物就是一个 DNS 服务器，
静默跳过运行期测试恰好会让最该防的回归不被观测。

## 上游缺陷：不修，如实记录

`axfr_out.c:send_zone()` 的哈希表遍历有 off-by-one：`index++` 发生在 `ht_value(&local_table, index)`
**之前**，导致取到越界槽位，`rr->qtype` 解引用崩溃，AXFR 子进程被 `SIGSEGV` 打断
（守护进程日志可见 `SIGSEGV trapped -- INTERNAL ERROR` + `dump_state()` 转储）。

- **这是上游缺陷，不是移植问题**：同一份源码用本机 x86-64 glibc 原生编译，AXFR 同样崩溃。
- 因此 `patches/0002` 刻意不动它。本包测试用 TCP **SOA** 查询走同一个 AXFR 服务套接字，
  既覆盖 TCP 路径又不进入那个有 bug 的循环。
- 完整 AXFR 区域传送属于未覆盖路径，已在此记录，供上游修复后跟进。

## 本地（WSL）执行的已知环境限制

OHOS 的 `<sys/select.h>` 把 `FD_SET` 定义成会调用 `__fd_chk()` 的宏。

- **真机 CI worker**：用的是真 OHOS libc，`__fd_chk` 有导出（`readelf --dyn-syms` 实测
  `69: __fd_chk FUNC GLOBAL DEFAULT 13`），二进制正常执行。
- **本机 WSL**：`/opt/ohos-guest` 的 guest musl 1.2.6 早于该符号，动态加载报
  `Error relocating ./yaku-ns: __fd_chk: symbol not found`，`exit 127`。

这是**跨宿主产物差异**，不是包缺陷（与记忆库 T017 同一形态：exit 127 + 空输出 = loader
类，非内容类）。本地跑运行期测试时用一个**仅供本地验证**的 `LD_PRELOAD` shim 补出该符号
即可（x86 宿主会刷 `cannot be preloaded` 噪声，属正常）。该 shim：

- 不在配方里、不在 `test_package` 里、不随 PR 提交；
- 只用于本机自证"内容是好的"，已在交付报告中标注本地/CI 运行环境的这一差异。

**红线自查**：`grep -rn 'fdchk\|LD_PRELOAD\|preload' archives/y/yaku-ns/` 只会命中
本文件的这几行说明文字，不命中 `conanfile.py` 或任何测试程序。

## 数字小结

| 项 | 值 |
|---|---|
| 上游测试用例 | 0（无测试套件） |
| 消费者断言总数 | 15（CLI 5 + ELF 3 + DNS 7） |
| 其中鸿蒙特有 | 7（真实 DNS 服务交互） |
| Conan 依赖 | 0 |
| 补丁 | 2 |

最终状态：built
