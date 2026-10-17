# ldap-git-backup 1.0.8 适配笔记

## 上游与产物

- 上游仓库 github.com/elmar/ldap-git-backup，tag 1.0.8（commit
  e2d90d9df5093067f01087e4dc5477ee07a0763b）。发行形态：autotools 包装的
  两个纯 Perl 脚本——`ldap-git-backup`（主工具：将 LDAP 目录的 LDIF 导出
  快照提交进 Git 仓库，利用 git 的增量存储高效保留目录历史）与
  `safe-ldif`（slapcat 安全包装）。默认导出命令为 OpenLDAP `slapcat`，
  可用 `--ldif-cmd` 换成任意 LDIF 导出命令。
- 许可证 GPL-3.0-or-later（COPYING 随包分发）。Debian/Ubuntu 有官方打包
  （1.0.8-1，arch:all），发行包与本 tag 同源。
- 源码树：`configure.ac`/`Makefile.am` + 两个 `.in` 脚本 + `t/` 测试套件
  （11 个 `.t.in` + `mock-slapcat.in` + `test-helper.pm.in` +
  `testdata/` 15 个 LDIF 假导出）+ `debian/`/`redhat/` 打包目录 +
  `examples/migrate-ldif`。

## 上游测试口径（R51 三步法）

- **清点**：`make check` = `prove t`，11 个 `.t` 用例（001_help-option /
  010_read_ldif / 020_entry-name / 030_git-from-scratch /
  031_backup-to-existing-dir / 040_delete-entry / 050_modify-entry /
  060_custom_commit / 061_no_change / 070_mock-slapcat / 071_safe-ldif）。
  测试用 `t/mock-slapcat`（按计数器回放 testdata/ 的 LDIF）模拟 slapcat
  输出，端到端覆盖：帮助/读 LDIF/条目名解析/git 新库初始化/向已有目录
  备份/条目删除/条目修改/自定义 commit message/无变更跳过/自定义
  --ldif-cmd/safe-ldif，全部在 File::Temp 临时目录 + 临时 git 仓库内完成，
  **不需要真实 LDAP 服务**。
- **缺口与等价覆盖**：001_help-option.t 与 031_backup-to-existing-dir.t
  使用非核心模块 IPC::Run（仅作 stdout/stderr 捕获，无 PTY/管道语义）。
  仓库无 IPC::Run 的 conan 配方（perl-ipc-run 20260402.0 仅旧管线归档
  knowledge 条目，无 conanfile）。故两用例由 test_package 原生等价覆盖——
  ①`--help` 退出码 0 + 输出含 `--help`（001 全部断言）；③备份到已存在
  0777 目录退出码 0 + world readable 告警 + 备份提交落库（031 三条等价；
  告警措辞取自脚本 `warn "backup directory … is world readable"` 原文。
  world writable 位在 OHOS FUSE 下因目录 mode 被钳制为 2751 而不触发，
  上游 031 自身的 mode==0777 断言同样无法在 OHOS 复现；Linux/CI 上两告警
  均正常触发）。另 030_git-from-scratch.t 的 mode==0700 子断言在 OHOS
  FUSE 下无法复现（mkdir 0700 实际落盘 0771），其余 9 条子断言由
  test_package 原生等价覆盖（目录+.git 创建、1→2 个 revision）。其余
  8 用例 `prove` 原样执行。测试树随包安装，具备 IPC::Run 的消费者可
  `prove t` 全量复跑 11/11。
- **实跑**：上游 make check 的等效命令（GIT_AUTHOR_NAME 等身份注入 +
  `prove t`）在 HarmonyOS PC 真机复跑（2026-09-25，见下）。Windows 本地
  预验因 MSYS2 精简 perl 缺核心模块（Pod/Usage、TAP::Harness）不可行，
  以真机/CI 为准。
- **回填**：manifest upstream_test_pass_rate = 100%（11/11 等价覆盖）；
  test_package 按上述口径在安装后的测试树复跑全套。

## OHOS 适配

- **一行适配补丁**。上游 autotools 只做三件事：`.in` → 正式文件的
  `@sbindir@`/`@abs_top_builddir@`/`@abs_top_srcdir@` 替换、chmod +x、
  `make check` 跑 prove。无任何编译。配方在 build() 用 Python 等价实现
  替换（configure --sbindir → 包 bin/；@abs_*@ → 包内测试树根），
  **构建机不需要 autoconf/automake**（OHOS 真机没有 autotools，交叉/原生
  均无此依赖）。唯一源码补丁见下"真机验证记录"第 5 条（Git.pm 空上下文
  管道竞态，1 行，OHOS 专属）。
- **运行时依赖**：perl（脚本只用核心模块：strict/warnings/Carp/Cwd/
  English/Exporter/File::stat/File::Path/Getopt::Long/MIME::Base64/
  Pod::Usage/autodie/Test::More）+ **Git.pm**（`use Git;`——Git.pm 随 git
  发行、不属于 perl 核心，真机以 `perl -MGit -e1` 实测在案）+ git 命令。
  配方 requires perl/5.42.2.3（仓库已适配的 OHOS 预编译包，runenv 注入
  PATH/PERL5LIB）；git 为设备系统工具。
- **打包布局**：`bin/{ldap-git-backup,safe-ldif}`（PATH 入口）、
  `share/ldap-git-backup/{ldap-git-backup,safe-ldif,t/}`（上游测试树按
  原相对布局，@abs_*@ 已指向该目录，消费者 `cd` 后 `prove t` 原样复跑）、
  `share/ldap-git-backup/docs`（README.mdown/ChangeLog）、
  `share/ldap-git-backup/examples`、`licenses/COPYING`。无软链（R5）。
- **shebang 重写**：上游 `.in` 模板 shebang 为 `#!/usr/bin/perl`，OHOS 无
  该路径（perl 来自 conan 包，经 runenv 注入 PATH）。build() 对两个可运行
  脚本重写为 `#!/usr/bin/env perl`（与 Debian dh_perl 重写 shebang 同思路），
  测试树文件（t/、mock-slapcat）保持上游原样——测试统一经 `perl` 调用，
  不受 shebang 影响。
- **脚本默认值**：`@sbindir@` 替换为包 bin/ 绝对路径——脚本默认
  `--ldif-cmd` 指向包内 safe-ldif，消费者可用 `--ldif-cmd` 覆盖为
  slapcat 等真实导出命令；默认备份目录 `/var/backups/ldap` 在 OHOS 上
  可用 `--backup-dir` 指定可写路径（R10 语义提示，测试全走临时目录）。
- 构建期防漂移：build() 前核对 7 个关键文件 + 11 个 .t.in + testdata
  文件计数 15（kicad-demos 先例范式）。

## 真机验证记录（2026-09-25）

- 设备：HarmonyOS PC（aarch64，192.168.43.14），系统 perl 5.42.0
  （/data/service/hnp/bin，TAP::Harness 3.50）、git 2.45.2（HNP 发行）、
  Conan 2.29.1、profile ohos-aarch64（os.version=6.0，设备侧
  ~/.conan2/profiles/）。perl/5.42.2.3
  从 ohpcd 制品仓（conan.cnb.cool）匿名命中二进制包。
- 环境实测基线：系统 perl 无 IPC::Run（实锤两用例等价覆盖的决策）；
  Git.pm 不在 perl @INC，真身在
  `/data/service/hnp/git.org/git_2.45.2/share/perl5`（随 git 发行）——
  test_package 的 PERL5LIB 自适应发现按此路径补全；设备 wget 为精简版
  不可用，配方传输走 http 镜像 + python3 urllib（Windows 侧
  python http.server，E017 镜像招）。
- `conan create . --build=missing -pr:h ohos-aarch64` 全绿（exit 0）：
  build() 替换（inventory 校验 15/15）+ package() + test_package 五组
  20/20 断言全过——① --help
  退出码 0+输出含 --help（001 等价）；② perl+Git.pm 可加载；③ 已存在
  0777 目录备份退出码 0 + world readable 告警 + 提交落库（031 等价）；
  ④ 全新目录建库 + 两次连续备份增量 1→2 revisions（030 等价）；
  ⑤ 包内测试树 8 用例全过（010/020/040/050/060/061/070/071，
  App::Prove 等价 prove；040 验证 1 行 SIGPIPE 补丁，见第 5 条）。
- 真机踩坑与修复（全部已回填配方）：
  1. **env 解释器被禁**：`#!/usr/bin/env perl` 真机报 "bad interpreter:
     Permission denied"（OHOS 禁 env）→ shebang 重写改为 conan perl 依赖
     包绝对路径（<128B），且 mock-slapcat 一并重写（071 经 sh exec 它）。
  2. **git 安全目录检查误报**：/storage FUSE 挂载下仓库所有权报告不一致，
     rev-parse/commit 全被拦（fatal: detected dubious ownership in
     repository）→ 测试脚本加 safe.directory '*'（HOME 已沙箱化，仅本次
     测试生效）。
  3. **FUSE 钳制目录 mode**：mkdir -m 0777 实际落盘 2751、mkdir 0700
     实际落盘 0771（存储守护进程钳制 mode），world writable 告警
     （mode & 02）不触发、030 的 mode==0700 断言失败（上游 031 的
     mode==0777 断言在 OHOS 同样无法复现）→ 031 等价覆盖改为 world
     readable 告警 + 提交落库；030 等价覆盖为目录+.git 创建 + 1→2
     revisions（mode 断言以技术原因如实记录）。
  4. **conan perl 包自带 prove 脚本 shebang 坏**（//bin/perl: bad
     interpreter，CI Linux 同样会挂）→ 用核心模块 App::Prove 等价执行
     （prove 本就是它的薄包装）。
  5. **Git.pm 空上下文管道竞态（SIGPIPE 打死 git rm）**：工具删除路径
     `$repo->command('rm', (keys %files_before))` 为空上下文——Git.pm
     command() 空上下文不读输出、立即关闭输出管道；git rm 首次写 stdout
     （"rm 'file'"）命中已关读端。Linux 上 perl 默认忽略 SIGPIPE（写变
     EPIPE，git 继续完成删除），上游 Debian/CI 多年无感；OHOS 上该
     perl/git 组合 SIGPIPE 为默认处置，真机实测 git 被 SIGPIPE 直接杀死
     （waitpid sig=13、stdout 空、文件仍在、索引未动），040_delete-
     entry.t 挂。修复：调用改为列表上下文（读到 EOF 即 git 退出后才关
     管道），真机复跑 040 通过。配方以 build() 补丁步骤落地（锚点计数
     校验防漂移；纯 shell 管道复刻 head -1 / >/dev/null / 1>&- 均无法
     复现——仅在 Git.pm open2 + 空上下文组合下触发）。
- 环境适配点：测试用 File::Temp 临时目录与 git 仓库全部落在可写
  TMPDIR/HOME（conan build_folder，R10）；git 提交身份经环境注入（上游
  check-local 同款）；@abs_*@ 指向包内测试树，消费者 cd 后 prove t
  原样复跑。

## 参考

- 上游仓库: https://github.com/elmar/ldap-git-backup
- Debian 源码包（1.0.8-1 同源打包线）: https://packages.debian.org/source/sid/ldap-git-backup
