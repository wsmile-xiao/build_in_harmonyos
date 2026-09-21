# E598 — 子包 `test_package` 怎么证明「测的就是本子包产物」：链接期符号归属 + 运行期 API 往返 + 交付面 CLI 往返

> Contributor: 474F | Status: Draft | Updated: 2026-09-20
> Source: libfstfar 1.8.4 适配（openfst-1.8.4.tar.gz 的 FAR 子包，积分赛）
> 对应：`knowledge/drafts/DRAFT-E598-subpackage-test-package-consumer-proof.kv`
> 关联：**E596**（同 tarball 子包的 N 清点与 openfst 家族配方形态）——本条只补 `test_package`
> 消费者侧，N 清点与 install shim 部分不重复。

## 现象

同一上游 tarball 派生的子包（`libfstfar` ⊂ openfst、`libgmpxx` ⊂ GMP、`libfstconst` ⊂ openfst……）
有一个共同的**假绿面**：三个包的头文件、README 甚至 `lib/libfst.a` 都一模一样，只有那一个
`libfst<ext>.a/.so` 不同。于是下面三类写法都"看起来测过了"，但都无法证明测的是本子包：

| 写法 | 为什么不算证据 |
|------|----------------|
| 只 `grep` 头文件 / 断言 `bin/` 里有文件 | 头文件与文件名都来自共同 tarball，**兄弟包全都满足**（libfstconst 的 `check_libfstconst.sh` 就是这一类） |
| `self.run("echo …")` / print-only / `pass` | PF3（create-pr 前置硬闸）与 R34 直接拦；CI L1e 还会把被测包换坏做**破坏性反向验证** |
| 编译一个只用**公共头文件**的消费者 | openfst 绝大部分实现是 header-only 模板；把 `libfstfar.a` 删掉照样编译通过、照样跑绿 |

## 根因（三层）

### 第一层：链接期没有"归属证明"

子包的消费者测试若只用到公共头文件里的模板，链接器可以完全不碰本子包的编译单元，
"测试通过"与"本子包产物存在且可用"之间没有因果关系。

**正解**：在本子包的**非头文件编译单元**里找一个强符号，让消费者直接调用它。
判据是该符号只在本子包源码里定义、兄弟包与核心库都没有。

openfst / FAR 例：`fst::IsSTList` / `fst::IsSTTable` 只在
`src/extensions/far/stlist.cc`、`sttable.cc` 里定义（`libfstfar.a` 之外无第二处）。
消费者一调用，链接期就把"有没有链到本子包产物"变成硬事实：

```text
# 破坏性反向验证（把被测包换坏）：
$ clang++ -std=c++17 -stdlib=libc++ -I<pkg>/include consumer.cc -L<pkg>/lib -lfstfar …
ld.lld: error: undefined symbol: fst::IsSTList(std::string_view)
>>> referenced by consumer.cc
```

### 第二层：链接参数缺 `whole-archive` → 注册表空 → `dlopen` 回退假败

openfst 的核心类型注册表用 `REGISTER_FST` 宏（`fst/register.h:119-120`）实现，展开成
文件作用域的 `static FstRegisterer` 静态对象，集中在 `src/lib/fst-types.cc` → `libfst.a`
的 `fst-types.o`。静态链接时链接器**按需取对象文件**，没有强引用就把 `fst-types.o` 剔除：

```text
fst-types.o 被剔除
   → FstRegister<Arc> 表空
   → Fst<Arc>::Read 查不到 reader（fst/fst.h:265-271）
   → GenericRegister::GetEntry 回退 dlopen("<type>-fst.so")（fst/generic-register.h:96-100）
   → 失败，返回 nullptr
   → "Fst::Read: Unknown FST type vector" / 消费者 CHECK 崩
```

修复只有一个形态：

```sh
-lfstfar -Wl,--whole-archive <libdir>/libfst.a -Wl,--no-whole-archive -lm -ldl
```

并且 `shared` / `static` 两种 `options` 都要能跑：动态构建时直接 `-lfstfar -lfst`，
静态构建时才需要 whole-archive；测试脚本按产物扩展名分支，不要写死一种。

### 第三层：声明面（同源子包必查的两条）

| 口径 | 错误形态 | 后果 | 正解 |
|------|----------|------|------|
| `cpp_info.libs` | 只写自己那一个库 `["fstfar"]` | 下游静态链接缺本包 `LIBADD` 里的核心库 | 看 `.la` 的 `LIBADD`：`libfstfar.la` → `../../lib/libfst.la`，故写 `["fstfar", "fst"]`（本包确实交付 `libfst.a`，声明两条既不越界也不遗漏） |
| `runenv_info` 路径 | 无条件 `prepend_path("LD_LIBRARY_PATH", <pkg>/lib/fst)` | 指向不存在的目录 | `lib/fst/` 只在 compact/const/ngram/… 被 `--enable` 时才生成；`package_info()` 里逐目录 `os.path.isdir` 判断后再注入 |

## 方案：消费者验证三件套

### ① 链接期符号归属证明

在 `test_package/<name>.cc` 里直接调用子包独有强符号，并把每一项断言计数打出来：

```cpp
Check(!fst::IsSTList(path),  "IsSTList() symbol lives in stlist.cc");
Check(!fst::IsSTTable(path), "IsSTTable() symbol lives in sttable.cc");
```

### ② 运行期 API 往返（要真正走过注册表路径）

```cpp
// 写：FarWriter<StdArc>::Create(path, FarType::STLIST) → Add("entry1", fst)
// 读：FarReader<StdArc>::Open(path) → Find("entry1") → GetFst() → 比对 states/arcs/start
```

`GetFst()` 内部就是 `Fst<Arc>::Read`，因此这一步同时覆盖了第二层的注册表问题。
（注意 STList 是**顺序**档案：`FarReader::Find()` 对它直接 `LOG(FATAL) "Operation not
supported"`，必须走 `Done`/`GetKey`/`GetFst`/`Next` 顺序迭代；STTable 才支持 `Find`。）

### ③ 交付面 CLI 端到端往返

子包往往还交付一组命令行工具（FAR 交付 9 个 `far*`，核心 `--enable-bin` 另交付 37 个
`fst*`）。这些是"包 install 得对不对"的独有证据面：

```sh
BIN=<pkg>/bin                      # ← 必须用包内绝对路径，不要走 PATH
printf '0 1 1 1 0.25\n1 0.5\n' > in.txt
"$BIN/fstcompile" in.txt in.fst
"$BIN/farcreate" --far_type=stlist --key_prefix=entry_ in.fst out.far
"$BIN/farinfo" out.far | grep -q entry_in
"$BIN/farextract" --keys=entry_in out.far
"$BIN/fstprint" entry_in > printed.txt && diff -u in.txt printed.txt
```

**走 PATH 会命中设备上的同名外部工具 → 测的是设备而不是包**（"设备全绿 ≠ CI 绿"的又一来源）。

### 计数口径

| 行 | 内容 | 本例 |
|----|------|------|
| 上游用例（父 tarball 口径，见 E596） | 注册 7 / 用例分支 10 / 源文件 3 / 断言 185（另一单位，不并入） | N = 10，N′ = 10 |
| 鸿蒙特有测试 | 消费者断言数 + 包内 CLI 检查数 | 14 + 8 = 22 |

两个来源各自输出机器可读标记，便于逐项归因与独立复算：

```text
HMBS_CONSUMER_CHECKS=14 HMBS_CONSUMER_FAILED=0
HMBS_HARMONY_SHELL_CHECKS=8 HMBS_HARMONY_SHELL_FAILED=0
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"check_libfstfar.sh","checks":8,"failed":0}
HMBS_UPSTREAM_TEST_RESULT={"discovered":10,"executed":10,"passed":10,"failed":0,"skipped":0}
```

## 复现

```sh
# 设备可直接执行（TASK_DIR 为任务持久目录，不要用只读的 /tmp）
. "$HOME/tmp/libfstfar-1.8.4/env.sh"
conan create archives/l/libfstfar/1.8.4 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
grep -E 'HMBS_CONSUMER_CHECKS|HMBS_HARMONY_SHELL_CHECKS|HMBS_TEST_PACKAGE_RESULT|HMBS_UPSTREAM_TEST_RESULT' \
  "$TASK_DIR/reports/conan-create.log"
```

## 边界与反例

- 若子包**没有**非头文件的编译单元（纯头文件库），第一件退化为
  `nm`/`readelf -sW` 符号指纹 + `sha256sum`（见 `.kv` 的 `fallback_*`），但必须在 PR 里
  写明降级原因，不能默默省略。
- 若子包产物是**纯可执行文件**（无库），第一、二件合并为"直接用包内绝对路径跑该可执行文件
  并断言其输出"，第三件不变。
- 本条的"三件套"不能替代上游用例清点：N 少报是独立的不通过项，清点口径见 E596。


## 第三件的额外价值：它会抓出「库链得上、工具不能用」的包级缺陷（libfstfar 实测）

只做第一、二件会得到一个**绿色的假结论**。libfstfar 1.8.4 的第一轮采信轮（静态构建）里：

| 件 | 结果 |
|----|------|
| ① 消费者链接 + FAR API 往返（whole-archive） | ✅ 全绿 |
| ② 包内 `far*` CLI 端到端往返 | ❌ `farinfo` 读回 0 个 FST、`farextract` 失败 |
| ③ 上游 10 用例 | ✅ 10/10 |

第二件的原始输出：

```text
$ <pkg>/bin/fstinfo in.fst
ERROR: GenericRegister::GetEntry: Error loading shared library vector-fst.so: No such file or directory
ERROR: Fst::Read: Unknown FST type "vector" (arc type = "standard"): in.fst
$ <pkg>/bin/farcreate --far_type=stlist --key_prefix=entry_ in.fst out.far ; echo rc=$?
rc=0                       # ← 静默成功
$ <pkg>/bin/farinfo out.far
far type  stlist / arc type  error / # of FSTs  0
$ ls -la out.far
-rw-rw---- 1 ... 12 out.far      # 只有 magic + version 的空档案
```

根因与第二层同源，但受害者换成了**交付给用户的二进制**：`--disable-shared` 静态链接时
`fst-types.o`（只含文件作用域 `static FstRegisterer`）被链接器按需取对象文件时整块剔除，
`FstRegister` 表为空。机械判据：

```sh
llvm-nm -C <pkg>/bin/fstinfo | grep -c FstRegisterer     # 静态构建 = 0
llvm-nm -C <pkg>/lib/libfst.a | grep -c FstRegisterer    # 库内 = 72
```

**修法**（按推荐顺序）：

1. **默认库形态改成 shared**（上游 `./configure` 不带 `--disable-shared` 时的默认）：
   动态库整库加载即执行全部静态注册器，`fstinfo` 立刻能报出 `fst type vector / 2 states`。
2. 必须静态时，**交付的二进制也要用 `-Wl,--whole-archive <libfst.a>` 重链**（只给测试程序加是不够的）。
3. 交付的二进制还要打 `$ORIGIN/../lib` 可重定位 rpath：libtool 不自动加 rpath，缺了它在
   裸 PATH / 无 `LD_LIBRARY_PATH` 的环境里加载器找不到同包的 `libfst.so.26`
   （CI 的 L2 smoke 正是裸 PATH 执行；用户把包目录整体拷走也要能直接跑）。
   ⚠ **注入 rpath 的判据必须只看那一行 `LDFLAGS`**，不能看整个 Makefile 是否出现
   `-rpath`——automake 生成的 Makefile 天然含 `am_libfst<ext>_la_rpath = -rpath $(libdir)`
   这类无关变量（`src/extensions/far/Makefile` 3 处），按整文件判断会**整文件跳过**：
   `bin/fst*`（`src/bin/Makefile`）拿到 rpath、`bin/far*`（`src/extensions/far/Makefile`）
   没有 → 前者裸跑 OK、后者 `rc=127 Error loading shared library libfstfarscript.so.26`，
   而 `test_package` 跑在 `conanrun`（有 `LD_LIBRARY_PATH`）里**完全掩盖**这个不一致，
   只有 CI 的 L2 裸 PATH smoke 会漏出 9 条 warn。首轮 W4 审计正是据此判 P1
   （"交付面声明与所引证据相反"）。判据：
   `for b in fstinfo farinfo; do llvm-readelf -d <pkg>/bin/$b | grep RUNPATH; done`。

**推广**：任何「用文件作用域静态对象做注册表」的 C++ 库——`REGISTER_*` 宏、`static Registrar`、
自注册工厂——在 `--disable-shared` 下都有这个面。判据统一：`nm` 数交付二进制里的注册器符号，
为 0 就是被剥离了；受害者按"谁读注册表"排序，通常是命令行工具与插件加载路径。
