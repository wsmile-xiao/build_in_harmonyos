# jimtcl 0.83 适配笔记

## 编译环境
- 构建系统: autotools（上游为 autosetup，兼容 `./configure` 调用面；仓库自带预生成 configure，无需 autoreconf）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 编译步骤

```bash
conan create archives/j/jimtcl/0.83 \
  -pr:h=$HOST_PROFILE -pr:b=$HOST_PROFILE -c tools.build:jobs=4
```

1. `source()`：下载官方 tag 归档 `https://github.com/msteveb/jimtcl/archive/refs/tags/0.83.tar.gz`
   （sha256 双面核：curl 与 urllib 独立取数一致），`strip_root=True` 解包。
2. `generate()`：`AutotoolsToolchain` 生成 CC/CXX（来自 `tools.build:compiler_executables`）
   并**追加 `CC_FOR_BUILD`**；**剔除**注入的 `--enable-static/--disable-shared/--oldincludedir/--datarootdir`。
3. `build()`：
   - `apply_conandata_patches()` 打两份 portability 补丁；
   - `./configure --prefix=/ --bindir=… --sbindir=… --libdir=… --includedir=…`（autosetup）
   - `make -j4`（`tools.build:jobs=4`）产出 `libjim.a` + `jimsh`；
   - `make -j1 check`（层1 上游 tcltest 套件，`ignore_errors=True`，真实统计见
     `reports/test-report.md` 与 `test_package/MANIFEST.yml`）。
4. `package()`：`make install DESTDIR=<package>` → `bin/{jimsh,jimdb,build-jim-ext}`、
   `lib/libjim.a`、`lib/jim/{README.extensions,tcltest.tcl}`、`lib/pkgconfig/jimtcl.pc`、
   `include/*.h`（6）、`docs/jim/Tcl.html`。
5. `test_package`：CMake 消费者 `test_jimtcl`（7 断言）+ 打包 `jimsh test.tcl`（5 断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `No working C compiler found. Tried cc and gcc.` | `autosetup/autosetup-find-tclsh` 自举 `jimsh0` 只试 `cc/gcc/c89/c99`（设备只有 clang），且忽略 `CC` 环境 | `generate()` 里 `env.define("CC_FOR_BUILD", <conf tools.build:compiler_executables.c>)` |
| 2 | `autosetup-config.guess: unable to guess system type`（伴随 `can't create .../cgXXXXXX/dummy.c: Permission denied`） | 脚本 2021-06-03 版无 `HarmonyOS` 分支；主 case 不命中后落到编译探测路径，在 HMDFS umask 077 临时目录写文件被拒 | 补丁 0001：主 case 首位注入 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`（早退，不进探测路径） |
| 3 | `Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized` | 同代 `config.sub` 的 OS 列表与 kernel-os 组合表无 `ohos` | 补丁 0002：OS case 加 `ohos*`、kernel-os case 加 `linux-ohos*` |
| 4 | `Error: Unknown option --oldincludedir`（`--enable-static` 同族 `Unknown option --static`） | Conan `AutotoolsToolchain` 注入 autotools 风格参数，autosetup 兼容表（`autosetup/system.tcl`）没有 `oldincludedir/datarootdir`；autosetup 只有 `--shared` 开关 | `generate()` 从 `tc.configure_args` 剔除上述四类前缀；`package_type="static-library"` 如实声明静态发行 |
| 5 | `package_type="library"` 报 `no 'shared' option declared`；`static_library` 报 Invalid package type | Conan 2.29 枚举为 `static-library`（连字符），且 `library` 强制要求 shared 选项 | 用 `static-library`（本包不发行共享变体，无 shared 选项） |
| 6 | `make -j1 check` 报 `No rule to make target 'check'` | conan out-of-source：`Makefile` 生成在 `build-release/`，`self.source_folder` 无 Makefile | `self.run(..., cwd=self.build_folder)` |
| 7 | `make check` 21 项失败（+1 文件级）阻断构建 | OHOS 环境类（musl 无 ualarm / 无 tty / HMDFS 禁硬链接 / `/tmp` 只读 / 无 `id` / SELinux 禁 AF_UNIX bind / libc·信号差异） | 按 `docs/TEST_QUALITY_SPEC.md` §3.3：`ignore_errors=True` + MANIFEST `upstream_test_run` 声明豁免 + `reports/test-report.md` 逐项归因；**不删改任何上游用例** |

## 源码修改

- `patches/0001-autosetup-config-guess-harmonyos.patch`（portability，1 hunk）：
  `autosetup/autosetup-config.guess` 主 case 首位注入 HarmonyOS 分支（aarch64/arm/x86_64/i?86 → `*-unknown-linux-ohos`）。
- `patches/0002-autosetup-config-sub-ohos.patch`（portability，2 hunks）：
  `autosetup/autosetup-config.sub` 接受 `ohos*` OS 与 `linux-ohos*` kernel-os 组合。
- 三关验证：NUL=0、`@@` hunk 头 ≥1（1/2）、对新解包源码真实 `patch -p1` 后与目标树逐字节 `cmp` 一致；
  功能探针：`sh autosetup/autosetup-config.guess` → `aarch64-unknown-linux-ohos`，
  `sh autosetup/autosetup-config.sub aarch64-unknown-linux-ohos` → 原样接受。
- 未修改任何测试用例、未新增/删除测试文件。

## 依赖版本

- 运行/链接依赖：`zlib/1.3.1.1`（ohpcd 远端二进制，`--build=never` 实核通过）——
  `jim-zlib` 扩展与 `jimtcl.pc` 的 `Libs.private: -lz`。
- 可选未启用：openssl（aio ssl）——设备/远端有货但 configure 探测 `openssl/ssl.h...not found`
  ⇒ 上游缺省禁用，功能面在 `reports/test-report.md` 登记（`ssl.test` NOT_RUN 5 例）。
- 内置捆绑（不额外依赖）：sqlite3 amalgamation（默认扩展集不含 sqlite，`make` 日志 0 次 sqlite 引用）、jsmn、linenoise。

## 验证结果

```bash
# 1) 预检轮（独立一次 conan create，rc=0）
grep -E "Totals:" $TASK_DIR/create-5.log
#   Totals: Total  5717   Passed  5527  Skipped   170  Failed    21
grep -E "assertions passed" $TASK_DIR/create-5.log
#   test_jimtcl: 7/7 assertions passed
#   jimsh.tcl: 5/5 assertions passed
# 2) 采信轮（清缓存干净轮）reports/conan-create.log 同值
# 3) 汇总：N=5753（PASS 5527 + FAIL 20 + SKIP 170 + NOT_RUN 36），鸿蒙特有测试 12/12
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/jimsh` | Jim shell（内嵌 initjimsh，任意 cwd 可跑） |
| `bin/jimdb`、`bin/build-jim-ext` | 上游自带调试/扩展构建脚本 |
| `lib/libjim.a` | 静态解释器库（含全部默认静态扩展） |
| `include/*.h` | `jim.h` 等 6 个头文件 |
| `lib/pkgconfig/jimtcl.pc` | pkg-config 元数据（`Libs.private: -lz`） |
| `lib/jim/tcltest.tcl`、`docs/jim/Tcl.html` | 上游测试框架与文档 |

## 注意事项

- 上游 21 项环境类失败 + 4 文件 NOT_RUN 的逐项豁免依据见 `test_package/MANIFEST.yml`
  与 `reports/test-report.md`；**不得写成 PASS**。
- `--shared` 变体上游支持（autosetup `--shared`）但本包不发行、未验证。
- `package_type=static-library` 下 Conan 注入的 autotools 参数必须剔除（问题 4），
  升级 Conan 版本后若新增注入参数需同步核对 `generate()` 的剔除清单。
