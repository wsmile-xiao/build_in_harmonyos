# nodebrew 1.2.0 — 适配笔记

## 软件信息
- 上游: https://github.com/hokaccha/nodebrew（官方 tag `v1.2.0`，2022-03-19）
- 语言: Perl（`#!/usr/bin/env perl`，纯脚本，无 C/C++ 编译）
- 许可证: MIT
- 构建系统: 无（custom；无 configure/make/编译器）
- 产物: `bin/nodebrew` 单脚本 + bash/zsh/fish 补全

## 适配决策
1. **纯脚本包，仿 nodenv（application）**：nodebrew 与 nodenv 同类，
   是自包含的 Node.js 版本管理器脚本。tarball 顶层只有一个可执行主脚本
   `nodebrew`（根目录，非 `bin/` 子目录）。配方以 `package_type =
   application` 打包：`package()` 将主脚本复制为 `bin/nodebrew` 并
   chmod 0755，保证消费者 PATH 可执行。
2. **无 patch**：主脚本自包含，运行目录由 `NODEBREW_ROOT` /
   `$HOME/.nodebrew` 动态决定，不硬编码绝对安装前缀，无需路径补丁；
   `conandata.yml` patches 为空。
3. **运行时依赖仅 perl 核心模块**：主脚本 `use` 的
   File::Path / File::Basename / POSIX / Cwd 均为 perl 核心模块；
   `version`/`help` 等命令不依赖 CPAN 非核心模块（cpanfile 里的
   Test::More 等仅为上游 perl 测试套件 `t/` 所需，不参与打包）。
4. **补全与许可证**：completions/{bash,fish,zsh} 按上游结构复制为
   resdir；LICENSE 复制到 licenses/。
5. **settings 四项齐全**：虽不调用编译器，但保留
   os/compiler/build_type/arch，满足 CI L0p/PF8 的交叉编译矩阵前提。

## 上游 tarball 顶层结构（实测）
```
nodebrew-1.2.0/
├── nodebrew                 # 主脚本（perl, shebang #!/usr/bin/env perl）
├── completions/{bash,fish,zsh}/   # nodebrew-completion / nodebrew.fish / _nodebrew
├── t/                        # perl 测试套件（Test::More，不打包）
├── README.md / LICENSE / History.md / cpanfile / carton.lock
```

## 验证
- 本机 perl 存在（perl 5.42.0，aarch64-linux）
- `perl nodebrew version` → 输出 `nodebrew 1.2.0` + 用法帮助，rc=0
- `./nodebrew version`（直接执行，验证 shebang 解析）→ 同上，rc=0
- test_package/test_nodebrew.sh：真实冒烟——校验 bin/nodebrew 存在、
  可执行、shebang 为 perl、`perl -c` 语法检查、`version`/`help` 输出含
  "1.2.0"，任一项失败累计计数并 exit 非 0
- sha256: `6d72e39c8acc5b22f4fc7a1734cd3bb8d00b61119ab7fea6cde376810ff2005e`

## 注意事项
1. nodebrew 运行时会在 `NODEBREW_ROOT` 或 `$HOME/.nodebrew` 下创建数据
   目录（仅执行 install/use 等写操作命令时需要可写 HOME；version/help 只读）。
2. CI 若缺少 perl 解释器，test_package 冒烟将无法执行——nodebrew 是
   perl 工具，运行期依赖 perl（基线发行版普遍预装）。
3. 无预编译二进制、无 ELF，无需签名/strip/RPATH。

---

**编译结束**: 2026-09-04
**最终状态**: built


---

## 上游测试全量运行记录（2026-09-04，PR #8193 补充验证）

### 运行环境
- perl 5.42.0（/data/service/hnp/bin/perl）；测试依赖经 cpanm（1.7049）装入私有前缀 `$HOME/perl5`（系统 site 目录零写入）。
- 补齐的 CPAN 测试模块：Test::TCP、File::Read、Plack::Loader、Plack::Middleware::Static、IO::Capture::Stdout、Test::MockObject::Extends 及其依赖（Try::Tiny、Test::SharedFork、Test::MockObject、Plack 等）。
- wget：系统默认 toybox wget 0.8.12 缺 `-S/-q/-c/--spider`（仅 -O/-d/--max-redirect/-p），导致 fetcher wget 后端失败；以 `$HOME/bin/wget` wrapper 前置 BusyBox v1.37.0 wget（完整支持 -S/-q/-c/--spider/-O/-U）后通过。属系统工具差异，非代码问题。

### 运行结果（全量 18 个 t/*.t）
| 测试文件 | 结果 | 断言 |
|---|---|---|
| t/basic.t | PASS | 15 |
| t/command_alias.t | PASS | 18 |
| t/command_clean.t | PASS | 11 |
| t/command_compile.t | PASS | 15 |
| t/command_help.t | PASS | 3 |
| t/command_install.t | PASS | 6 |
| t/command_install_binary.t | PASS | 1 |
| t/command_install_nightly.t | PASS | 4 |
| t/command_ls.t | PASS | 6 |
| t/command_prune.t | PASS | 7 |
| t/command_selfupdate.t | PASS | 1 |
| t/command_setup.t | PASS | 13 |
| t/command_uninstall.t | PASS | 10 |
| t/command_use.t | PASS | 10 |
| t/config.t | PASS | 17 |
| t/fetcher.t | PASS | 14 |
| t/utils.t | PASS | 28 |
| t/live.t | SKIP（需 LIVE_TEST=1 与真实外网 node 安装，上游设计内跳过） | - |
| **合计** | **17 PASS + 1 SKIP + 0 FAIL** | **179** |

### 可复现命令
```bash
export PERL5LIB=$HOME/perl5/lib/perl5
export PATH=$HOME/bin:$PATH          # busybox wget wrapper（可选）
cd <nodebrew 源码根>
perl -I . -I t t/<name>.t
```
