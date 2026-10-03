# st 0.9.1 适配笔记

## 编译环境

- 构建系统: **makefile**（纯 Makefile，**无 `configure`**）
- 编译日期: 2026-09-29（配方首稿）／2026-09-30（验证闭环）
- 编译器: clang（profile `tools.build:compiler_executables["c"]`；OHOS aarch64 工具链）
- Conan: 2.29.1 ｜ 设备: HarmonyOS PC aarch64 真机 ｜ musl: `/lib/ld-musl-aarch64.so.1`
- CONAN_HOME: 任务私有 `~/tmp/ch/home-sw5-st`
- 状态: built

## 编译步骤

1. `source()`：`get()` 官方包 `https://dl.suckless.org/st/st-0.9.1.tar.gz`
   （sha256 `16f43b9433ade9d70d6085c31f9fd99f2835eaade31221020f22143035dfc0d2`，48412 B 实测），`strip_root=True`。
2. `generate()`：`PkgConfigDeps` 生成 `x11.pc / fontconfig.pc / freetype2.pc / xft.pc` →
   `buildenv_info.append_path("PKG_CONFIG_PATH", generators_folder)`（**必须在 VirtualBuildEnv 之前**）→ `VirtualBuildEnv`。
3. `build()`：在 Python 侧纯解析 PkgConfigDeps 生成的 `.pc`（`_pc_query`，等价 pkg-config
   `--cflags`/`--libs` 非 static 口径）得到 `INCS`、`LIBS`，再
   `self.run('make CC=<cc> INCS="…" LIBS="…"', env="conanbuild", cwd=self.source_folder)`
   （2026-10-01 CI 返修起不再 exec `pkg-config` 二进制，原因见问题表 9）。
4. `package()`：把产物 `st` 拷到 `<package_folder>/bin/`。
5. `test_package`：`self.run('ST_BINDIR=… python3 test_st.py', env="conanrun")` 真实执行打包产物。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ModuleNotFoundError: No module named 'conan.tools.pkg_config'`（r1） | 该模块在 `conan.tools.gnu` 下 | 改 import |
| 2 | `Version conflict: freetype/2.14.3 vs 2.14.3.1 … Conflict originates from fontconfig/2.18.3`（r2） | 传递依赖要 `2.14.3` | 锁到 `freetype/2.14.3` |
| 3 | `No package 'x11'/'freetype2' found` + `make: *** No targets specified`（r3） | `.pc` 目录不在 `PKG_CONFIG_PATH`；cwd 不对 | 显式 `append_path` + `cwd=self.source_folder` |
| 4 | `x.c:11:10: fatal error: 'X11/Xatom.h' file not found`（r4–r6，三轮） | **同一 shell 命令里 `PKG_CONFIG_PATH=x make INCS="\`pkg-config …\`"` 的反引号在待定赋值生效前就被展开（POSIX）** ⇒ `INCS` 为空 | 改成在 Python 侧设好 env 再 `subprocess` 调 pkg-config |
| 5 | `Error loading shared library libXft.so.2/libfontconfig.so.1`（r7 起，前任停靠点） | **已发布依赖包 `libxft/2.3.9` / `fontconfig/2.18.3` 的 `.codesign` 签名不被本设备 ldso 接受（设备绑定签名）** | 任务私有 `CONAN_HOME` 内按 `E517`+`E077` 重签两枚 `.so`（见对话 #2） |
| 6 | 构建脚本报 `Error 127`（找不到 `c99`） | `Makefile` 带 `.POSIX` ⇒ make 默认 `CC=c99`，本机无 `c99`/`cc` | 配方显式给 `CC`（取 profile conf，缺省 `clang`） |
| 7 | `config.mk` 的 `X11INC/X11LIB=/usr/X11R6/*` 找不到 | 本机无 `/usr/X11R6`，路径被上游烧死 | 只覆盖 `CC`/`INCS`/`LIBS` 三个 make 变量，路径全交 pkg-config |
| 8 | `conan-init` 生成的是 autotools 模板 | `st` 无 `configure` | 改成显式 `make`；`package_type` `library` → `application` 并去掉 `shared` 选项 |
| 9 | CI 首错 `FileNotFoundError: [Errno 2] … 'pkg-config'`（PR #14017 build #65601；本地全绿、CI 红） | `subprocess` 直调二进制走的是 conan 客户端进程的 PATH，CI worker 的 PATH 没有 `pkg-config`（本机交互 shell 有 ⇒ 只在 CI 暴露）；profile `[buildenv]` 只进 conanbuild.sh，救不了 `os.environ` | `build()` 改纯 Python 解析 `.pc`（`_pc_query`：被依赖者在后拓扑序 + `-L` 前置 + 同名去重）；对拍真实 pkg-config：`--cflags` 12/12、`--libs` 19/19 token 集合一致 |

## 源码修改

无 —— **本包 0 个补丁**（`patches_applied: []`、`conandata.yml` 的 `patches: {}`）。
所有适配都落在配方侧的编译变量覆盖上，未改一个上游字节。

## 依赖版本

| Conan 包 | 版本 | 说明 |
|---|---|---|
| freetype | 2.14.3 | 与 fontconfig 传递要求对齐（2.14.3.1 会冲突） |
| fontconfig | 2.18.3 | 运行期 + pkg-config |
| libx11 | 1.8.13 | 运行期 + pkg-config |
| libxft | 2.3.9 | 运行期 + pkg-config |

W0 `preflight_check.sh st/0.9.1` 实测：**四依赖全部 released**、`st/0.9.1` 版本号未占用，`PREFLIGHT_RC=0`。

## 验证结果

```bash
# ① 配方验证（真绿）
$ ohc-run.py conan-verify st 0.9.1
✅ 配方验证通过: st 0.9.1        VERIFY_RC=0
G0/G1/G2/G3/G4/L2/L4/L5 全 PASS
报告: archives/s/st/0.9.1/reports/conan-verify-report.md  Verdict: PASS

# ② 消费者测试（conan-create.log 实读）
======== Testing the package: Executing test ========
RUN: ST_BINDIR="…/p/b/st3fe8e569d4c54/p/bin" python3 "…/test_package/test_st.py"
[st -v] rc=1 out='…/p/bin/st 0.9.1'
[st -h] rc=1 out='usage: …/p/bin/st [-aiv] [-c class] [-f font] …'
PASS: st 0.9.1 消费者测试通过（真实执行二进制 + 版本串 + usage）

# ③ 本地 CI 模拟（W3，阻塞门禁）
ci/conan/setup.sh 通过 · build_and_test.sh st/0.9.1 通过
日志: archives/s/st/0.9.1/reports/w3-local-ci.log

# ④ PR 原子性（W2）
仅含配方变更 9 文件，无框架文件

# ⑤ 装载修复后复验（两枚依赖 .so 重签后）
$ LD_LIBRARY_PATH=<conan 9 目录> st -v
st 0.9.1
ErrorLoadingCount=0  ErrorRelocCount=0
```

**`st -v`/`st -h` 退出码 = 1 是上游 `x.c` 的 `die()` 设计**（打印后 `exit(1)`），
所有断言都落在**输出**上，不把非 0 退出码当失败（`test_st.py` 注释已载明）。

## 注意事项

- 上游**无测试套件**（R51 清点：源码 15 文件、无 `tests/`/`test/`、`Makefile` 无 `check` 目标）
  ⇒ `test_package/MANIFEST.yml` 写 `upstream_tests: []` + 清点证据，消费者侧 4 断言覆盖。
- 运行期依赖 `libxft/2.3.9` / `fontconfig/2.18.3` 的 `.codesign` 在**本设备**不被 ldso 接受；
  修复只作用于本任务私有 `CONAN_HOME`，**配方 9 文件未因它改动**（风险披露已上报主理，供 W4 审计引用）。
- 本机没有 `ldd`；显式 exec `/lib/ld-musl-aarch64.so.1 --list` 会被系统策略拒（Permission denied）
  ⇒ 判断装载问题一律以**真跑目标二进制**的 stderr 为准，`ctypes.dlopen` 的读数不可作判据
  （它会把 SONAME 印成自己的路径，造出一片假 FAIL）。

---

## 对话记录

### 对话 #1 [2026-09-29] 配方首稿与七轮构建调通（收尾-5）

- **症状**: `ohc-run.py build` 不接 `--url`（首轮卡 Step1）；随后 r1–r6 六轮编译期报错。
- **根因**: ①`build` 需先 `init-build st 0.9.1 --url=…`（登记表 URL，实测 206；⚠ 别用
  `dl.suckless.org/misc/…`，404）；②r1 import 路径错；③r2 传递依赖版本冲突；
  ④r3 `.pc` 不可见 + `cwd` 不对；⑤r4–r6 是 **POSIX 反引号展开顺序**导致 `INCS` 为空。
- **最小复现**: `PKG_CONFIG_PATH=<dir> make INCS="\`pkg-config --cflags x11\`"` ⇒ `INCS` 为空、
  紧接着 `x.c:11: 'X11/Xatom.h' file not found`。
- **已试失败方案**: ①`conan-init` 的 autotools 模板直接用（`st` 无 `configure`）；
  ②`package_type=library` + `shared` 选项（Conan 2.29.1 拒载）；③shell 内联反引号取 `INCS`（三轮同错）。
- **最终方案**: Python 侧设 `PKG_CONFIG_PATH` 再 `subprocess` 调 pkg-config；显式 `CC`/`INCS`/`LIBS`
  覆盖；`package_type="application"`。**r7 起 `conan create` 建成包**
  （`Already installed! (10 of 10)`、`st3fe8e569d4c54/p/bin/st` 在位、用 profile 的 clang 编译，
  `CC=c99` 之谜已解），**只剩 `test_package` 运行期装载失败 ⇒ 按用户 09-29 令就地停靠**，首稿入库
  （`a745c0397a`，8 文件、无 `reports/`）。

### 对话 #2 [2026-09-30] 定因 test_package 装载失败 + 修复 + W3 闭环（主理-1）

- **症状**: `[st -v] rc=127 out='Error loading shared library libXft.so.2: (needed by …/p/bin/st)'`，
  随后 `libfontconfig.so.1` 同错 + 一串 `Error relocating … symbol not found` ⇒ `VERIFY_RC=2`。
- **根因（内容级）**: **已发布 conan 包 `libxft/2.3.9` 与 `fontconfig/2.18.3` 的 `.so` 所带
  `.codesign` 签名不被本设备 `ld-musl` 接受**（设备绑定签名）——与路径、权限、目录、
  `LD_LIBRARY_PATH`、`DT_NEEDED`、ELF 结构全无关。出处：知识图谱 **E517**
  （`remove-then-resign-in-task-local-view`）+ **E077**（四步顺序）+ **E135**；
  草稿 `DRAFT-PKG-VER-remote-prebuilt-so-codesign-is-device-bound` 的 dmenu 5.4 #12032
  四臂判决点名的正是这两枚 package_id。
- **最小复现（三臂 A0/A1/A2，`env -i` 干净环境 + `LD_LIBRARY_PATH` 逐组对照）**:
  - **A0 原件** ⇒ `ErrorLoadingCount=2`（只 `libXft.so.2` + `libfontconfig.so.1`，
    libXrender/libX11/libxcb/libXdmcp/libXau/libxml2/libfreetype 七项全部装载成功）
  - **A1 仅 `llvm-objcopy --remove-section=.codesign`** ⇒ **仍 2**（剥段不够）
  - **A2 剥段 + `binary-sign-tool sign -selfSign 1` 重签** ⇒ **`ErrorLoadingCount=0`** ✅
  - 佐证：把**能装载的 libX11 字节冒充 `libXft.so.2`** ⇒ 0；真实件换到全新 755 目录 ⇒ 仍 2；
    换另一 conan home 的 `libxft/2.3.8` ⇒ 仍 2 ⇒ 跟内容走、跟名字/路径无关。
- **已试失败方案（均被读数排除）**: ①"环境没传" —— `conanrunenv-release-armv8.sh` 实读
  9 个依赖 lib 目录**全在**；②"上游缺件" —— 9 项 `DT_NEEDED` 对应 `.so` 在 `p/*/lib` **全在**；
  ③权限/挂载/xattr —— 与通过件 `libX11.so.6.4.0` 完全同型（`mode 770`、`security.selinux=u:object_r:hmdfs:s0`、
  `user.hmdfs.perm=0xd4`、`security.isolate=3`）；④ELF 结构 —— header/phdr/LOAD 对齐/`SONAME`/
  `BIND_NOW`/`GNU_STACK`/`GNU_RELRO` 与通过件同型；⑤逐段 bisect（section header 表、`PT_NOTE` 段与字节、
  `DT_FLAGS`/`DT_FLAGS_1`、`DT_NEEDED`、`DT_SONAME`、末段 `memsz`、19 个节区间清零）**全不改判**；
  ⑥`chmod` 到 755、`dd` 重建、拷到全新目录 —— 均无效。
- **最终方案（E517 + E077 四步）**: 在**任务私有 `CONAN_HOME`（`~/tmp/ch/home-sw5-st`）**内
  对两枚依赖 `.so` 执行 `llvm-objcopy --remove-section=.codesign` → `binary-sign-tool sign -selfSign 1`
  （调用时剔除 `LD_LIBRARY_PATH`）→ 覆盖回原路径 → `chmod` 恢复权限 → 校验 `.codesign` 计数恰为 1。
  改前 md5 `8fb0d115…`/`90e16133…`、改后 `198c191e…`/`5a5e868b…`。
  **⛔ 未修改配方任何一字节、未动共享 conan 缓存、未碰 `build`/Step9。**
- **结果**: `st -v` → `st 0.9.1`，`ErrorLoadingCount=0`、`ErrorRelocCount=0`；
  `conan-verify st 0.9.1` **`VERIFY_RC=0`**；本地 CI 模拟（W3）双过；W2 原子性过。
- **遗留风险（已上报主理，供 W4 审计）**: 修复只落在本任务私有 `CONAN_HOME`，配方未改；
  坏签属**已发布依赖包**。若 CI worker 以同一错误红 ⇒ 按 §7.2 返修，改走配方侧
  "有签名工具就签、缺失降级直跑"（仓内 `binary-sign-tool` 先例 2142 处）；⛔ 不为可能的 CI 红预先改配方。

### 对话 #3 [2026-10-01] CI pkg-config 缺失返修（st/0.9.1 返修链主）

- **症状**: PR #14017 CI build #65601 红：`Calling build()` 后零输出，日志第 305 行
  `FileNotFoundError: [Errno 2] No such file or directory: 'pkg-config'`；本地 W3 一直绿。
- **根因**: `subprocess.check_output(["pkg-config", …], env=os.environ)` 用的是 conan 客户端
  进程的 PATH；CI worker env dump 实测 PATH 不含 `/data/service/hnp/bin`（pkg-config 实际所在），
  本机交互 shell 含它 ⇒ 只在 CI 暴露；profile 的 `[buildenv]` 只写进 conanbuild.sh，只有
  `self.run(env="conanbuild")` 的子进程可见，救不了 Python 侧的 `os.environ`。
- **已否决**: ①`tool_requires("pkgconf/…")` —— 同样只注入 conanbuild.sh 的 PATH，
  `os.environ` 依旧没有（ohpcd 仓库实有 pkgconf 3.0.4/3.0.5/3.0.6，有也不解决问题）；
  ②给 env 手补 hnp/bin 绝对路径 —— 把本机布局写死进配方，换台机就碎。
- **最终方案**: `build()` 改纯 Python 解析 PkgConfigDeps 生成的 `.pc`
  （`_pc_expand/_pc_read/_pc_requires/_pc_query`）：被依赖者在后的拓扑序 + `--libs` 的 `-L`
  统一前置 + 同名 flag 去重，口径与 pkg-config 不带 `--static` 一致（只取 Cflags/Libs/Requires）。
- **读数**: 对拍真实 pkg-config 0.29.2 —— `--cflags` 12/12、`--libs` 19/19 token 集合完全一致
  （仅顺序不同）；`conan-verify st 0.9.1` **VERIFY_RC=0**（G2 `conan create` 干净构建 PASS）；
  finish W3 `.ci-result.json` **exit_code=0**、W2 恰 9 文件、manifest `status: built`。

**编译结束**: 2026-09-30 15:34
**最终状态**: built
### 对话 #4 [2026-10-01] CI test_package 运行期装载返修（st/0.9.1 返修链主 第 2 轮）

- **症状**: PR #14017 CI build #65929（失败步 `conan-build-test`）红：`[st -v] rc=127`、
  `Error loading shared library libXft.so.2` / `libfontconfig.so.1`（**其余 7 件 NEEDED 正常装载**）
  + 一串 `Error relocating … Xft*/Fc* symbol not found`；build 本体全过（对话 #3 的 pkg-config 返修生效）。
- **判别（H1 路径 vs H2 签名，A 机单变量矩阵：同一二进制、同一环境，只换那两件的字节）**:
  ① `readelf -d st` = `DT_NEEDED` 10 项 + `BIND_NOW`/`PIE`、**无 DT_RPATH/DT_RUNPATH**（H1 前提为真）；
  ② **M0** 裸跑 `errload=9 rc=127`（本机系统里这 9 件一个都没有）；**M1** `LD_LIBRARY_PATH=依赖 9 目录`
  ⇒ `errload=0 errreloc=0`、打印 `st 0.9.1` ⇒ **路径机制有效，H1 否**（E088 的准确口径是
  「DT_NEEDED 写**绝对路径**时按字面解析、无 `LD_LIBRARY_PATH` 回退」，不是「裸 SONAME 不认 `LD_LIBRARY_PATH`」）；
  ③ **M2** 把两枚**制品仓原件**插到 `LD_LIBRARY_PATH` 最前、其余 7 目录照旧 ⇒ `errload=2`
  （恰 libXft/libfontconfig）且文案与 CI 逐字相同 ⇒ **唯一变量=字节内容 ⇒ H2 成立**；
  ④ `ctypes.CDLL`：原件 `Permission denied` FAIL×2，重签件 OK，同批已发布的
  `libX11.so.6`/`libfreetype.so.6` 对照 OK；⑤ 签名段：原件与重签件 `.codesign` 都在
  （sections=1）、`display-sign` 三者均 `code signature is self-sign`；原件 md5
  `8fb0d115b1cc8753…` / `90e16133de27e244…`，重签件 `198c191ef30ffcf…` / `5a5e868b58726c2e…`。
- **旁证（为什么不加 rpath）**: CI 侧 7/9 件装载成功 ⇒ worker 上 `LD_LIBRARY_PATH` 生效；
  ktimer 自己的 test-report **F9/F10** 写明「注入 RPATH 后**仍**红、由 F8 签名根因（第 10 轮重签）转绿」
  ⇒ **该先例的真修法是重签不是 rpath**；`经验库/12a` 另载 patchelf 后处理出的 ELF 会被 ldso 拒载。
  交付物 RPATH 由框架打包流水线第 5 步负责，本配方不加。
- **最终方案（经主理批准动 `test_package/`）**: `test()` 真跑二进制**之前**，对 `libxft`/`fontconfig`
  两枚依赖包 lib 目录里**实际被装载**的 `.so`（软链取 realpath）做 `llvm-objcopy --remove-section .codesign`
  → `binary-sign-tool sign -selfSign 1 -signAlg SHA256withECDSA` 原地重签 → `chmod`。
  依据 E517 `remove-then-resign-in-task-local-view` + E077 四步 + E135 + `经验库/12a`
  「配方侧有签名工具就签、缺失降级直跑最稳」。工具定位零硬编码：先 `shutil.which`
  （**CI 客户端进程 PATH 实测没有工具箱目录 ⇒ 返回 None**）→ 再取 profile `[conf]` 编译器所在目录
  （该目录实测同时含 `binary-sign-tool`/`llvm-objcopy`）；调用签名器一律剔除 `LD_LIBRARY_PATH`
  （`12a`：构建环境会注入工具链运行时劫持其 libc++ ⇒ exit 127）。
- **读数（提交前两道自证）**: ①**幂等复测** —— 已签件再走一遍 strip+sign：
  `libXft.so.2` `198c191ef30ffcfcd12010b475b373fa` → 同值、`libfontconfig.so.1.17.0`
  `5a5e868b58726c2e4bbe69cf214625b5` → 同值（`same=YES`，`strip_rc=0 sign_rc=0`）；
  ②**干净 PATH 端到端复现** —— 剥掉工具箱目录的 PATH（两工具 `which` 均 None）下，用**全新任务私有
  CONAN_HOME + 制品仓原件依赖**跑 `conan create`：日志实读「已剥段+重签 …/libXft.so.2（strip rc=0 / sign rc=0）」
  「已剥段+重签 …/libfontconfig.so.1.17.0」→ `[st -v] … st 0.9.1` →
  `PASS: st 0.9.1 消费者测试通过（真实执行二进制 + 版本串 + usage）` → **CREATE_RC=0**。
- **风险（如实）**: `binary-sign-tool`/`llvm-objcopy` 在 **CI worker** 的工具箱目录里**未实证**
  （A/B 两机均在，CI 构建所用编译器同处该目录）⇒ 若 CI 首错为「工具不存在」属**新类别第 1 轮**，
  按停损口径回主理定；若仍是装载红 ⇒ 同类别第 2 轮红即停。

**编译结束**: 2026-10-01 04:05
**最终状态**: built
---

**编译结束**: 2026-10-01 03:59
**最终状态**: built
