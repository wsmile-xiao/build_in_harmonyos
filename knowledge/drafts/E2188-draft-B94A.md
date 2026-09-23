# DRAFT: 发布版包 package_id 不编码 PIC 状态——同一 package_id 下 zlib 的 PIC 与非 PIC 变体可共存（bambamc 0.0.50 实测）

## 错误特征

`configure`、`make` 全部通过，但链接**共享库**时报：

```
ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'; recompile with -fPIC
>>> defined in /storage/Users/currentUser/.conan2/p/zlib56af09fbb4346/p/lib/libz.a(zutil.o)
>>> referenced by zutil.c
>>>               zutil.o:(zError) in archive /storage/Users/currentUser/.conan2/p/zlib56af09fbb4346/p/lib/libz.a

ld.lld: error: relocation R_AARCH64_ADD_ABS_LO12_NC cannot be used against symbol 'z_errmsg'; recompile with -fPIC
```

文案是 `recompile with -fPIC`，指向「重新编译」，很容易误判为**本项目**没传 `-fPIC`。
实测本项目对象早已是 `-fPIC`（libtool 编译行含 `-fPIC -DPIC`），报错对象在**依赖**的归档里。

## 触发条件

- 构建系统：autotools / cmake / 任意把「依赖的静态库」吸收进 `.so`、插件、Python 扩展或
  `dlopen` 场景的构建系统
- 阶段：linking
- 平台：OHOS aarch64（`R_AARCH64_ADR_PREL_PG_HI21` 是 aarch64 专用形态）
- 依赖条件：同一远程上存在多个 ref，`package_id` 重合而编包口径（CFLAGS）不同

## 根因分析

1. PIC 是**构建期 CFLAGS** 的属性（`-fPIC`），而 Conan 的 `package_id` 只由
   settings + options + requires 计算，**不包含 CFLAGS**。因此同一 `package_id` 下可以存在
   PIC 与非 PIC 两种二进制；远程不会报版本冲突，也不会产生 hash 不匹配。
2. 本仓 zlib 的三种 ref 恰好构成这个形态（设备实测，2026-09-11，OHOS armv8 profile）：

   | ref | 配方是否注入 `-fPIC` | `libz.a` 成员 `zutil.o` 对 `z_errmsg` 的重定位 | 吸收进 `.so` |
   | --- | --- | --- | --- |
   | `zlib/1.3.1` | **否** | `R_AARCH64_ADR_PREL_PG_HI21` + `R_AARCH64_ADD_ABS_LO12_NC` | **失败**（ld.lld 拒绝） |
   | `zlib/1.3.1.1` | 是（`CFLAGS="-fPIC -O2"`） | `R_AARCH64_ADR_GOT_PAGE` + `R_AARCH64_LD64_GOT_LO12_NC` | 成功 |
   | `zlib/1.3.2` | 是（`CFLAGS="-fPIC -O2"`） | `R_AARCH64_ADR_GOT_PAGE` + `R_AARCH64_LD64_GOT_LO12_NC` | 成功 |

   三者在本 profile 下的 `package_id` **完全相同**：`6b129b068851896169fae42d399fa922d239ce8a`
   （package revision 不同：`7ec24a23…` / `b27d5a8c…` / `fbb0afb3…`，但消费方按 ref 解析时
    `package_id` 无法区分可链接性）。

   本仓配方自身已经写明这一点：`archives/z/zlib/1.3.1.1/conanfile.py` 与 `1.3.2/conanfile.py`
   的 docstring 均写着「区别于远端 zlib：远端 `./configure --static` 不加 -fPIC，libz.a 非 PIC，
   链进共享库（如 libcairo.so）会报 R_AARCH64 relocation」——即**修的是编包侧**，但
   `package_id` 没有随之变化，消费侧仍然无法靠 `package_id` 判断。
3. aarch64 上非 PIC 的全局数据寻址在共享对象里无解（页相对重定位无法在加载期确定），
   故 lld 硬失败；可执行文件不受影响，所以「编译成功 + 测试套件全绿」与本错误并不矛盾。

## 真实证据（bambamc 0.0.50，2026-09-11 设备实测）

### 1. 用 `conan cache path` 精确解析每个 ref 的包目录（不要用 `ls | head -1` 通配）

```sh
PID=6b129b068851896169fae42d399fa922d239ce8a
for ref in zlib/1.3.1 zlib/1.3.1.1 zlib/1.3.2; do
  echo "$ref -> $(conan cache path "$ref:$PID")"
done
# zlib/1.3.1   -> .../.conan2/p/zlib56af09fbb4346/p
# zlib/1.3.1.1 -> .../.conan2/p/zlibef5df15a693be/p
# zlib/1.3.2   -> .../.conan2/p/zlibadde02423c9a0/p
```

> 用 `ls -d ~/.conan2/p/zlib*/p | head -1` 之类的通配会把**别的** zlib ref 当成目标，
> 从而得出方向相反的结论（本任务第一轮即踩此坑）。必须用 `conan cache path <ref>:<pid>`。

### 2. 归档成员级判据（决定性证据）

```sh
for ref in zlib/1.3.1 zlib/1.3.1.1 zlib/1.3.2; do
  P=$(conan cache path "$ref:$PID")
  ar p "$P/lib/libz.a" zutil.o > "/tmp/$(echo $ref | tr / _).o" 2>/dev/null || \
    ar p "$P/lib/libz.a" zutil.o > "./$(echo $ref | tr / _).o"
  echo "--- $ref"; readelf -r "./$(echo $ref | tr / _).o" | grep -A1 z_errmsg
done
# zlib/1.3.1   : R_AARCH64_ADR_PREL_PG_HI21 / R_AARCH64_ADD_ABS_LO12_NC   <- 非 PIC
# zlib/1.3.1.1 : R_AARCH64_ADR_GOT_PAGE    / R_AARCH64_LD64_GOT_LO12_NC   <- PIC
# zlib/1.3.2   : R_AARCH64_ADR_GOT_PAGE    / R_AARCH64_LD64_GOT_LO12_NC   <- PIC
```

### 3. 链接期反证（与项目无关的最小探针）

```c
/* t.c */
#include <zlib.h>
const char *probe(void){ zError(1); return zlibVersion(); }
```

```sh
SR=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot
for ref in zlib/1.3.1 zlib/1.3.1.1 zlib/1.3.2; do
  P=$(conan cache path "$ref:$PID")
  clang -shared -fPIC t.c -I"$P/include" -L"$P/lib" -lz \
    --target=aarch64-unknown-linux-ohos --sysroot=$SR -o "$(echo $ref | tr / _).so"
  echo "$ref rc=$?"
done
# zlib/1.3.1   rc=1   ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'; recompile with -fPIC
# zlib/1.3.1.1 rc=0
# zlib/1.3.2   rc=0
```

### 4. `package_id` 相同的证据

```sh
for ref in zlib/1.3.1 zlib/1.3.1.1 zlib/1.3.2; do
  conan install --requires="$ref" -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> --build=never -of <scratch> \
    | grep -E "^    $ref"
done
# zlib/1.3.1#2ee7c0eeb8f4dfef8982d0c5c1551a61:6b129b068851896169fae42d399fa922d239ce8a#7ec24a23f2d13bf0a3658deb250d2777
# zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9:6b129b068851896169fae42d399fa922d239ce8a#b27d5a8c4c5eafd64d3a7f1e7a12dceb
# zlib/1.3.2#73f9291bbbf6587c1b453f541f5debf7:6b129b068851896169fae42d399fa922d239ce8a#fbb0afb34d16643c8b06ef23a0d003a4
```

三个 `package_id` 均为 `6b129b068851896169fae42d399fa922d239ce8a`。
**「package_id 相同」不能推出「可链接性相同」。**

### 5. 包级/门禁侧后果

若本包按 `shared=False` 只产出 `.a`，`conan create` **不会**碰到这条错误（可执行文件允许非 PIC
重定位），`test_package` 与 `conan-verify` 全绿、上游测试 2/2 通过，缺陷被推迟到**下一个**
把它链进 `.so`/插件/Python 扩展的消费者。

## 解决方案

### 推荐方案

配方 `requirements()` 钉住**经归档成员探测确认 PIC** 的 ref：

```python
def requirements(self):
    # zlib/1.3.1 / 1.3.1.1 / 1.3.2 在本仓远程解析出同一个 package_id
    # (6b129b068851896169fae42d399fa922d239ce8a)，但 1.3.1 的 libz.a 不是 PIC
    # (zutil.o 对 z_errmsg 用 R_AARCH64_ADR_PREL_PG_HI21)，吸收进共享对象会被 ld.lld 拒绝；
    # 1.3.1.1 与 1.3.2 均注入 CFLAGS="-fPIC -O2"，是 PIC 变体。
    self.requires("zlib/1.3.1.1")
```

选版流程（**先探测再选**，不要看 package_id 或版本号）：

```sh
PID=$(conan graph info --requires=zlib/<ver> -pr:h="$HOST_PROFILE" -pr:b="$HOST_PROFILE" \
        --format=json | python3 -c "import json,sys;print(json.load(sys.stdin)['graph']['nodes']['1']['package_id'])")
P=$(conan cache path "zlib/<ver>:$PID")
for o in $(ar t "$P/lib/libz.a"); do
  ar p "$P/lib/libz.a" "$o" > /tmp/probe.o
  readelf -r /tmp/probe.o | grep -qE 'ADR_PREL_PG_HI21|ADD_ABS_LO12_NC' && echo "NON-PIC: $o"
done
# 取无 NON-PIC 输出的 ref 写进 requirements()
```

验收（本任务实测）：

```sh
clang -shared -fPIC probe.c -I"$PKG/include" -I"$Z1311/include" \
  -L"$PKG/lib" -lbambamc -L"$Z1311/lib" -lz \
  --target=aarch64-unknown-linux-ohos --sysroot=$SR -o libbambamc_probe.so    # rc=0
./driver ./libbambamc_probe.so
# -> dlopen probe: bambamc_probe_ok() = 1   rc=0
readelf -d libbambamc_probe.so | grep NEEDED   # 只有 libc.so（libbambamc 与 zlib 对象均被吸收）
```

### 回退方案

远程不存在任何 PIC 变体时，就地自建并把 `-fPIC` 注入上游构建，产出到任务私有 prefix：

```sh
conan create . -o "zlib/*:shared=False" --build=zlib/* \
  --conf 'tools.build:cflags=["-fPIC"]'
```

### 禁止做法

- ❌ **`-Wl,--exclude-libs,ALL` / `-Wl,-Bsymbolic` 压过报错**：设备实测两者都能让链接 rc=0，
  但吸收进来的仍是带非 PIC 重定位的对象，符号被本地化后与真正 PIC 构建产物不等价，
  等于把缺陷放行给下游。
- ❌ **只看 `conan list` 的 package_id 或版本号新旧选变体**：pid 不含 CFLAGS，实测三个 ref
  pid 全同，选版结论与可链接性无关。
- ❌ **用通配符猜包目录**（`ls -d ~/.conan2/p/zlib*/p | head -1`）：会把别的 ref 当成目标，
  得出**方向相反**的结论。必须用 `conan cache path <ref>:<pid>` 精确解析。
- ❌ **给本项目加 `-fPIC` 了事**：本项目对象早已是 `-fPIC`，报错对象在依赖侧。

## 验证

```sh
# 项目侧对象无不安全重定位（证明问题不在本项目）
readelf -r <build>/src/.libs/libbambamc_la-*.o | grep -c R_AARCH64_ADR_PREL_PG_HI21   # -> 0

# 依赖侧：三 ref 的成员判据 + 链接探针（见上文 §2/§3）

# 端到端
conan create archives/b/bambamc/0.0.50 --user=ohpcd --channel=stable -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>
# G2 PASS；reports/conan-create.log 含 RUN: autoreconf / Apply patch ×2 / RUN: make -j1
# test_package: bambamc consumer round-trip: 28 checks, 0 failures
# reports/conan-verify-supplement.md 记录 G4/L2/L4/L5 人工补测
```

## 查重差异（与既有条目的可执行反证）

- **E005（add-cflags，linking）**：只覆盖「**本项目**静态库编译时未加 `-fPIC`」。本条目被报错的
  对象在**依赖**的归档里，且本项目 `-fPIC` 已生效。反证：本项目对象
  `readelf -r ... | grep -c ADR_PREL_PG_HI21` → `0`，而报错仍指向
  `p/zlib56af09fbb4346/p/lib/libz.a(zutil.o)`。
- **E234（静态 Autotools 库的 Conan fPIC 映射）**：讨论 `--with-pic` 与 Conan `fPIC` 选项冲突，
  属「本项目选项传递」问题；本条目不涉及 `--with-pic`，也不涉及 configure 失败。
- **E539 / E541（zlib test_package PIC 探针 / zlib 应 static-only 但用 PIC 对象）**：结论落在
  **编包侧**「zlib 自身要产 PIC 归档」；本条目是**消费侧**「在一个 `package_id` 无法区分 PIC 的
  远程上如何选对变体」，并给出归档成员级判定命令与三 ref 对照。三者互补。
  差异段实测反证：本仓 `zlib/1.3.1`、`1.3.1.1`、`1.3.2` 三个 ref 的 `package_id` **完全相同**
  （`6b129b06…`）而 PIC 状态不同——这一点 E539/E541 正文未覆盖；它们描述的是「1.3.1.1/1.3.2
  修好了编包」，但消费侧仍无法用 `package_id` 区分。
- **E533（libarchive 3.7.7 适配）**：其 error_signature 里出现过
  `R_AARCH64_ADR_PREL_PG_HI21.*z_errmsg` 字样，但结论落在 libarchive 的 configure/umask
  与依赖边界上，未形成「pid 不编码 PIC → 选版判据」这一可复用模式。
- 结论：新增（路径 B），与本任务同 PR。
