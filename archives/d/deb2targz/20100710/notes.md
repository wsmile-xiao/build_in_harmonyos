# deb2targz 20100710 OpenHarmony adaptation

## Source

上游**不是归档**，而是作者 Mike Taylor 个人站点上的单个 Perl 脚本：

- URL: `https://www.miketaylor.org.uk/tech/deb/deb2targz`
- 1947 字节；sha256 `f597319db098a9d6b5199e39b8a9ced0973d9ee84927286de4d5816d8e76a44b`
- 上游**不带版本号**：Gentoo（`app-arch/deb2targz-1-r3`）与 FreeBSD
  （`archivers/deb2targz`）都以日期 `20100710` 作为发行版本号，本配方沿用。
- 该包**不在 Debian 官方仓库**（`sources.debian.org` 与 snapshot 均查无此包）。

## Adaptation

只有一个适配点，但它是"不修就装出不可执行脚本"的两处耦合问题：

**shebang 改写**（`#!/usr/bin/perl -w` → `#!/usr/bin/env perl`）

1. **OHOS 无 `/usr/bin/perl`** —— perl 由 ohpcd 的 `perl/5.42.2` 提供，位于包内
   `bin/`，故改为 `/usr/bin/env perl` 由 PATH 解析。

2. **必须同时去掉 `-w`** —— `#!/usr/bin/env perl -w` 是**错误写法**：内核只把
   shebang 首个空白之后的全部内容作为**一个参数**传给解释器，于是 `env` 收到的
   是单个字符串 `"perl -w"`，会去找名为 `perl -w` 的程序而失败（实测
   `env: exec perl -w: No such file or directory`）。脚本内已有 `use strict;`，
   功能无损失。

配方在 `source()` 中直接改写，并**自校两件事**：首行确为 `#!/usr/bin/env perl`、
且不含 `-w`（避免补丁静默失效后仍"构建成功"）。

此外：

- 上游是**裸文件非归档** → 须用 `download()` 而非 `get()`（后者会尝试解压）。
- 运行期依赖 `perl/5.42.2`（ohpcd 已发布）；脚本仅用核心模块 `strict` + `IO::File`。

## ⚠️ 测试环境的坑：`env perl` 会解析到设备上的另一个 perl

本包产品是 `#!/usr/bin/env perl` 脚本，**perl 由 PATH 解析**。设备上可能同时存在
**多个 perl**（实测本机 `/data/service/hnp/bin/perl` 为 **5.42.0**、conan perl 为
**5.42.2**）：

```
# 依赖 runenv 未应用时
环境诊断: perl=/data/service/hnp/bin/perl        ← 解析到设备 perl（5.42.0）
[FAIL] 转换执行失败 rc=22: Can't load '.../perlbad96edf51f7f/p/lib/perl5/5.42.2/
       aarch64-linux-thread-multi/auto/IO/...'
IO.c: loadable library and perl binaries are mismatched
      (got first handshake key 0xf880080, needed 0xf180080)
```

它加载的是 **conan perl 的 XS 模块 `IO.so`**，执行的却是**设备 perl** —— 两者
XS 握手密钥不同、**不可互载**。

**修法**：`test()` 中 `self.run(..., env="conanrun")` **显式应用**依赖 runenv。
⚠️ 只 `generate()`（`VirtualRunEnv`）而**不应用**是**无效**的 —— 先前正是漏了这步。
修正后 `PATH 首位` 变为依赖 perl 的 `bin`：

```
环境诊断: perl=.../perlbad96edf51f7f/p/bin/perl   ← 解析到依赖 perl（5.42.2）
环境诊断: PATH 首位=.../deb2t2cf29550a0753/p/bin
RESULT: passed=7 failed=0 skipped=0
```

> 相关既有条目：`DRAFT-6049`（libnxml）记录了同一**握手不匹配机制**，但其语境是
> **构建期**（conanbuild 的 PERL5LIB 指向 conan perl），修法是"统一改用系统 perl"；
> 本条是 **test_package 运行期**，修法是应用依赖 runenv。两者互补。
> `E428`（pico-sdk）亦用 `env="conanrun"`，但其失败模式是工具**找不到**（bash -lc
> 丢 PATH），不是解释器 ABI 不匹配。

## Verification

- `conan create`（`ohos-aarch64` profile）：**EXIT=0**
- `test_package/run_deb2targz_tests.py`：**6/6 通过**
  1. `bin/deb2targz` 存在且可执行
  2. shebang 确为 `#!/usr/bin/env perl`
  3. shebang 未携带 `-w`
  4. **负向**：非 `.deb` 输入被正确忽略（打印 `ignoring`）且不产生输出文件
  5. **true 正向**：Python 现场按 ar 格式手工构造一个含真实 tar 数据的 `.deb`
     → 执行转换 → **输出与原始 `data.tar.gz` 逐字节一致**
  6. 转换后的 `.tar.gz` 能被 `tarfile` 解开且含预期文件

> 第 5 项是本包唯一职责的直接验证 —— 不是"文件存在"，而是"转换结果正确"。
> 手工构造 `.deb` 无需 `ar`/`dpkg-deb`（该脚本本身按字节解析 ar 格式）。

## 与 debarchiver 的区别

两者**名字相近但无关**：`debarchiver` 是 Debian 官方的仓库管理工具
（Perl，`debarchiver.pl`，依赖 `OpaL::*`）；`deb2targz` 是单文件转换脚本。
