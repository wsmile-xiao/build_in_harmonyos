# DRAFT：test_package 跑自家产出的可执行文件全部退 126 —— 别把它当成「包缓存 noexec」，那是误诊

> 状态：草稿（待知识库主编 promote）
> 来源：osm2pgrouting 3.0.0 适配，`archives/o/osm2pgrouting/3.0.0`，CI #55334
> 类别：conan / 测试 / OHOS 签名 / ELF
> 配套草稿：`DRAFT-osm2pgrouting-3.0.0-cli-test-without-backend-service`（同一个
> `test.sh` 的另一半：为什么是 22 条断言）、
> `DRAFT-ohos-elf-skip-strip-codesign`（同一根因的上游面）、
> `DRAFT-binary-sign-tool-buildenv-ldlibrarypath`（签名调用本身的坑）

## 症状

CI 只在 **test_package** 阶段失败，形态极具误导性：

```
# exec failed: rc=126 args=[--version]
# captured output: test.sh: line 59: /root/.cache/conan2/p/b1e…/bin/osm2pgrouting:
#                  Operation not permitted
```

22 条断言里 **8 条查安装文件（`mapconfig*.xml` / `COPYING`）的照常通过，
14 条依赖二进制输出的全挂** —— 于是失败面看起来"很窄"，很容易被读成
"这个 CLI 的行为不对"，而不是"它**根本没被启动过**"。

## 误诊路径（先说不要走的）

`Operation not permitted` + 退出码 `126` + 一个位于 `~/.cache/conan2/p/…` 下的路径，
三条线索拼起来指向一个听起来完全合理的结论：

> **conan 包缓存所在的分区被挂成了 noexec。**

这条推理是错的，但它会驱动一个**看着对、实际无效**的修法：
把二进制 `cp` 到 test_package 的构建目录再跑。搬完之后报错一字不差，只是路径变了。

两条反证足以当场证伪：

```sh
cp "$PKG_ROOT/bin/osm2pgrouting" /tmp/probe && /tmp/probe --version   # 仍然 126
chmod 755 "$PKG_ROOT/bin/osm2pgrouting" && "$PKG_ROOT/bin/osm2pgrouting" --version
                                                                     # 仍然 126
```

**换个目录仍 126 → 不是挂载选项；chmod 755 仍 126 → 不是权限位。**

## 根因

### (1) OHOS 拒绝执行未签名的 ELF

内核在 `execve` 阶段就回 `EPERM`，shell 统一把它映射成**退出码 126**
（"command found but not executable"）。缺的是 **`.codesign` 段**，
不是权限、不是挂载、不是路径。判据：**同一绝对路径下换成一个已签名
（或系统自带）的 ELF 就能跑。**

### (2) 本包产物为什么恰好没有 `.codesign`

OHOS 的 lld 在**链接期**会给产物自动补一个自签的 `.codesign` 段 —— 这就是绝大多数
OHOS 预编译包拿来就能跑的原因。但只要链接后有任何一步字节级改写
（`strip` / `objcopy` / `patchelf` / 重新打包），段内容就与文件内容对不上
→ 校验失败 → 同样按"未签名"处理、同样 126。

本包 `package()` 里对 `bin/osm2pgrouting` 做过 strip，签名随之失效。
而在 Linux/conan 视角下文件一切正常：

```
$ file bin/osm2pgrouting
ELF 64-bit LSB executable, ARM aarch64, dynamically linked, …
$ readelf -S bin/osm2pgrouting | grep -c '\.codesign'
0
```

## 处置（可复用）

在 `test_package/test.sh` 里、**任何一次 exec 之前**，把已安装的二进制 staging 到
可写目录再自签。staging 与签名是同一件事的两半，缺一不可：

```sh
STAGE_DIR="${2:-${TMPDIR:-/data/storage/el2/base/cache}/osm2pgrouting-test}"
INSTALLED_BIN="$PKG_ROOT/bin/osm2pgrouting"
BIN="$STAGE_DIR/bin/osm2pgrouting"
SIGNER="/data/service/hnp/bin/binary-sign-tool"

rm -f "$BIN"                      # 先清上一次的副本，见下条要点
mkdir -p "$STAGE_DIR/bin"
if ! cp "$INSTALLED_BIN" "$BIN" 2>/dev/null; then
    echo "FAIL: cannot stage $INSTALLED_BIN (package bin/ missing?)"; exit 1
fi
chmod 755 "$BIN" >/dev/null 2>&1
if [ -x "$SIGNER" ]; then
    if ! env -u LD_LIBRARY_PATH "$SIGNER" sign \
             -inFile "$BIN" -outFile "$BIN" -selfSign 1 >/dev/null 2>&1; then
        echo "FAIL: binary-sign-tool could not sign the staged binary"; exit 1
    fi
else
    echo "WARN: $SIGNER not found; the binary will not be executable on OHOS"
fi
```

每一条都有独立的失败面：

| 要点 | 不这么做会怎样 |
|------|----------------|
| **签副本，绝不就地改包内文件** | 包清单在 `package()` 结束时已 compute，就地写会让哈希与内容不符 |
| **`cp` 前先 `rm -f` 旧副本** | CI 的 L1e 破坏性检查（移走包内 `bin/` 再跑一遍、要求失败）会命中残留副本而**假通过** |
| **`cp` 失败必须 fatal** | 早先版本让 cp 静默失败，L1e 下报的是一堆莫名其妙的断言失败，而不是"缺少二进制" |
| **调用签名器要 `env -u LD_LIBRARY_PATH`** | conan buildenv/runenv 把 OHOS SDK 的 `llvm/lib` 前置进 `LD_LIBRARY_PATH`，签名器自己的 `NEEDED libc++.so` 命中 `std::__1` 那份 → 成串 `Error relocating … symbol not found`、退 **127** |
| **`SIGNER` 缺失只 WARN 不 FAIL** | 在没有该工具的环境（本机静态检查）不该把测试判死 |
| **驱动脚本用 bash** | OHOS 的 `/system/bin/sh`(mksh) 执行 ELF 不可靠，经 `CONFIG_SHELL` 或显式 `/data/service/hnp/bin/bash` |

**附加要点（诊断友好）**：`run()` 在 `RC != 0` 时把 rc 与实际输出回显成 TAP 注释行，
否则 "二进制起不来" 和 "文案对不上" 在 CI 日志尾部长得一模一样：

```sh
run() {
    OUT="$("$BIN" "$@" 2>&1)"; RC=$?
    if [ "$RC" -ne 0 ]; then
        printf '# exec failed: rc=%s args=[%s]\n' "$RC" "$*"
        printf '# captured output: %s\n' "$OUT"
    fi
}
```

**仓内先例**

- `archives/s/sound-juicer/3.40.0/test_package/test.sh` —— shell 侧同款（`cp` 副本
  + `binary-sign-tool … -selfSign 1` + `trap 'rm -f' EXIT`）；
- `archives/g/glade/3.40.0/test_package/conanfile.py` 的 `_sign()` —— Python 侧，
  多一步 `llvm-objcopy --remove-section .codesign` 先剥旧段再签。

## 怎么提前发现

1. **症状侧判据**：test_package FAIL，报错含 `Operation not permitted` 或 `rc=126`，
   且"查文件存在性"的断言通过、"跑二进制"的断言成片失败 —— 两组数量大致对半。
2. **反证侧判据**（区分 noexec/权限误诊）：把产物分别拷到 `$HOME`、`/tmp`、
   构建目录各跑一次，**三处报错完全一致** → 不是目录问题；`chmod 755` 后仍 126
   → 不是权限位问题。
3. **确认侧判据**：`readelf -S <bin> | grep codesign` 无输出 → 确认未签名。

同一形态也出现在**构建期工具**上（glib 的 `glib-compile-resources` 被 ninja 记成
`[code=126]`），以及 test_package 里临时 `cp` 出来的任何副本 —— **`cp` 会把
`.codesign` 一起拷走，但副本一旦被任何方式重写就失效**。

## 反例（不要做）

| 反例 | 后果 |
|------|------|
| `chmod 755` 当修法（"加个执行位就能跑"） | 对未签名 ELF 完全无效，改完仍是 126；本地报错文案一字不差，极易带着一个什么都没解决的改动进 CI |
| 归因于"conan 包缓存分区 noexec"，去 `mount -o remount,exec` / 换目录 | 挂载选项是配方无法控制的本机属性；且解释不了"系统自带 ELF 在同一个目录下能跑" |
| 对**包内文件**就地 `sign -inFile "$PKG_ROOT/bin/…"` | 破坏已 compute 的包清单；CI 复跑内容漂移，可复现性丧失 |
| 让 `cp` 静默失败继续往下跑 | L1e 破坏性检查下报一堆无意义的断言失败，掩盖"缺少二进制"这个直白结论 |
| 裸调用 `binary-sign-tool`（不剔除 `LD_LIBRARY_PATH`） | 退 127、成串 `Error relocating`，且比 126 更难辨认 |

## 退路

**让产物在构建期就带合法签名、此后不再触碰它**：确认工具链走 OHOS lld（会自签）、
把配方里链接后的 `strip`/`objcopy` 去掉或挪到链接前、`package()` 之后不再做任何
字节级改写（含 `patchelf` 改 rpath、重压缩打包）。优点是 test_package 里不必再签、
真机部署也直接可跑；缺点是**对"链接后必须 strip 减体积"或"必须 patchelf 修 rpath"
的包不成立**（见 `DRAFT-ohos-elf-skip-strip-codesign`：签名一旦失效只能重签），
且改的是产物形态、容易波及已 compute 的文件哈希，故仅在没有 test_package 侧
下手空间时采用。

## 验证

- **最小验证（不需要 conan）**：起一个假 package 目录，
  `mkdir -p /tmp/pk/bin && cp <built>/osm2pgrouting /tmp/pk/bin/`，
  再 `bash test.sh /tmp/pk /tmp/stage` → `assertions: 22, failures: 0`。
- **破坏性自检**：把 `/tmp/pk/bin/` 移走再跑 → `cp` 失败即 `exit 1`
  并打印 `FAIL: cannot stage …`（证明断言绑在产物上，不是恒真）。
- **端到端**：`conan create archives/o/osm2pgrouting/3.0.0 -pr:h=ohos-aarch64
  -pr:b=ohos-aarch64 --build=missing`，观察 test_package 不再出现 `rc=126`。

## 关联

- `archives/o/osm2pgrouting/3.0.0/test_package/test.sh`（签名 + staging）
- `archives/o/osm2pgrouting/3.0.0/test_package/conanfile.py`（把 staging 根目录
  作为第二个参数传给 test.sh）
- `DRAFT-ohos-elf-skip-strip-codesign`（上游面：链接期自签 + 链接后改写使签名失效）
- `DRAFT-binary-sign-tool-buildenv-ldlibrarypath`（`env -u LD_LIBRARY_PATH` 的由来）
- `DRAFT-osm2pgrouting-3.0.0-cli-test-without-backend-service`（同一个 `test.sh`
  的 22 条断言为什么这么写；本条失败时它会一起带红 14 条）
