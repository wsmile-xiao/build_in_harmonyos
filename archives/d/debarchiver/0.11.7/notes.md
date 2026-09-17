# debarchiver 0.11.7 OpenHarmony adaptation

## Source

- URL: `https://deb.debian.org/debian/pool/main/d/debarchiver/debarchiver_0.11.7.tar.xz`
- 93764 字节；sha256 `4517e667b576013d5fa3cf683508aecc722180aaccf7a1c0d9d956030901c093`
  （与官方 Content-Length 逐字节一致）

## ⚠️ 硬前置：opalmod

`debarchiver.pl` 在 **BEGIN 阶段**即加载 OpaL 模块：

```perl
use OpaL::action qw(pdebug action cmdaction ...);
use OpaL::read   qw(readfile readcommand);
```

Debian `control` 亦声明 `Depends: opalmod (>= 0.1.10)`。缺它连 `--version` 都跑不了
（实测 `Can't locate OpaL/action.pm` → `BEGIN failed`）。

→ 按仓库「依赖任务先行」惯例，**先适配 opalmod 0.2.2.1**（本仓库 PR #9708），
本配方以 `self.requires("opalmod/0.2.2.1")` 声明该依赖。

## Adaptation

纯 Perl 脚本，无编译步骤。四个适配点：

| # | 适配项 | 说明 |
|---|--------|------|
| 1 | **shebang 改 `env perl`** | 上游 `#!/usr/bin/perl`，而 **OHOS 无 `/usr/bin/perl`**（perl 由 ohpcd 的 perl 包提供，位于包内 `bin/`）→ 改为 `#!/usr/bin/env perl` 由 PATH 解析。配方在 `source()` 中改写**并自校**首行确实生效 |
| 2 | ★ **不调 `make install`** | 上游 `src/Makefile` 与 `conf/Makefile` 均用 **`install -m755` / `install -m644`** 落盘，而 **OHOS 无 coreutils `install`（E188）**（实测 `command -v install` 为空）→ 由配方按上游布局自行落盘（`bin/` + `etc/` + `share/man/man1`）|
| 3 | **man 页改用 `Pod::Man`** | 上游 `po4a/Makefile` 依赖 `podselect`（**ohpcd 的 perl 包内无 `Pod::Select`**）与 `po4a`（未适配）→ 改由 perl 自带的 `Pod::Man` 直接从 `debarchiver.pl` 的内嵌 POD（75 个指令）生成 `debarchiver.1`（实测 16455 字节）|
| 4 | **运行期目录不硬改** | `$inputdir`/`$destdir`/`$cachedir` 默认指向 `/var/lib`、`/var/cache`；目录不存在时脚本 `chdir` 失败 → `EXIT: 2`。**实测 `--configfile` 可覆盖**，故包本身保持上游默认值，由使用者/测试提供配置 |

R32：`settings.os` 判断用 `in ("Linux", "OHOS")`。R33：不依赖未定义的 shell 变量。

## Verification

- `conan create`（`ohos-aarch64` profile）：**EXIT=0**
- `test_package/run_debarchiver_tests.py`：**9/9 通过**
  1. `bin/debarchiver` 存在且可执行
  2. shebang 已正确改写为 `#!/usr/bin/env perl`
  3. **依赖 opalmod（`OpaL::*`）已被真实加载**（无 `Can't locate OpaL`）
  4. `--help` 真实执行并输出 `Usage: debarchiver`
  5. `--version` 真实执行成功
  6. 负向：不给 `--configfile` 时因硬编码 `/var/lib` 不存在而失败（证明 ⑤ 非恒真）
  7. `etc/debarchiver.conf` 已随包
  8. `etc/logcheck/ignore.d.workstation/debarchiver` 已随包
  9. man 页已生成并随包（16455 字节）

### ★ 实测发现：上游版本串与包版本不一致

```
$ debarchiver --configfile <conf> --version
Debian package archiver, version 0.10
```

上游脚本内的版本串是 **0.10**，而 Debian 包版本是 **0.11.7**（上游未同步更新该字符串）。
测试断言按**实测输出**写 —— 若按包版本 0.11.7 断言会假失败。已在 test_package 中注明。

### ★ 实测踩到的三个具体问题（均已修）

**① 上游脚本不是 UTF-8（Latin-1）—— shebang 改写必须走二进制**

`debarchiver.pl` 实测为 **Latin-1**：offset 924 处 `0xe9` 是作者名 "Valéry Perrin"
的 `é`（全文件 14 个非 ASCII 字节）。用 `replace_in_file`（默认按 UTF-8 解码）会抛：

```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 924
```

→ 改为**二进制**改写：只替换首行、其余字节逐字节保留（配方内含自校，断言首行外
内容未变）。

**② 上游对 logcheck 文件改了名，须同步重命名**

`conf/Makefile:25` 把源文件 `debarchiver.logcheck` 装成
`/etc/logcheck/ignore.d.workstation/**debarchiver**`（去掉 `.logcheck` 后缀）。
配方若只 `copy()` 会保留原名 → 落盘布局与上游不一致（测试曾因此失败）。

**③ ★ `package_type="application"` 使传递依赖的 `runenv_info` 不传播**

`debarchiver` 依赖 `opalmod`（`use OpaL::*`），而 opalmod 的 `package_info()` 用
`runenv_info.append_path("PERL5LIB", ...)` 声明模块路径。但实测**该路径不会传递到
消费者**：

```
$ conan install --requires=debarchiver/0.11.7 -g VirtualRunEnv
Skipped binaries
    opalmod/0.2.2.1
```

对照实验（同一命令）：

| 依赖声明 | 消费者 runenv 中 opalmod 路径数 |
|---------|------------------------------|
| 仅 `debarchiver/0.11.7`（经传递）| **0** ← 失败 |
| `debarchiver/0.11.7` + `opalmod/0.2.2.1`（直接声明）| **8** ✅ |

→ 被 skip 的依赖，其 `runenv_info` **不会**进入聚合环境。故：

- **`test_package` 中必须直接声明 `opalmod/0.2.2.1`**（本包运行期确实需要 OpaL，
  直接声明是正确语义），否则测试报 `Can't locate OpaL/action.pm in @INC`；
- 配方 `package_info()` 中试图经 `self.dependencies["opalmod"]` 自行补 PERL5LIB
  **不可行** —— 该阶段取不到依赖的 `package_folder`（实测输出
  `未取到 opalmod 的 package_folder`，WARN 可见）；
- **真实消费者**若需运行 `debarchiver`，应在其图中**直接声明 `opalmod`**（或自行把
  opalmod 的 `lib/perl5/...` 加入 `PERL5LIB`）。本包已在 README 中声明该使用要求。

## ⚠️ 已知限制：核心功能依赖的外部工具在 OHOS 上不可得

debarchiver 的核心功能（收 `.changes`、建 apt 索引、gpg 签名）依赖下列外部工具，
**在 OHOS 上全部不可用**（实测 `command -v` 均为空）：

| 外部工具 | 用途 | OHOS |
|---------|------|------|
| `apt-ftparchive` | 生成 Packages/Sources 索引 | ❌ |
| `dpkg-scanpackages` | 包扫描建索引 | ❌ |
| `dpkg-deb` | 解析 .deb | ❌ |
| `gpg` | 签名 Release | ❌ |
| `adduser` | 用户管理 | ❌ |

→ 因此本包在 OHOS 上**可安装、可运行（`--help`/`--version`/参数解析/配置加载均正常）**，
但**无法完成完整的收包与建索引流程**（同 apt 链的既有结论，属功能限制而非适配缺陷）。
本配方与 test_package **如实声明**该限制，未伪称功能可用。

> 这与 `cron-apt` 的情形同类：脚本本身能跑，但其功能依赖的上游工具链在 OHOS 不可得。
