# conan-verify 补测报告 — cycfx2prog 0.47（G4 / L2 / L4 / L5）

> 补测原因：`conan-verify` 对 `package_type = "application"` 的纯可执行包会整组走
> 「无 cache 路径」分支 —— 报告里 `G4` 打 `⚠️ 无法找到程序包 ID`、`L2/L4/L5` 打
> `⏭️ 跳过（无 cache 路径）`，而同一行仍打印 `✅ PASS`（工具文案缺陷，以跳过行为准）。
> 本文件按 workflow 第 7.2 节的人工补测口径逐项给出原始判据。
>
> **指针说明（避免误读）**：本文件正文里出现的 Conan 缓存分片目录名（形如
> `…/p/b/cycfx…/p`）是**某一具体轮次**的目录名。分片目录名 = 包名前 5 字符 + 内容 hash，
> 每次清缓存重建都会换名，旧目录在后续轮次已不存在，**因此不要把正文里的目录名当固定路径，
> 复现时按下方「包目录定位」一节的命令现场定位**；判据本身（文件清单、退出码、ELF 属性、
> sha256）与目录名无关。
>
> 本任务全程观察到的分片目录名（同一份源码、四轮独立构建，产物 sha256 四轮同值）：
>
> | 轮次 | 分片目录名 | 说明 |
> |------|-----------|------|
> | round 1 | `cycfx8e47bdce965e9` | 首个采信轮（`conan-verify` 清缓存干净轮） |
> | round 2 | `cycfxf0ef35aa590db` | 同提交强制重建（`--build='cycfx2prog/*'`） |
> | round 3 | `cycfx117fe41cafc46` | `2e5ade0b` tip 上的 `conan-verify` 清缓存轮 |
> | round 4a | `cycfxcc926641d991d` | `a4bb0006` tip 上的 `conan-verify` 清缓存轮 → **提交版 `reports/conan-create.log` / `conan-verify-report.md` 出自此轮** |
> | round 4b | `cycfx91543efa327d1` | 同一 tip 的 `finish` 内嵌 W3 轮 → **提交版 `reports/w3-local-ci.log` 出自此轮** |
>
> 说明：`finish` 内部会再跑一次 `conan-verify`/W3，所以**同一个 tip 上会产生两个子轮**
> （4a/4b），分片目录与日志一一对应如上；两轮都是改完 `test_package/test.sh`（仅加注释，
> 语义零变化）之后跑的，因此与 PR 内 `test_package/` 的最终内容严格对应，不存在"日志产自
> 改动前一轮"的轮次错配。两轮的 mtime（09:20:52 / 09:21:24）都**早于**证据提交时间
> （09:23:08），符合"先在本 tip 验证、再提交证据"的顺序。
>
> 判据必须从**日志自身**回取目录（多分片并存时 `glob | head -1` 取值不确定）：
>
> ```sh
> grep -m1 'Package folder' reports/conan-create.log   # → …/p/b/cycfxcc926641d991d/p
> grep -m1 'Package folder' reports/w3-local-ci.log    # → …/p/b/cycfx91543efa327d1/p
> ```
>
> `conan-create.log` 特征：`Calling source()` ×1、`Calling build()` ×1、`RUN: make` ×1、
> `TOTAL=33 PASS=33 FAIL=0`。
>
> 各轮之间**构建输入的变化是可枚举的**，判据必须用**完整包路径**（本仓库的裸 pathspec
> 恒返回空、等于空判据）：
>
> ```sh
> # A) 采信轮与前一验证轮之间，包构建输入逐字节未变
> git -C "$TARGET_REPO" diff --numstat 5dfe54d4..2e5ade0b -- \
>   archives/c/cycfx2prog/0.47/conanfile.py \
>   archives/c/cycfx2prog/0.47/conandata.yml \
>   archives/c/cycfx2prog/0.47/test_package        # → 空
>
> # B) 其后唯一的包内改动：test.sh 增加 7 行注释（0 行删除）
> git -C "$TARGET_REPO" diff --numstat 2e5ade0b..91d5e273 -- \
>   archives/c/cycfx2prog/0.47/conanfile.py \
>   archives/c/cycfx2prog/0.47/conandata.yml \
>   archives/c/cycfx2prog/0.47/test_package
> # → 7  0  archives/c/cycfx2prog/0.47/test_package/test.sh
>
> # C) 该改动全部是注释行（过滤掉 # 开头的增删行后计数为 0）
> git -C "$TARGET_REPO" diff 2e5ade0b..91d5e273 -- \
>   archives/c/cycfx2prog/0.47/test_package/test.sh \
>   | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | grep -v '^[+-][[:space:]]*#' | wc -l   # → 0
> ```
>
> 即包构建输入在 A 区间零变化、在 B 区间只有不参与编译的注释；因此 round 1–4 的产物
> sha256 相同是可预期的，且提交版日志（round 4a/4b 两个子轮）对应的正是含该注释的最终
> `test.sh`。
> 注意本包**没有 `patches/` 目录**（零补丁），因此判据里不含 patches 路径。
> 引用形态 `cycfx2prog/0.47@ohpcd/stable`。

## 包目录定位

多分片目录并存时**不要**用 `glob | head -1` 取包目录（取值不确定，命中哪个分片取决于
目录名字典序），应从要核对的**日志自身**回取：

```sh
# 提交版 conan-create.log 对应的包目录
PKGDIR=$(grep -m1 'Package folder' reports/conan-create.log | awk '{print $NF}')
# → /storage/Users/currentUser/.conan2/p/b/cycfxcc926641d991d/p

# 提交版 w3-local-ci.log 对应的包目录（finish 内嵌 W3 轮）
PKGDIR_W3=$(grep -m1 'Package folder' reports/w3-local-ci.log | awk '{print $NF}')
# → /storage/Users/currentUser/.conan2/p/b/cycfx91543efa327d1/p

# 需要"任意一个可用包目录"时（例如只看产物属性）才用 glob：
PKGDIR=$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/cycfx*/p | head -1)
```

分片目录名是「包名前 5 字符 + hash」（`cycfx…`），`ls -d p/b/cycfx2prog*` 必定失配；
目录名每轮变化，**必须现场定位**（见上面的指针说明表格）。

## G4 — 产物完整性（工具报「无法找到程序包 ID」，人工补测）

`conan list --format=json` 的顶层键带 `@ohpcd/stable` 而 `self.ref` 不带，工具取键时
`KeyError` 被吞（workflow 第 17 节已知缺陷），因此该路径对**所有**包类型都会失败。

> **本节捕获输出取自 round 1**（分片目录 `cycfx8e47bdce965e9`）；判据值与轮次无关，
> 已在 round 4a/4b 两个分片目录复算相同。

```sh
$ cd "$PKGDIR" && find . -type f -o -type l | sed 's|^\./||' | sort
bin/cycfx2prog
conaninfo.txt
conanmanifest.txt
```

与 `package_info()` 声明互证（`conanfile.py:130-133`）：

```python
self.cpp_info.libs = []
self.cpp_info.libdirs = []
self.cpp_info.includedirs = []
self.cpp_info.bindirs = ["bin"]
```

结论：包内**只有** `bin/cycfx2prog` 一个交付物，与 `package_type = "application"`、
`bindirs = ["bin"]`、`libdirs = []`、`includedirs = []` 完全一致；`conaninfo.txt` 与
`conanmanifest.txt` 是 Conan 元数据，不是产物。✅ PASS

## L2 — 消费者侧真实命令行为（工具 skip，人工补测）

判据用**消费者运行环境**（`conanrun`），因为交付物是动态链接 musl 且 `DT_NEEDED`
含 `libusb-1.0.so.0`；脱离运行环境直接执行会得到加载器错误（见文末说明）。

> **本节捕获输出取自 round 1**（分片目录 `cycfx8e47bdce965e9`）；判据值与轮次无关。
> `command -v` / `<PKGDIR>/bin/cycfx2prog` 只是当轮的实际路径，复现时按要核对的轮次
> 从日志回取目录即可（见「包目录定位」一节）。

```sh
$ conan install --requires="cycfx2prog/0.47@ohpcd/stable" \
    --profile:host="$HOST_PROFILE" -g VirtualRunEnv -of <tmpdir>
$ . <tmpdir>/conanrun.sh
$ echo $LD_LIBRARY_PATH
/storage/Users/currentUser/.conan2/p/libus04e54d4f229a5/p/lib
$ command -v cycfx2prog
/storage/Users/currentUser/.conan2/p/b/cycfx8e47bdce965e9/p/bin/cycfx2prog

$ cycfx2prog --version   ; echo rc=$?
cycfx2prog version 0.47
rc=0
$ cycfx2prog --help > /dev/null ; echo rc=$?
rc=0
$ cycfx2prog --list     ; echo rc=$?
rc=0
$ cycfx2prog            ; echo rc=$?
No unconfigured Cypress FX2 attached.
rc=1
$ cycfx2prog -id=1234.5678 ; echo rc=$?
Device with vendorID=0x1234, productID=0x5678, nth=0 not attached.
rc=1
```

全部退出码 ≠ 126（内核拒绝 exec 的判据），且带真实参数的业务输出符合源码语义。
`--list` 的 rc=0 表示 `usb_init()` → `usb_find_busses()` → `usb_find_devices()` 三步
全部成功（`cycfx2prog.cc:212-222`，任一步失败都会以 1 退出）。✅ PASS

## L4 — 静态安全属性（工具 skip，人工补测）

> **本节捕获输出取自 round 1**（分片目录 `cycfx8e47bdce965e9`）；五项 ELF 属性与
> 轮次无关，已在 round 4a/4b 两个分片目录复算相同。

```sh
$ readelf -hW "$PKGDIR/bin/cycfx2prog" | grep -E 'Type|Machine'
  Type:                              DYN (Position-Independent Executable file)
  Machine:                           AArch64
$ readelf -lW "$PKGDIR/bin/cycfx2prog" | grep -E 'GNU_STACK|GNU_RELRO'
  GNU_RELRO      0x007320 0x0000000000009320 ... 0x000458 0x000ce0 R   0x1
  GNU_STACK      0x000000 0x0000000000000000 ... 0x000000 0x000000 RW  0
$ readelf -dW "$PKGDIR/bin/cycfx2prog" | grep -E 'BIND_NOW|FLAGS|NEEDED'
 0x0000000000000001 (NEEDED)  Shared library: [libusb-1.0.so.0]
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
 0x000000000000001e (FLAGS)   BIND_NOW
 0x000000006ffffffb (FLAGS_1) Flags: NOW PIE
$ file "$PKGDIR/bin/cycfx2prog"
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

逐项：`DYN`（PIE）✅、`GNU_STACK RW`（NX）✅、`GNU_RELRO` ✅、`BIND_NOW` ✅、
`FLAGS_1 PIE` ✅。**未做 `strip`**：workflow 第 7.2 节实测未 strip 的 hnp 产物 rc=0、
`strip` 后 rc=126；且 hnp clang 产物自带链接器签名（`.codesign`），不对其重签。✅ PASS

## L5 — 产物基线与可复现性（工具 skip，人工补测）

**可复现性判别优先**：同一份源码反复清缓存重建，逐产物比对 sha256。本任务共做了
**四轮**（round 4 在 tip 上分为 `conan-verify` 与 `finish` 内嵌 W3 两个子轮，详见顶部指针表）。

```sh
# round 1：首个采信轮（清缓存干净轮）        → 分片 .../p/b/cycfx8e47bdce965e9/p
$ sha256sum "$PKGDIR/bin/cycfx2prog"
703abddb03a7ad935615fdd81e323796c3245aede67bc9ab7aa3636a96283aed  .../bin/cycfx2prog

# round 2：同提交同源码强制重建               → 分片 .../p/b/cycfxf0ef35aa590db/p
$ conan create "$PACKAGE_DIR" -pr:h="$HOST_PROFILE" -pr:b="$HOST_PROFILE" \
    --build='cycfx2prog/*' --user=ohpcd --channel=stable     # rc=0，日志含 1 条 RUN: make
$ sha256sum "$PKGDIR/bin/cycfx2prog"
703abddb03a7ad935615fdd81e323796c3245aede67bc9ab7aa3636a96283aed  .../bin/cycfx2prog

# round 3：2e5ade0b tip 上的 conan-verify 清缓存轮   → 分片 .../p/b/cycfx117fe41cafc46/p
$ sha256sum "$PKGDIR/bin/cycfx2prog"
703abddb03a7ad935615fdd81e323796c3245aede67bc9ab7aa3636a96283aed  .../bin/cycfx2prog

# round 4a：a4bb0006 tip 上的 conan-verify 清缓存轮 → 分片 .../p/b/cycfxcc926641d991d/p
#           （提交版 reports/conan-create.log 出自此子轮）
$ PKGDIR=$(grep -m1 'Package folder' reports/conan-create.log | awk '{print $NF}')
$ sha256sum "$PKGDIR/bin/cycfx2prog"
703abddb03a7ad935615fdd81e323796c3245aede67bc9ab7aa3636a96283aed  .../bin/cycfx2prog

# round 4b：同一 tip 的 finish 内嵌 W3 轮            → 分片 .../p/b/cycfx91543efa327d1/p
#           （提交版 reports/w3-local-ci.log 出自此子轮）
$ PKGDIR=$(grep -m1 'Package folder' reports/w3-local-ci.log | awk '{print $NF}')
$ sha256sum "$PKGDIR/bin/cycfx2prog"
703abddb03a7ad935615fdd81e323796c3245aede67bc9ab7aa3636a96283aed  .../bin/cycfx2prog
```

**四轮五目录**独立构建（分片目录依次为 `cycfx8e47bdce965e9` → `cycfxf0ef35aa590db` →
`cycfx117fe41cafc46` → `cycfxcc926641d991d` → `cycfx91543efa327d1`）产物逐字节一致 →
**构建可复现**，基线可以给出（不存在 `__DATE__`/`__TIME__` 内嵌，Release flags 无 `-g`，
因此无 DWARF `DW_AT_comp_dir` 漂移面）。这也直接说明顶部的「目录名会变、判据不变」：
各轮里只有目录名不同，sha256 完全相同。

**稳定聚合基线**（包目录内用相对路径；排除 `conaninfo.txt`/`conanmanifest.txt`，
后者首行是打包时间戳，含它的聚合跨轮必然漂移）：

```sh
$ cd "$PKGDIR" && find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt \
    | sed 's|^\./||' | sort | xargs sha256sum | sha256sum
8112473e2fb7806d73bf7f5fe7b239d1a3b3f2eaf8c57f8842c09cf46f0ecde8  -     # round 1/2/3/4a/4b 同值（在 cycfxcc926641d991d 与 cycfx91543efa327d1 两个分片目录复算均一致）
```

产物基线（单文件交付物）：

| 文件 | 大小 | sha256 |
|------|------|--------|
| `bin/cycfx2prog` | 见包目录 | `703abddb03a7ad935615fdd81e323796c3245aede67bc9ab7aa3636a96283aed` |

✅ PASS

## 附：脱离运行环境的执行结果（说明而非缺陷）——同时解释 W3 的 L2 skip

`bin/cycfx2prog` 直接执行（不 source `conanrun.sh`）时退出码 127：

```text
Error loading shared library libusb-1.0.so.0: (needed by .../bin/cycfx2prog)
Error relocating .../bin/cycfx2prog: libusb_init: symbol not found
```

这是**动态链接消费方的运行环境**问题（`libusb-1.0.so.0` 只存在于 Conan 包目录），不是
产物缺陷：`conanrun` 环境（或消费者自己的 loader 配置）会提供该路径。已同时核对
`DT_NEEDED` 与 `soname`，两者的库名一致。

`reports/w3-local-ci.log` 里的同一现象：

```text
[step] L2: Smoke test (version/help check)...
[warn] L2: cycfx2prog --version/--help failed (non-blocking)
L2_RESULT=skip: cycfx2prog version/help failed
```

W3 的 L2 smoke 探针在**未注入运行环境**的裸 PATH 下执行交付物，因此必然命中上述加载器
错误（workflow 第 17 节已登记 W3 L2 探针的形态缺陷，本包属"有依赖动态库的 CLI"这一
新增形态）。按 workflow 口径，此类 skip 必须人工补测 —— 即本文件「L2」一节：在
`conanrun` 环境下 5 条真实命令全部得到预期退出码与输出。L2 的实际结论为 **PASS**，
`L2_RESULT=skip` 是探针环境问题，不是产物问题。

同一轮 W3 的其余结果（`reports/w3-local-ci.log`）：

```text
L0_RESULT=pass: all checks passed          # 含 L0i 依赖可用 / L0j 版本冲突 / L0k commands.json / L0m 目录结构
L1_RESULT=pass: test_package executed      # L1a/L1b 证据齐全；L1c 报「无上游 make check/ctest」= 上游 0 测试的如实结果
L2_RESULT=skip: (见上，人工补测为 PASS)
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
[step] L1e: Destructive negative test (R34)... [ok] test genuinely depends on cycfx2prog
Pass rate: 100.0% (1/1)                    # Total 1 / Success 1 / Failed 0
```

## 附：G0 知识命中的误报

`conan-verify` 的 G0 报 `Knowledge hit: E490`（autotools helper 脚本可执行位），并给
`⚠️ 已知风险 E490 未在配方中处理`。本包是**手写 Makefile**（`prescan` 判
`build_systems=['make']`、无 `configure`/`config.guess`），E490 不适用，属检索错配
（workflow 第 17 节已登记「知识建议检索错配多例」）。G0 本身 PASS，不影响结论。
