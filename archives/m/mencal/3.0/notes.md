# mencal 3.0 适配笔记

## 编译环境
- 构建系统: none（单文件 Perl 脚本，发行物无 configure/make/cmake）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4（未参与——本包无编译步骤）
- 状态: built

## 语言预检复核（R47 人工复核留证，2026-09-23）

`lang-preflight mencal 3.0 --src <源码目录>` 检测结果为 `other`（evidence：build_system=none、manifest=未发现语言 manifest 文件、source_stats=无源文件可统计），原因是主体为**无扩展名单文件脚本**，`lang_detect` 只按扩展名/构建系统统计、不嗅探 shebang。复核证据（逐字）：

```console
$ file mencal
mencal: /usr/bin/perl script
$ head -1 mencal
#!/usr/bin/perl -w
```

人工复核结论：真实实现语言为 **Perl5**（shebang + `use strict`/`use POSIX`）。按 `notes/device-facts.md` §4.2「误判不构成终止任务的依据，按…人工复核留证」，以 `--lang other`（与检测口径一致）取 rc=0 通过门禁、真实语言以上述证据留档，**不**按 perl 传参触发假 `env_unsupported` 终态（会污染 result 草稿链）。该盲区三处披露：本笔记、`feedback/pending/2026-09-23-mencal-3.0.md`、知识草稿 E684（编排方裁决 2026-09-23 确认此处置）。

## 编译步骤

上游无构建系统，`conan create` 全程：

1. `source()`：`get()` 官方直链 tarball（sha256 锚定）并 `strip_root=True` 解包；
2. `build()`：`apply_conandata_patches()` 打 `patches/0001-mencal.patch` → **shebang 守卫断言**（首行必须是 `#!/usr/bin/env perl`，否则 RuntimeError——防补丁静默失效假绿）→ 安装树装配 `install/bin/mencal`（字节级 `shutil.copyfile` + chmod 755；源为 latin-2 编码故不转码）；
3. `package()`：拷 `bin/mencal`，许可证 `LICENSE_EN.html`/`LICENCE_CZ.html`/`README` 落 `licenses/`；
4. `package_info()`：`bindirs=["bin"]`，无 lib/include（与真实产物一致，R38 软件级 commands.json 已配）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `./mencal` 直接执行 rc=126 `bad interpreter: /usr/bin/perl: No such file or directory`（实测） | 设备与 CI worker 均无 `/usr/bin/perl`（HNP perl 在 `/data/service/hnp/bin/perl`） | 补丁 `0001-mencal.patch`：shebang 改 `#!/usr/bin/env perl`（`/usr/bin/env` 实测存在=toybox；先例 abi-compliance-checker 同型已 published）；build() 内守卫断言防补丁静默失效 |
| 2 | `-w` 无法随 env shebang 保留 | toybox `env` 不支持 `-S`（实测 `env: Unknown option 'S perl -w'` rc=125） | 去掉 `-w`；实测去 -w 前后 stdout/stderr 行为一致（同一两行 stderr 均来自缺 locale，见 #4） |
| 3 | `lang-preflight` 判 `other` 与真实语言 Perl5 不一致 | `lang_detect` 按扩展名统计，无扩展名单文件恒「无可统计源文件」；不嗅探 shebang | 按 §4.2 人工复核留证（见上节逐字证据），`--lang other` 过门禁；三处披露，编排方裁决确认 |
| 4 | 每次运行 stderr 固定两行 `Can't exec "locale": ... at mencal line 334` + `Use of uninitialized value in split` | OHOS 无 `locale` 命令；`locale -c LC_TIME` backtick 失败 | 上游本身优雅降级：`split` 得空 → 默认星期头 `Su Mo Tu We Th Fr Sa` 正确输出（实测），退出码 0；测试只断言 stdout，不修上游（登记不修） |
| 5 | `-h` 首行写 `Menstruation calendar 2.1` 而 `-V` 写 3.0 | 上游 usage 文案未随版本更新（README 亦停在 VERSION 2.4） | 上游文案问题，不改（登记不修）；测试只断言 `-V` 的 3.0 版本串与 `-h` 的 Usage 行 |
| 6 | 上游无任何测试套件 | 发行物仅 4 文件（脚本+两许可证+README），无 tests/、无测试框架 | 上游 N=0 如实申报；34 条断言全部计入「鸿蒙特有测试」行（test_package 消费者断言） |

## 源码修改

- `patches/0001-mencal.patch`：首行 `#!/usr/bin/perl -w` → `#!/usr/bin/env perl`（+1/-1，`refresh-patch --auto` 按 edit-tracker 精准模式生成，conandata 已登记）。

## 依赖版本

- conan 依赖：**0**（源码仅用 Perl 核心模块 `strict`/`POSIX`，无 CPAN 外部模块；W0 硬依赖集合为空）。
- 运行期解释器：perl 由 HNP 提供（`/data/service/hnp/bin/perl` 5.42.0，短 PATH 实测可得；设备 harmonybrew 另有 5.44.0 仅设备层）。仓库 340 个 `system: perl` 包先例、abi-compliance-checker 已 published 证 CI worker 可用；ohpcd 另有 `perl/5.42.2` 三版在档，但 conan perl tool_require 有 HMFS 不可用先例（avimetaedit/burp2 配方注释）故不引入。

## 验证结果

```bash
# 直执与版本（实测，采信轮后补全量读数）
$ mencal -V            # rc=0 Menstruation calendar 3.0
$ mencal -q -y 2026     # 年视图 rc=0 输出确定（两次 cmp 一致）
$ test_package/test.sh  # 34/34 断言
```

## 注意事项

- 源码三方同源 sha256：上游官方直链 = Debian pool `mencal_3.0.orig.tar.gz` = Ubuntu pool 同名件 = `.dsc`（PGP 签名）声明，均为 `9328d0b2f3f57847e8753c5184531f4832be7123d1b6623afdff892074c03080`（19560 B）——排除「发行版改名实为另一版本」。上游主页 Download 选择器含 3.0、公告「new version 3.0 released」。
- `patch_generation`/`patch_classification` 两段由 `refresh-patch`/finish 自动回写，收尾按 §2 逐项 diff 复核。
