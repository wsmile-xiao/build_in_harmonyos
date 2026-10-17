# bool 0.2.2 适配阶段记录

## 基本信息

- 任务号：7241
- 主理 agent：Codex-1
- 上游：`https://ftp.gnu.org/gnu/bool/bool-0.2.2.tar.xz`
- 初始分支：`feat/bool-0.2.2`
- W0 起始 HEAD：`9b49d7903dabc928913f2008b547a681b1e072de`
- 任务声明语言：C
- 构建系统：Autotools（根目录 `configure.ac` + `Makefile.am`）
- 源码 SHA256：`dc75d36344c93c49eac3196f7543ed67f3bde9e0bdebdb5677099455f3ab2dbb`

## W0/W0b 与预检

- W0：`ci/scripts/preflight_check.sh bool/0.2.2` 通过；配方尚未生成，无依赖声明。
- W0b：同软件无历史归档/notes；从当前上游源码重新探索。
- `prescan --no-writeback`：命中 E007/E072 族的旧 config.guess/config.sub、HMDFS 临时目录权限、NLS/glibc 兼容提示；无外部依赖。
- `lang-preflight` 首次因 `contrib/symtab-0.1.1/Makefile.PL` 把辅助 Perl 文件纳入统计而报 mixed。人工核验根目录 `SUBDIRS = doc lib src tests`，`src/Makefile.am` 构建 13 个 C 源文件，故按既有辅助脚本误报经验覆盖为 partial，继续 C 适配。

## 上游测试账本（初始静态统计）

- `tests/Makefile.am` 注册 18 个 shell 测试目标：`boolean.sh`、`context.sh`、`empty.sh`、`html.sh`、`line.sh`、`opt_b.sh`、`opt_c.sh`、`opt_d.sh`、`opt_f.sh`、`opt_h.sh`、`opt_i.sh`、`opt_l.sh`、`opt_n.sh`、`opt_p.sh`、`opt_q.sh`、`opt_s.sh`、`single.sh`、`status.sh`。
- 上游静态注册数 `N_static=18`；最终实际执行 `N_executed=18`，通过 18，失败 0，跳过 0。
- 新增消费者测试 `N_consumer=1`：`test_package/test_bool.sh` 真实调用安装后的 `bool` CLI 并断言行为。

## 已定位适配点

- 设备 `uname -m=aarch64`、`uname -s=HarmonyOS`；上游 2013 年 `config.guess` 原始脚本无法识别。
- 上游 `config.sub` 原始脚本拒绝 `aarch64-unknown-linux-ohos`。
- 项目补丁脚本成功加入 HarmonyOS 分支但未能处理旧 `config.sub`；探索副本已补齐 `linux-ohos` 合法性并将 `config.guess` 临时目录 `umask 077` 调为 `022`，HarmonyOS 分支立即输出并退出。
- 当前探索验证：`config.guess -> aarch64-unknown-linux-ohos`，`config.sub aarch64-unknown-linux-ohos -> aarch64-unknown-linux-ohos`。
- 设备无裸 `install` 命令，但 Autotools 探测到可用 `ginstall`；交付 `package()` 按上游安装规则手动复制 CLI、man page 和许可证，避免依赖环境安装工具。

## 发现与知识

- ✅ E007/E072：补丁后的旧 `config.guess/config.sub` 在设备上输出并接受 `aarch64-unknown-linux-ohos`；不使用伪造 build/host 参数。
- ✅ E011：生成的 `config.status` 使用 `umask 077` 时在 HMDFS 创建 `subs1.awk` 失败；配方在 `build()` 中用 `replace_in_file` 将生成脚本调整为 `022`。
- ✅ 可复用 aarch64 兼容性模式：`ALIGN` 将指针显式转换为 32 位 `unsigned` 会截断地址并造成运行时 SIGSEGV；用 `uintptr_t` 做对齐运算后上游 18/18 测试恢复通过。
- ✅ 语言预检误报：`contrib/symtab-0.1.1/Makefile.PL` 属未参与根构建的辅助 Perl 目录；根 `SUBDIRS` 与 `src/Makefile.am` 的 C 目标是权威证据。
- ✅ 产物验证：release tarball 解包后 `bin/bool --version` 和消费者脚本通过，产物为 arm64 PIE ELF。

## 当前状态

- 设备负载窗口恢复后完成 configure、`make -j1`、`make -j1 check` 和 `make install DESTDIR`。
- 首次 `make check`：18 个目标中 3 通过、15 失败、0 跳过；失败均表现为 `SIGSEGV`，根因是 `src/mem.h` 中 32 位 `unsigned` 截断指针。
- 修复 `ALIGN` 为 `uintptr_t` 运算后：`make -j1` 通过（仅保留 8 个旧式指针/格式警告），`make -j1 check` 为 18/18 通过、0 失败、0 跳过，安装为 0。
- 安装树包含 `bin/bool` 和 `share/man/man1/bool.1`；`bool --version` 输出 `bool (GNU) 0.2.2`。
- 消费者测试 `test_bool.sh` 使用安装后的绝对二进制，覆盖版本、布尔匹配/不匹配、固定字符串和缺失文件状态；修正一次输出格式断言后最终通过，`N_consumer=1`。
- 路径 B 结论：走路径 B。`ALIGN` 指针截断是跨旧 C 仓库可复用的 aarch64 崩溃模式；已查重 E213（隐式 int 返回值截断）/E420（缺失直接声明）等相关条目，均未覆盖显式窄整数对齐转换。将提交同 stem `.kv/.md` 知识草稿、知识库扩展 Issue，并在 PR 正文互链；E007/E011/E072 作为已有知识引用。
- 没有把设备公共 `ohpcd-ai-worker-result.json` 当成本任务结果，结果统一写入任务专属目录。

## 对话记录

- 2026-09-11：Codex-1 按 W0/W0b、语言预检、源码探索、Conan G2、W3、W4 前置要求推进；设备负载高峰期间未干扰其他窗口，所有构建与测试证据均来自任务专属设备环境。
---

**编译结束**: 2026-09-11 12:21
**最终状态**: built
