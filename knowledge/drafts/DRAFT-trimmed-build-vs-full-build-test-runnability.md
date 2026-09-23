# DRAFT-trimmed-build-vs-full-build-test-runnability — 裁剪构建不能作为「上游测试不可运行」的证据

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-11
> **Severity**: 🟡 medium | **Category**: testing / false-declaration / build-config

## 相关既有条目（同族差异化定位）

| 既有条目 | 同族点 | 本 skill 的增量（差异化） |
|---------|--------|--------------------------|
| **E363** | 均涉及「harness 静默跳过、用退出码 0 假通过」 | E363 讲的是 harness **setup 失败却报 PASS** 的假绿；本条目讲的是**构建配置选择**导致的可跑性误判（交付配置 vs 测试配置），并给出「必须做一次完整构建」的证伪程序 |
| **E165** | 均有 `#!/bin/bash` 需改指实际 bash | E165 是 shebang 解释器缺失的单点修复；本条目把它列为「完整构建后才浮现的阻塞项」之一 |
| **E488 / E489** | 同属 OHOS 环境限制类 | 那两条讲 hmdfs/chmod 与 CTest 签名闭包；本条目讲**如何判断某限制是真限制还是配置造成** |
| **DRAFT-bats-suite-ohos-runtime-shims** | 均为「测试套件可跑性」 | 那条是 bats 框架的实跑装配；本条目是**决策/举证方法论**（何时才有资格声明不可运行） |

> 查证（2026-09-11）：`裁剪构建`、`disable-all-programs`、`完整构建.*测试`、`ts 套件` 在
> knowledge/doc 与 knowledge/drafts 下命中 **各 0 条**（`xargs -I` 命中 E363，故相应内容
> 不作为本条主贡献，仅作环境适配清单引用）——本条为空白领域。

## Scope（何时用）

包配方做了**裁剪构建**（只编目标库、关掉工具/程序/测试），而上游自带测试套件需要那些
被裁掉的产物时。典型错误声明：

> 上游测试用例通过率：0/0 可跑（上游 ts 套件需完整工具集环境，裁剪构建仅编库，按 rule 1.2 声明）

## 核心：这是两个不同命题，不能跳步

```
(a) 「当前交付配置（裁剪构建）的产物里跑不了测试」   ← 通常为真
(b) 「上游测试在 OHOS 上不可运行」                    ← 未被 (a) 证明
```

把 (a) 直接写成 (b) 会**系统性低估通过率**。裁剪构建只证明包内缺辅助二进制，
不证明套件本身跑不通。

**实证（本条目来源）**：util-linux 2.42 原声明「ts 套件需完整工具集环境故不可运行（0 可跑）」；
本地**完整构建**后实跑 → **91/91 套件全 PASS（176 sub-test）**：

| 套件 | 结果 |
|------|------|
| `blkid` | All 11 tests PASSED（含 134 个 sub-test）|
| `mount` | All 33 tests PASSED |
| `findmnt` | All 6 tests PASSED |
| `uuidgen` | All 2 tests PASSED |

同族：combblas 2.0.0（PR #9161）从「需外部 TESTDATA 不可运行」纠正为实跑 **18/20**。

## 第二类误报：测试框架自身静默跳过

即使做了完整构建，框架仍可能**跳过全部用例**而不报错。util-linux 的 `tests/run.sh`：

```sh
if [ -z "$SYSCOMMANDS" -a ! -f "$top_builddir/test_ttyutils" ]; then
    echo "Tests not compiled! Run 'make check-programs' to fix the problem."
    exit 1
fi
```

→ 必须先 `make -j4 check-programs` 生成框架需要的辅助二进制。**只看退出码**会再次误判。

## 五步程序（缺一不可）

### ① 分清两个命题
先明确：当前是"交付配置跑不了"，未必等于"测试不可运行"。

### ② 做一次完整构建（唯一能证伪的手段）
去掉裁剪开关，保留上游默认目标集：

```bash
cd $BUILD && TMPDIR=$BUILD $SRC/configure \
  --host=aarch64-unknown-linux-ohos \
  --build=aarch64-unknown-linux-ohos --disable-nls
TMPDIR=$BUILD make -j4            # 不裁剪 → 含工具二进制
```

若全量构建被无关目标挡住（如 util-linux 的 `lsfd` 撞 OHOS sysroot 的
`sockaddr_storage` 重复定义），可**定向构建测试所需目标**绕开：

```bash
make -j4 blkid findmnt uuidgen libblkid.la libuuid.la
```

> 注意：`configure` 直接跑可能报 `cannot guess build type`（OHOS 的 `uname -s` 是
> HarmonyOS，E007）——需显式传 `--host/--build`，这也反向佐证了配方内 config.guess
> patch 的必要性。

### ③ 补齐环境适配（此步才产生真实阻塞列表）
完整构建后，阻塞通常只剩几项**可修的**环境差异：

| 适配 | 原因 |
|------|------|
| `#!/bin/bash` → 实际 bash 路径 | OHOS 无 `/bin/bash`（E165）；否则生成脚本报 `Error 126` |
| 补 GNU 兼容 `xargs` | OHOS `toybox xargs` 不支持 `-I`（E363）；**实现要点：遇首个非选项参数须立即停止选项解析**，否则会吞掉 `bash -c` 的 `-c` |
| `TMPDIR` 指向可写目录 | OHOS `/tmp` 只读 |
| `make check-programs` | 框架需要的辅助二进制（见上） |

### ④ 断言真实执行痕迹（防假通过）
**不能**用退出码 0 当通过证据（框架可静默跳过全部用例后仍退 0，E363）：

```bash
grep -cE "\.\.\. (OK|FAILED)|All [0-9]+ tests (PASSED|FAILED)" <log>
```

本轮即靠此断言发现：某轮 `All 11 tests PASSED` 是**我的 xargs shim 把命令搞坏**造成的
假象（真实命令未执行），修正 shim 后才发现真结果。

### ⑤ 解读报错：`symbol not found` 常是**加载失败的下游症状**

完整构建后若仍失败，**报错文本的顺序**比内容更重要：

```
Error loading shared library libjson-glib-1.0.so.0: Permission denied   ← 真因（库未装载）
Error relocating ./x: json_object_has_member: symbol not found          ← 下游症状
Error relocating ./x: json_array_get_length: symbol not found           ← 下游症状
```

**成串的 `symbol not found` 几乎必然是"依赖库根本没被加载"**——库未装载，其中任何符号
自然都解析不到。此时若去查"为什么 json-glib 缺符号"会**方向错误**（甚至误判为上游库有缺陷）。

正确的判定顺序：

```bash
# 1) 先看是否真有 "Error loading shared library" / Permission denied（真因在首行）
# 2) 该 .so 的文件名/别名是否解析得到（E505：LD_LIBRARY_PATH 压过 DT_RPATH、
#    soname 别名在 HMDFS 上不可解析）
# 3) 直接验证符号是否真的存在 —— 若存在，则问题一定在"加载"而非"符号"
llvm-nm -D <lib>.so.<ver> | grep <symbol>      # 有输出 → 库本身不缺符号
# 4) 权限/属主是否阻止加载（E488/E489：HMDFS 钳制属主与 other 位）
python3 -c "import ctypes; ctypes.CDLL('<abs path>')"   # 单库加载，隔离出真因
```

> **本轮实例（gusb/0.4.9，PR #8937）**：实跑报 `Error loading shared library
> libjson-glib-1.0.so.0: Permission denied` + 一串 `json_*: symbol not found`。
> 根因是**该 .so 权限 770、属主为非当前 UID，而 HMDFS 吞掉 chmod**（`chmod 777`
> 后仍为 770）——`llvm-nm -D` 确认 `json_object_has_member` 等符号**本来就存在**。
> 因此 PR 描述中原先"json-glib 运行时符号加载问题"的措辞被修正为"依赖 .so 的
> dlopen 权限问题"，避免读成 json-glib 自身有缺陷。

## 记录口径

完整构建的结果写入 manifest 时，**必须同时说明配方为何不并入**：

```
ts 套件实跑 91/91 PASS（本地完整构建 + 3 项环境适配）；
配方 --disable-all-programs 裁剪使套件无法随包运行，故 ts 结果为本地实测、
不并入配方构建。
```

二者不可混为一谈——既不能因裁剪就声明"不可运行"，也不能假装套件随包运行。

## 备选（fallback）

若完整构建后仍跑不通（如确缺某个系统工具且无替代），则**同时记录两种配置**并指名阻塞：
交付配置＝裁剪构建（套件不随包运行）、完整构建实测 N/M 通过、剩余失败具名原因。
不得只留"不可运行"的整体声明。

## 禁止

- ❌ **裁剪构建故上游测试不可运行**：只证明 (a)，不能推出 (b)。
- ❌ **未做完整构建即写 rule 1.2**：rule 1.2 的"环境限制"以尽力尝试为前提。
- ❌ **以 rc=0 作为套件通过依据**：框架可静默跳过（E363），必须核对真实执行痕迹。

## 实证

- **util-linux/2.42（PR #9262）**：原声明 0 可跑 → 完整构建后 **91/91 套件 PASS**
  （176 sub-test）。3 项适配：bash shebang ×7、GNU xargs、TMPDIR。
- **combblas/2.0.0（PR #9161）**：通过率 **1/20 → 7/20 → 9/20 → 18/20（90%）**，
  经三轮逐步证伪"不可运行"声明。
