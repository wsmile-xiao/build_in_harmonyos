# splint 3.1.2 适配笔记

## 编译环境
- 构建系统: autotools（手写 configure + GNU make；无 cmake/meson）
- 编译日期: 2026-09-26
- 编译器: clang 15（OHOS aarch64 profile，设备原生编译）
- 目标平台: HarmonyOS PC — OHOS / aarch64 / build_type=Release
- 状态: published

## 编译步骤

1. W1 同步主仓库 `git checkout main && git pull origin main`。
2. W0 依赖发布检查：`preflight_check.sh splint/3.1.2` 通过；`conan download` 实证
   制品仓已有本配方可能用到的 `bison/3.8.2`（os=OHOS）与 `flex/2.6.4`（os=OHOS）。
   splint 无第三方运行时依赖（仅 libc/system）。
3. W0b 历史经验核验：`archives/s/splint/` 不存在，无历史归档 → 无历史结论需迁移。
4. R47 语言预检（源码 checkout 后、编译前）：`lang-preflight` → task=cpp /
   detected=c，同族兼容，通过。
5. 模式 B 探索性编译（`init-build` → `source .build-context-splint-3.1.2`）：
   `./configure --build=aarch64-unknown-linux-gnu --prefix=<prefix> && make -j1 &&
   make install DESTDIR=<test-prefix>`，随后 `make check` 跑上游完整测试套件。
   逐条问题见下表，最终以 5 个补丁固化。
6. 补丁生成：`refresh-patch --auto`（编辑追踪器 hash 比对，剔除 bison 构建产物后
   仅保留 5 处真实源码改动），每个补丁独立 `patch --dry-run -p1` 验证可复现。
7. 端到端补丁验证：全新目录解压 tarball → 应用 5 补丁 → `./configure`（确认
   `LEXLIB` 为空、`BISON`/`LEX` 正常）→ `make` → 上游测试，全部在补丁版上复现。
8. `conan create` 干净构建（CI profile，`--build=missing`）：G2 通过，build() 内
   上游测试 131/133，test_package 5/5。

## 上游测试三步法（R51）

### 1. 清点
- 上游测试目录：`test/`（406 个文件：183 个 `*.c`、3 个 `*.splintrc`、142 个
  `*.expect`，其余为 Makefile/辅助脚本）。
- 测试注册：`test/Makefile.in` 中 `SPLINTTESTS = $(UNITTESTS) $(SUBDIRTESTS)`
  = 114 + 19 = **133** 个检查；`make check` 别名到 `fulltest`。
  上游无 ctest / pytest / meson 注册。
- 运行方式：每个检查运行 `src/splint`，再把输出与 `test/<name>.expect` 逐字比对
  （`CLEANOUTPUT` 过滤器剔除 Splint 版本行与 make 噪声）。无独立测试框架、
  无断言库，比对即断言。

### 2. 实跑（本机设备，补丁版）
```
$ TMPDIR=<writable> make check        # 在 test/ 目录内执行
...
Checking rc...                                  *** FAIL ***
Checking utypes...                              *** FAIL ***
====================================
133 checks run, 131 passed, 2 failed
```
（脚本化统计：`grep -c "Checking"` = 133，`*** FAIL ***` = rc、utypes 两行。）

### 3. 如实回填与失败根因
两个失败均**不是**源码缺陷，且都不是「没有环境」这类空话——各自有可核对的具体技术原因：

| 检查 | 实证症状（test/<name>.out 原文） | 根因 |
|------|----------------------------------|------|
| `rc` | `Temporary file for pre-processor output already exists.  Trying to open: /tmp/cl5AAA.c.` → `*** Cannot continue.` | 上游夹具 `test/rc3.splintrc` 第 6 行硬编码 `-tmpdir /tmp`（测试自带固定路径，与本次补丁无关）；OHOS 上 `/tmp` 为只读 erofs 挂载（知识条目 E002），`src/fileTable.c:fileTable_createFile` 的 `open(O_EXCL)` 必然失败。显式传 `TMPDIR` 时该用例行为与退出码符合预期。 |
| `utypes` | `Cannot find include file sys/types.h on search path: /usr/include;...` → `*** Cannot continue.` | 该检查要求 splint 默认系统搜索路径下存在 `<sys/types.h>`；OHOS 镜像无 `/usr/include`（实测 `os.path.isdir('/usr/include') == False`）。 |

配方据此只为这两个检查设**证据化容忍**：`build()` 仅在失败检查的输出文件中出现
上表登记的实证症状字符串时才放行，任何其他失败（或同名字检查因其他原因失败）都会
让构建失败；上游测试文件与断言一律未改动、未跳过。

`rc`/`utypes` 之外的 131 个检查在干净 `conan create` 环境中全部通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 报 `cannot create a temporary directory in .` / 目录不可写 | HMDFS 上 `umask 077` 建目录被拒（setgid 目录 02700 + UID 映射，知识条目 E011） | `0001-configure.patch`：`configure` 中 confstat 临时目录的两处创建分支（mktemp -d 与 mkdir 回退）`umask 077` → `umask 022` |
| 2 | `config.guess` "unable to guess system type" | 上游 config.guess 为 2008 年版本，不认识 HarmonyOS | 配方 `tc.configure_args` 显式补 `--build=aarch64-unknown-linux-gnu`（bundled config.sub 接受该三元组） |
| 3 | 并行 make 失败（jobserver） | HMDFS 不支持 mkfifo，GNU make jobserver FIFO 建不出来 | build()/install()/测试统一 `-j1` 串行 |
| 4 | `signature.tab.h` 找不到 | bison ≥ 3 生成的头文件名与 Makefile 期望的 `signature_gen.h` 不一致 | `0002-src-Makefile.in.patch`：两处 BISON 规则改为把生成结果经 `sed 's/signature\.tab\.h/signature_gen.h/g'` 输出（回移上游官方补丁） |
| 5 | 链接报 `undefined reference to yywrap` | OHOS 侧 flex 的 `LEXLIB` 探测结果为空，`yywrap` 由 libfl 提供的假设不成立 | `0004-src-globals.c.patch`：去掉 `yywrap` 外层的 `# ifdef WIN32`，无条件定义（`nm` 实证 `globals.o` 提供 `T yywrap`）。因此本配方**不**依赖 flex/libfl |
| 6 | `__pid_t` 未定义 | OHOS libc 不提供 `__pid_t` | `0005-src-osd.c.patch`：局部变量改为 `int`（该函数返回类型本就是 `int`） |
| 7 | 运行 splint 报 `Cannot continue`（临时文件不可写） | 编译期默认临时目录为 `/tmp/`，OHOS 上只读（E002） | `0003-src-context.c.patch`：POSIX 分支下 FLG_TMPDIR 改读 `TMPDIR` 环境变量（`osd_getEnvironment`），回退到编译期默认值 |
| 8 | `conan create` 中 133 个检查**全部**失败，输出里夹带 `shell-init: error retrieving current directory: getcwd` | 在 build 目录下执行 `make -C test`，HMDFS 上每个 recipe shell 启动即 getcwd 失败，而测试套件会捕获 stderr 参与逐字比对 | 改为进入 `test/` 目录后执行 `make check`（上游 `src/Makefile.in` 的 `cd ../test; ${MAKE}` 同款做法） |
| 9 | test_package 无法直接执行二进制 | OHOS 默认 shell（mksh）不能执行 ELF | 参照 2048.c 先例：`bash test.sh <path-to-splint>` 包装 |

## 源码修改（patches/，均为 `refresh-patch --auto` 生成，`patch --dry-run -p1` 可复现）

| 补丁 | 文件 | 修改内容 | 理由 |
|------|------|----------|------|
| `0001-configure.patch` | `configure` | 两处 confstat 临时目录创建分支 `umask 077` → `umask 022` | HMDFS setgid + UID 映射（E011）；平台宏，PR 正文说明理由 |
| `0002-src-Makefile.in.patch` | `src/Makefile.in` | `signature.c.der:` 与 `Headers/signature_gen.h signature.c:` 两条 BISON 规则：生成后经 `sed` 把 `signature.tab.h` 改写为 `signature_gen.h` | bison ≥ 3 的头文件命名变化；上游官方补丁回移 |
| `0003-src-context.c.patch` | `src/context.c` | FLG_TMPDIR 的 POSIX 分支：`cstring_makeLiteral(DEFAULT_TMPDIR)` → `cstring_copy(osd_getEnvironment("TMPDIR", DEFAULT_TMPDIR))` | `/tmp` 只读（E002），让 `TMPDIR` 可覆盖 |
| `0004-src-globals.c.patch` | `src/globals.c` | 删除 `yywrap` 外层的 `# ifdef WIN32` / `# endif`，改为无条件定义 | 消除对 libfl 的隐式依赖，`@LEXLIB@` 为空也能链接 |
| `0005-src-osd.c.patch` | `src/osd.c` | `__pid_t pid = getpid ();` → `int pid = (int) getpid ();` | OHOS libc 无 `__pid_t` |

未使用 `sed` 直接改生成文件；补丁均由追踪器差异生成后逐条人工复核。

## 依赖版本

无第三方运行时依赖（仅 libc / libm，系统自带）。
构建期不使用 bison/flex 作为 conan 依赖：tarball 自带预生成的
`src/signature.c`、`src/cscanner.c`、`src/Headers/signature_gen.h`，
`yywrap` 由 `0004` 补丁无条件提供，故配方不引入 `tool_requires`。
（若上游源码变更导致必须重新生成 parser，制品仓已有 `bison/3.8.2`、`flex/2.6.4`
可作为 `tool_requires` 使用——已 `conan download` 实证可取。）

## 验证结果

```bash
# 上游测试套件（build() 内实跑，conan create 干净环境）
$ TMPDIR=<writable> make check      # 在 test/ 目录执行
133 checks run, 131 passed, 2 failed
splint/3.1.2: upstream test suite: 131/133 checks passed (2 environment-dependent failures: rc, utypes)

# 失败两项均为环境性，症状已实证：
$ cat test/rc.out | tail -3
Temporary file for pre-processor output already exists.  Trying to open: /tmp/cl5AAA.c.
*** Cannot continue.
$ cat test/utypes.out | tail -2
Cannot find include file sys/types.h on search path: /usr/include;...
*** Cannot continue.

# test_package 消费者验证（conan create 自动执行）
$ TMPDIR=<writable> bash test.sh <pkg>/bin/splint
PASS 1: -help exits 0 and reports 'Splint 3.1.2'
PASS 2: LARCH_PATH=<pkg>/share/splint/lib contains standard.lcd
PASS 3: clean.c analysed with no warnings (exit 0)
PASS 4: warn.c reports both expected diagnostics (exit 1)
PASS 5: withinclude.c pre-processed through TMPDIR and analysed (exit 0)
test splint 3.1.2: 5/5 checks PASS

# 包内容
$ ls <pkg>/bin/splint <pkg>/share/splint/lib/standard.lcd
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 应用型配方（build() 内跑上游 make check + 证据化容忍） |
| conandata.yml | 官方 URL（splint.org）+ SHA-256 |
| patches/ | 5 个补丁（见上表） |
| test_package/ | `conanfile.py` + `test.sh` + `clean.c` / `warn.c` / `withinclude.c` / `local.h` + `MANIFEST.yml` |
| commands.json | CLI 工具声明（R38，软件级，`type=tool`） |
| notes.md | 本文件 |
| reports/ | pr-body.md、audit-result.json、conan-create.log 等 |

## 注意事项

- splint 依赖 `LARCH_PATH` 定位 `.lcd` 模型库（安装前缀与运行前缀不一致时会失效）。
  配方通过 `runenv_info.define_path("LARCH_PATH", <pkg>/share/splint/lib)` 发布，
  消费者用 VirtualRunEnv 即可直接运行。
- splint 的临时目录必须可写；OHOS 上 `/tmp` 只读，消费侧应设 `TMPDIR`
  （`0003` 补丁使该变量生效）。
- 上游 `test/rc3.splintrc` 硬编码 `-tmpdir /tmp`，与本适配无关；不要为了让
  `rc` 变绿去改上游夹具。
- 上游测试必须在 `test/` 目录内执行，不要用 `make -C test`（见问题 #8）。

---

### 对话 #1

- 2026-09-26：完成 splint 3.1.2 在 HarmonyOS PC（OHOS / aarch64 / 设备原生）的适配。
  产出 5 个补丁、autotools Conan 配方、test_package（5 项断言，5/5 通过）；
  `conan create` 干净构建通过，上游测试 133 项执行、131 项通过（`rc`/`utypes` 为环境性失败，见问题 #6/#7）。
  后续修复：manifest `configure_options` 补 `--build=` triplet（问题 #2 的 G0 侧复现），并补齐 packaging 产物。

---
**编译结束**: 2026-09-26
**最终状态**: published
---

**编译结束**: 2026-09-27 00:36
**最终状态**: published
