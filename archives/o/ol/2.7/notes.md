# ol (Otus Lisp) 2.7 适配笔记

## 编译环境
- 构建系统: makefile（上游 plain GNUmakefile，无 configure）
- 编译日期: 2026-09-13
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，target aarch64-unknown-linux-ohos）
- 目标平台: OHOS aarch64（Conan profile `ci/conan/profiles/ohos-aarch64`，os=OHOS/6.0, arch=armv8）
- 状态: built

## 编译步骤

上游是纯 C（C99）单文件虚拟机工程，`make release` 一次产出四个目标：

```bash
# 配方 build() 实际执行（工作目录 = conan 源码/构建树，即 self.source_folder）
make release -j1 CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr"
```

`release` = `vm ol olvm libol.so`：

| 目标 | 编译命令要点 | 产物 |
| --- | --- | --- |
| `vm` | `clang src/olvm.c extensions/ffi.c -Iincludes $(CFLAGS) -DPREFIX=\"/usr\" -lm` | `vm`（未 strip 的虚拟机） |
| `ol` | 同上 + `src/repl.S -DREPL=repl`（内嵌 REPL fasl） | `ol` |
| `olvm` | `cp vm olvm && strip olvm` | `olvm` |
| `libol.so` | 同上 + `-DOLVM_NOMAIN -shared -fPIC -Wl,-soname,libol.so`（补丁 0001） | `libol.so`（带 `DT_SONAME`） |

CFLAGS 由上游 GNUmakefile 自行拼装（`-std=gnu99`、`configure.mk` 的
`HAVE_SOCKETS/HAVE_DLOPEN/HAVE_SECCOMP/HAVE_MEMFD_CREATE` 编译探测、发布优化
`-O2 -DNDEBUG`）。**不能给 make 传 `CFLAGS=`**：GNU make 的命令行变量优先级高于
makefile 内的 `CFLAGS +=`，传进去会整段覆盖上述 flags（实测只剩调用方给的值）。

上游测试（等价于 `make check`，四组独立副本并行编排；见「验证结果」的编排参数）：

```bash
# 四组各自复制一份已构建的源码树，在副本里并行跑（各组 -j1），再按固定顺序拼接日志
FLAGS='CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr" \
       HAVE_SOCKETS=1 HAVE_DLOPEN=1 HAVE_SECCOMP=1 HAVE_MEMFD_CREATE=1'
for g in language-tests rosettacode-tests ffi-tests check-reference; do
   rm -rf "../ol-test-$g" && cp -a . "../ol-test-$g"
   ( cd "../ol-test-$g" && make -j1 $FLAGS "$g" > "upstream-$g.log" 2>&1 ) &
done; wait
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `make install` 报 `make: install: No such file or directory`（Error 127） | OHOS 未提供 coreutils 的 `install(1)`（`command -v install` 为空），而 `extras/setup.mk` 的 install 目标所有落盘动作都依赖它 | 不使用 `make install`；`package()` 用 `conan.tools.files.copy()` 按上游 install 目标的布局自行落盘（bin/、lib/libol.so、include/ol/、lib/ol/、share/man/man1/） |
| 2 | `./olvm --version` 报 `Operation not permitted`（rc=126），而 `./ol --version` 正常（rc=0） | 上游 `olvm` 目标在链接后执行 `strip`，剥离符号时一起丢掉了 hnp clang 链接器写入的 `.codesign` 节；鸿蒙内核拒绝执行无有效签名的 ELF | `package()` 对 `bin/` 下 ELF 统一 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 重新自签名；实测重签后 rc=0。**`libol.so` 不重签**（hnp clang 产物自带链接器签名，对 .so 用 selfSign 重签会让本机 musl 加载器 SIGSEGV） |
| 3 | `libraries/OpenGL` 为空目录，构建期打印 `Submodules not loaded. Run 'git submodule update --init --recursive'` | 该目录是 git submodule（`libol-opengl`），GitHub tag tarball 不含 submodule 内容 | 仅告警，不阻塞：`release`/`check` 不依赖 OpenGL 库；OHOS 侧无对应图形栈，不引入该 submodule |
| 4 | 上游 language/rosettacode 的 `tests` 目标恒返回 0 | 失败只把文件名写进 `FAILMARK`，目标最后一句是 `echo`（`FAILED!`/`passed!`），退出码不反映结果 | 配方把 `make check` 输出落盘后解析：记录 `UPSTREAM_MAKE_CHECK_RC`、统计 `| ok |` 与 `|fail` 单元格与 `# <GROUP>` 分组头；任一失败、退出码非 0 或零用例都让 `conan create` 失败（避免假绿） |
| 5 | 运行期 `ol` 找不到标准库（`OL_HOME` 默认 `<PREFIX>/lib/ol`，而 Conan 包不在 /usr） | `src/olvm.c` 用编译期 `PREFIX` 作为 `OL_HOME` 默认值（`setenv(..., 0)`，不覆盖外部已设值） | 编译期 `PREFIX` 保持上游默认 `/usr`，`package_info()` 通过 `runenv_info`/`buildenv_info` 导出 `OL_HOME=<包>/lib/ol`，包可重定位；test_package 在 `conanrun` 环境下执行 `bin/ol harness.scm` 实测标准库导入正常 |
| 6 | `make check` 在 FFI 阶段失败：`(dlsym (dlopen) "OLVM_ffi")` 取不到符号，`tests/ffi/src.inc` 生成失败并连带 C 编译报 `unterminated /* comment` | 鸿蒙 `uname -s` 返回 `HarmonyOS`（HongMeng Kernel 的 sysname，而 `uname -a` 尾部仍是 `GNU/Linux`），上游 `ifeq ($(UNAME),Linux)` 分支被跳过 → 链接命令丢掉 `-Xlinker --export-dynamic`，`OLVM_ffi` 不进动态符号表（`llvm-nm -D ol` 实测计数 0） | 用上游 `UNAME ?=` 的覆盖入口显式传 `UNAME=Linux`（OHOS 就是 Linux ABI：ELF + musl + lld），不改上游源码；加该变量后 `llvm-nm -D ol` 计数为 1，FFI 生成器恢复正常。同一分支还恢复了 `-z noexecstack` |
| 7 | `tests/rosettacode/object_serialization.scm` 失败（`|fail|fail|`，输出 `#false` / `#false` 而不是对象与 `#true`） | 该用例把序列化结果硬编码写到 `/tmp/object.bin`，而 OHOS 的 `/tmp` 是 root 属主只读挂载（`touch /tmp/x` → `Read-only file system`），`fasl-save` 直接失败、`fasl-load` 返回 `#false` | 补丁 `0002-tests-rosettacode-object_serialization.scm.patch` 把落盘路径改为构建树内相对路径 `tmp/`（用例语义与 `.ok` 期望完全不变，只是换了可写目录）；该写法在任何平台都成立，故 `platform_only: False`、无平台宏 |
| 8 | `binary-sign-tool` 在 `package()` 里报 `Error loading shared library libc++.so` + 一串 `Error relocating ... symbol not found`（本地手工执行同一命令却正常） | `conanbuild` 环境把 OHOS **目标** sysroot 的 `.../llvm/lib/aarch64-linux-ohos` 放在 `LD_LIBRARY_PATH` 最前（实测值由 profile 的 `(path)` 变量加 host 三元组后缀展开），该目录含目标机 `libc++.so`，遮蔽了 `binary-sign-tool` 需要的宿主 libc++ | 签名/objcopy 两条命令前加 `LD_LIBRARY_PATH=` 清空（宿主 libc++ 走默认搜索路径）；实测清空后 `add codesign section success` 且产物 `--version` rc=0 |
| 9 | `finish` 内嵌 W3 的 L5a 质量门禁报 `libol.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址` | 上游 `libol.so` 目标只用 `-shared -fPIC` 链接、未传 `-Wl,-soname`；OHOS 工具链不会自动补 SONAME，`llvm-readelf -dW libol.so` 实测动态段无 `SONAME` 行 | 补丁 `0001-GNUmakefile.patch` 在该链接行追加 `-Wl,-soname,libol.so`；实测 `SONAME Library soname: [libol.so]`，W3 的 L5a 转为通过 |

## 源码修改

两个补丁，均由 `refresh-patch --auto` 生成（per-file-difflib）：

- `patches/0001-GNUmakefile.patch`（+1/-1）
  `libol.so` 目标的链接行追加 `-Wl,-soname,libol.so`（见问题 9）。
- `patches/0002-tests-rosettacode-object_serialization.scm.patch`（+3/-2）
  `tests/rosettacode/object_serialization.scm`：`fasl-save`/`fasl-load` 的路径由
  硬编码 `/tmp/object.bin` 改为相对路径 `tmp/object.bin`（见问题 7）。

两个补丁都没有平台宏、没有 `#ifdef`，`platform_only: False`、`guard: none`。
除此之外不改上游任何文件；问题 1/2/4/5/6/8 都在配方层处置。

## 依赖版本

无编译依赖、无运行依赖（仅 OHOS clang 15 工具链与 libc）。

## 验证结果

采信轮（提交 SHA 上的干净构建，清缓存后执行）：

```bash
# 配方 build() 内实际执行（工作目录 = conan 源码/构建树）
make release -j1 CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr"
make check（四组并行编排）CC="/data/service/hnp/bin/clang" UNAME=Linux PREFIX="/usr" > upstream-check.log 2>&1

# 配方验证（含 G0-G4 / L2 / L4 / L5）
python3 scripts/ohc-run.py conan-verify ol 2.7 --project-dir .
```

- 构建：`release` 四个目标（`vm`/`ol`/`olvm`/`libol.so`）全部成功，`Apply patch` 2 次（`0001-GNUmakefile` 的 SONAME 与 `0002-...object_serialization` 的 `/tmp` 路径）。
- 编排参数：上游 `make check` 的四个分组（language / rosettacode / ffi / doc-reference）
  各自在**独立的源码树副本**里并行执行（各组自身仍 `-j1`），日志按固定顺序拼接成
  `upstream-check.log`。用独立副本是为了消除四个并发 make 实例对共享中间产物
  （`tmp/`、`ol`/`olvm`、`tests/ffi/src.inc`）的竞态——CI #46152 上 ffi 组曾因共享树以 rc=2 失败。
  另外在命令行预置 `HAVE_SOCKETS/HAVE_DLOPEN/HAVE_SECCOMP/HAVE_MEMFD_CREATE=1`
  （`configure.mk` 用 `?=`，预置后每次子 make 省掉 5 次 clang 特性探测）。
  用例集合与串行 `make check` 完全相同（不抽样、不减变体），墙钟由 ~25-30 分钟压到 ~10 分钟，
  以满足 CI 的 `conan create` 3600s 上限。
- 上游测试：清点 **211** 个用例，实际运行 **210/210（100%）**——LANGUAGE 62（执行 61）、
  ROSETTACODE 112、FFI-Tier-1 7、FFI-Tier-2 9、CHECK REFERENCE 21，全部 `| ok | ok |`，
  无 `FAILED!`/`|fail`，末行 `UPSTREAM_MAKE_CHECK_RC=0`。其中 `tests/fasl-binary.bin`
  属**上游默认不执行**（`extras/check.mk` 的 `%.bin.ok` 规则被整段注释，`tmp/check.log`
  无其执行记录，日志只有名字行没有结果行），既非 PASS 也非本包 SKIP，单列申报不冒充通过。
  逐字日志见 `reports/upstream-check-log.md`。
- 消费者验证：**3/3（100%）**——`test_package` 的 `embed_test`（C 消费者，5 断言）、
  `harness.scm`（`bin/ol` 7 断言）、`olvm --version`；`conan create` 内实跑，
  见 `reports/conan-create-log.md`。
- CI 本地模拟（W3）：L0/L1/L2/L4 通过；L5a 起初报 `libol.so 缺少 DT_SONAME`，加 `-Wl,-soname,libol.so` 后该门禁转为通过（`llvm-readelf -dW` 见 `SONAME Library soname: [libol.so]`）。
- `conan-verify` 的 G2 PASS；G4/L2/L4/L5 因工具在 `--user/--channel` 形态下解析
  package_id 失败而报「跳过（无 cache 路径）」，已按产物清单/实跑/`llvm-readelf`/
  两轮 sha256 逐项人工补测，见 `reports/conan-verify-supplement.md`。
- 两轮独立构建（不同缓存目录）产物逐字节一致：包内容聚合
  `19358458ce1fdd468f84194715d4c4fe21f413eead873ff7434e00cc54afd09e`（280 文件）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/ol` | 解释器（内嵌 REPL fasl，已重新自签名） |
| `bin/olvm` | 独立虚拟机（strip 后重新自签名） |
| `lib/libol.so` | 可嵌入的 VM 共享库（保持 hnp clang 链接器签名） |
| `include/ol/ol.h`、`include/ol/vm.h` | 嵌入 API 头（`vm.h` 构建期由 `src/olvm.c` 生成） |
| `lib/ol/**` | Ol 标准库（`libraries/**.scm\|*.lisp`）与 `repl` fasl |
| `share/man/man1/ol.1.gz` | 手册页（`mtime=0` 压缩，可复现） |

## 注意事项

- 语言预检 `lang-preflight` 判定 `detected=c`：任务卡标注 C++，但本工程主体是纯 C
  （C99，`src/olvm.c` + `extensions/ffi.c`），C 与 C++ 属兼容族，按 C 口径构建。
- `bin/ol` 未 strip（保留符号，便于诊断）；`bin/olvm` strip 后必须重新签名，见问题 2。
- 若下游在同一进程内嵌入 `libol.so`，请通过 `conanrun`/`conanbuild` 环境拿到
  `OL_HOME`，或自行把 `lib/ol` 装到 `<PREFIX>/lib/ol`。
