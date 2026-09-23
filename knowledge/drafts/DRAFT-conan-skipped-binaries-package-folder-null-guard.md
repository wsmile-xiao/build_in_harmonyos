# DRAFT-conan-skipped-binaries-package-folder-null-guard — Conan 2 Skipped binaries（package_folder=None）依赖循环判空守卫

> **Contributor**: GoliWie | **Status**: DRAFT | **Updated**: 2026-09-03
> **Severity**: blocking (2) | **Category**: conan / graph / recipe-guard
> **Audience**: 所有迭代 `self.dependencies` 并解引用 `dep.package_folder` 的 Conan 配方作者与移植 Builder

## 触发（trigger）

- 消费图存在 **SHARED×STATIC 结构**：shared 库（glib/2.84.0.1，default_options
  shared=True）把 static 子依赖（pcre2/10.45、libffi/3.4.4，shared=False）静态链入自身；
  这类 require 向下游传播时 `libs=False`——下游消费图不再需要 STATIC 子依赖的二进制。
- 该 shared 库的二进制来自 **Cache/Download**（不参与本次构建）：Conan 2 不展开
  Cache/Download 节点，其 STATIC 子依赖被标记 **Skipped binaries**——节点仍在图中
  （`cpp_info` 可见、`self.dependencies` 可遍历），但 `binary=Skip`、`package_folder=None`。
- 配方在 `generate()`/`build()` 遍历 `self.dependencies.values()` 并直接
  `os.path.join(dep.package_folder, ...)` 或解引用 `dep.cpp_info`。
- 本库实例的进入路径：granite-6.2.0 消费图顶层 force 统一 glib/2.84.0→2.84.0.1
  （版本 pin 冲突的解法），glib 二进制为 Cache，pcre2/libffi/xz/graphite2 被 Skip。

## 症状（symptom）

conan create/install 在 generate()/build() 阶段硬崩，granite 消费图日志原文：

```
Skipped binaries
    graphite2/1.3.14, libffi/3.4.4, pcre2/10.45, xz/5.6.2
...
ERROR: libgee/0.20.8: Error in generate() method, line 62
	pkg_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
	TypeError: expected str, bytes or os.PathLike object, not NoneType
```

跨 run 佐证：runs/granite-6.2.0/logs/ci-run2.log:241/:279、ci-run3.log:258。

## 机制（root cause）

Conan 2.29.1 实测（自包含探针见下节）：**SHARED×STATIC + 中间 SHARED 节点 Cache**
三个条件同时满足时，STATIC 子节点 `binary=Skip`、`package_folder=None`。诊断入口：
日志见 `TypeError ... NoneType` 先查 `Skipped binaries`，再对配方**全部**依赖循环逐一
检查判空——漏一处即崩（libgee/0.20.8 三处循环均未设防，granite 消费图命中即崩）。

**机理修正**（本轮以 conan 缓存配方与自包含探针实证，替代本草稿初稿表述）：
glib/2.84.0.1 配方仍声明 `requires("pcre2/10.45")`/`requires("libffi/3.4.4")`，
pcre2/libffi **并非被 vendor 移除**，失效面是 shared×static 图语义；"无缓存全新环境
必崩"亦不成立——全新环境全链 Build 时，Build 节点会展开其直接依赖（required、有真实
package_folder），不产生 Skip；触发需要中间 shared 库二进制处于 Cache/Download
（force 统一 glib 版本只是本例把 libgee 带入这种消费图的进入路径）。

## 修复（rec）

配方中**每一处**依赖循环的 for 行后插入守卫（generate() 与 build() 全数设防）：

```python
for dep in self.dependencies.values():
    # SHARED 库（glib）的 STATIC 子依赖（pcre2/libffi）在消费图被标记
    # Skipped binaries：package_folder=None，必须跳过，否则 generate()
    # / build() 直接 TypeError 崩溃（granite-6.2.0 run 实测）
    if not dep.package_folder:
        continue
    # ...原有循环体...
```

- libgee/0.20.8.1 落位三处：conanfile.py:57（generate() cflags/ldflags 循环）、
  :69（generate() PKG_CONFIG_PATH/PATH/LD_LIBRARY_PATH 循环）、:112（build() .la 清理循环）。
- 守卫对正常依赖（package_folder 非空）零行为变化；最小插入、0 删改。

## 退路（fallback）

配方不可改时：消费方构建命令强制失效面 SHARED 中间节点参与本次构建——
`conan create <consumer-dir> --build=missing --build='skipmid/*'`。Build 节点会展开其
直接依赖，STATIC 子依赖被 require、不再被 Skipped，未守卫循环因此不崩（探针 P5 实测）。
诚实权衡：**治标不治本**——仅消除本次图的 Skip 条件，不修复配方健壮性缺陷，任一后续
图中该库二进制回到 Cache 即复发；全链重建显著拉长构建时间。仅作监控/应急退路，
配方可改时必须用判空守卫。

## 反模式（forbid）

1. 循环体内直接 `os.path.join(dep.package_folder` 而循环 for 行后无判空——任何一处
   未设防都会在含 Skip 节点的消费图 TypeError 崩溃（granite ci-run2/ci-run3 实测）。
2. 用升级依赖 pin 或删掉传递依赖遍历来"回避"崩溃——前者引入新传递依赖、改变全图
   语义，后者丢功能；都不消除配方健壮性缺陷，下一个 STATIC 子依赖出现时原样复发。

## 原则挂靠（principles）

- **P-BUILD-001**（平台限制必须降级而非绕过）：构建图级语义差异（Skipped binaries）
  与 FIFO/SELinux 类平台限制同理，是工具链/平台级行为，不因重试而改变；判空
  `continue` 即"降级到可用方案"（跳过无产物的节点），而非忽略错误继续或绕过图语义。

## 自包含复现探针（设备 conan 2.29.1 实测跑通）

需要 `sh` + `conan 2.x` + `python3`（设备 PATH 无 python3 时脚本自动回退到用户
python3 绝对路径），任意新 shell、任意空目录可跑。以下脚本一字未改实测通过：

```sh
#!/bin/sh
# Conan 2 "Skipped binaries" => dep.package_folder=None => unguarded loop TypeError.
# Mechanism: SHARED lib (shared=True) statically links a STATIC dep; when the
# shared lib binary is Cache (not built here), Conan marks the static child
# "Skipped binaries" (binary=Skip, package_folder=None).
set -eu
PY="$(command -v python3 || echo /storage/Users/currentUser/usr/local/bin/python3)"
ROOT="$(mktemp -d)"
mkdir -p "$ROOT/leaf" "$ROOT/mid" "$ROOT/bad" "$ROOT/good"

make_lib() {
    d="$1"; n="$2"; sh_opt="$3"
    cat > "$ROOT/$d/conanfile.py" <<EOF
from conan import ConanFile
class P(ConanFile):
    name = "$n"
    version = "1.0"
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": $sh_opt}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
EOF
}

make_lib leaf skipleaf False
make_lib mid  skipmid  True
make_lib bad  skipbad  True
make_lib good skipgood True

cat >> "$ROOT/mid/conanfile.py" <<'EOF'

    def requirements(self):
        self.requires("skipleaf/1.0")
EOF

cat >> "$ROOT/bad/conanfile.py" <<'EOF'

    def requirements(self):
        self.requires("skipmid/1.0")

    def generate(self):
        # libgee/0.20.8 style: join package_folder unguarded
        import os.path
        for dep in self.dependencies.values():
            self.output.info("LOOP: ref=" + str(dep.ref) + " pkg_folder=" + str(dep.package_folder))
            os.path.join(dep.package_folder, "lib", "pkgconfig")
EOF

cat >> "$ROOT/good/conanfile.py" <<'EOF'

    def requirements(self):
        self.requires("skipmid/1.0")

    def generate(self):
        # libgee/0.20.8.1 style: null guard skips Skipped binaries
        import os.path
        for dep in self.dependencies.values():
            if not dep.package_folder:
                self.output.info("GUARD-SKIP: " + str(dep.ref) + " package_folder=None")
                continue
            self.output.info("LOOP: " + str(dep.ref) + " -> " + os.path.join(dep.package_folder, "lib", "pkgconfig"))
EOF

export CONAN_HOME="$ROOT/conan-home"
mkdir -p "$CONAN_HOME/profiles"
cat > "$CONAN_HOME/profiles/default" <<'EOF'
[settings]
os=Linux
arch=armv8
compiler=clang
compiler.version=15
compiler.libcxx=libc++
build_type=Release
EOF

echo "=== P1: create leaf (static) + mid (shared); binaries land in cache ==="
conan create "$ROOT/leaf" >/dev/null && echo "skipleaf/1.0 created (static)"
conan create "$ROOT/mid" >/dev/null && echo "skipmid/1.0 created (shared)"

echo "=== P2: UNGUARDED consumer graph: Skip node has package_folder None ==="
conan graph info "$ROOT/bad" --format=json | "$PY" -c "
import json, sys
for n in json.load(sys.stdin)['graph']['nodes'].values():
    if n.get('ref'):
        print('node:', n.get('ref'), '| binary:', n.get('binary'), '| package_folder:', n.get('package_folder'))
"

echo "=== P3: create UNGUARDED consumer: real TypeError in generate() ==="
conan create "$ROOT/bad" > "$ROOT/bad.log" 2>&1 || true
grep -n -A1 'Skipped binaries' "$ROOT/bad.log" || true
grep -n 'LOOP:' "$ROOT/bad.log" | tail -2 || true
grep -n 'TypeError' "$ROOT/bad.log" | tail -1 || true

echo "=== P4: GUARDED consumer: guard skips Skip node, build succeeds ==="
conan create "$ROOT/good" > "$ROOT/good.log" 2>&1 || true
grep -n 'GUARD-SKIP' "$ROOT/good.log" || true
grep -c 'TypeError' "$ROOT/good.log" || true

echo "=== P5: fallback: force mid rebuild => no Skip => unguarded loop survives ==="
conan create "$ROOT/bad" --build=missing --build='skipmid/*' > "$ROOT/fb.log" 2>&1 || true
grep -c 'Skipped binaries' "$ROOT/fb.log" || echo "no Skipped binaries section"
grep -n 'LOOP:' "$ROOT/fb.log" | tail -2 || true

echo "=== P6: crash primitive ==="
"$PY" -c "import os.path; os.path.join(None, 'lib')" 2>&1 | tail -1 || true

echo "PROBE-DONE"
```

实测关键输出（设备 conan 2.29.1，与上脚本步骤一一对应）：

```
=== P2 ===
node: skipmid/1.0#7a7e9841b47c5e205788121e6e6ed87c | binary: Cache | package_folder: None
node: skipleaf/1.0#3a403b8e3a5c0018b6168201e1a38f0c | binary: Skip | package_folder: None
=== P3 ===
41:Skipped binaries
42-    skipleaf/1.0
57:skipbad/1.0: LOOP: ref=skipleaf/1.0 pkg_folder=None
60:	TypeError: expected str, bytes or os.PathLike object, not NoneType
=== P4 ===
57:skipgood/1.0: GUARD-SKIP: skipleaf/1.0 package_folder=None
0                                    # TypeError 计数为 0，create 成功
=== P5 ===
no Skipped binaries section          # Skip 计数为 0
76:skipbad/1.0: LOOP: ref=skipleaf/1.0 pkg_folder=/…/conan-home/p/b/skipl…/p   # 真实路径，未守卫循环存活
=== P6 ===
TypeError: expected str, bytes or os.PathLike object, not NoneType
```

注：探针用手写最小 profile（配方自带 options，无需编译器探测；`conan profile detect`
在本设备新 shell 会因 PATH 无 cc/clang++ 失败——E405 posix_spawn 同族现象，作为探针
的实现注意点记录，非本条机理组成部分）。

## 查重（dedup）

按 curation-policy 对 knowledge/graph（E001–E542 + index.tsv + pre-scan-rules.yaml）、
knowledge/drafts（本分支全列表 + feat/granite-6.2.0 分支全部 DRAFT）、经验仓 ophs_ci_review、
配方树 archives/ 检索（`package_folder|skip.*binar|skipped|vendor|TypeError` 等）：

1. `package_folder` graph 命中 20 条（E221/E241/E297/E323/E340/E362/E384/E389/E395/
   E396/E423/E428/E443/E448/E451/E473/E487/E489/E498/E511）：逐项核对均为"使用
   package_folder 路径"（注入/拷贝/工具定位），无一遍历判空跳过 Skipped。最近邻两个：
   - E396（package_folder null）：证据校验层——graph info JSON 字段合法为 null、以
     install JSON 身份绑定定 materialization；症状层（证据 schema vs 配方 TypeError 崩溃）
     与修法（文档 join vs 循环守卫）均不同，不覆盖。
   - E473：`if webp.package_folder:` 单一具名依赖在 cmake build-module 注入处的防御
     条件——无遍历、无 Skipped 语义、无 TypeError 诊断，形似不覆盖。
2. `Skipped binaries`：graph 0 条；drafts 仅 DRAFT-conan-shared-pkgconfig-requires-drop
   （audacious run，baseline 分支）。该草稿把 Skipped 机制讲到 conan 源码层
   （transform_downstream / get_transitive_requires / pkgconfigdeps），但失效面 =
   PkgConfigDeps 生成 .pc 的 Requires 链静默截断（生成器侧、无告警），修法 =
   transitive_headers/提直接依赖；本条失效面 = 配方 build 期 TypeError 硬崩，修法 =
   判空 continue。同一 conan 语义的两个独立后果面，互补不重叠，**交叉引用**。
3. `TypeError` graph 仅 E226（设备 Python3.12 os.popen str/bytes）——无关。
4. feat/granite-6.2.0 分支 3 对 DRAFT（meson vala os define / conanbuild
   LD_LIBRARY_PATH / vala vapi discovery）机制零重叠；且只存在于该分支未合入本分支，
   无交付冲突、无共享文件。
5. 经验仓 ophs_ci_review：0 命中。
6. 配方树既有实践：`grep -rl 'if not dep.package_folder' archives/` 本 run 复验命中
   10 文件（Curator 记 8 处核心清单：cairo-gobject/1.18.4.1 与 1.18.4.2 conanfile.py:206、
   ice/3.8.2、abiword-plugin-openwriter/3.0.8、aws-c-auth/0.10.4、aws-c-http/0.11.0、
   captagent/6.4.4、ekg2/0.3.1；复验另证实 s3transfer/0.19.2 test_package:25、
   simple-tiles/0.6.2 conanfile.py:90/201 同款）。**定位：模式已被配方树多个已发布
   配方实践，知识库首次知识化为问题类条目（非首创）。**

## 证据（evidence）

验证链三段（跨 run 证据按 run 相对路径标注）：

1. **机理探针**（自包含、conan 2.29.1 实测）：上节 P2–P6——Skip 节点
   `package_folder=None`、未守卫循环真实 TypeError、守卫存活、`--build` 强制重建消除
   Skip，四点闭环。
2. **崩溃路径**（无守卫配方 + glib Cache 消费图）：granite-6.2.0 run
   runs/granite-6.2.0/logs/ci-run2.log:241（Skipped binaries）、:279（TypeError）、
   ci-run3.log:258。
3. **正式修复**（守卫随配方全新源码构建）：run libgee-0.20.8.1 ci-run1——0.20.8.1 无
   任何缓存/远端二进制，conan 全新源码构建 PASS：
   runs/libgee-0.20.8.1/logs/ci-run1.log:174（Building from source）、:418（make check
   -j1 真实执行）、:1090（gtester PASS: tests）、:1912-1916（L0 pass/L1 pass/L2 skip
   合法/L4 warn 不失败/L5 pass）。

**诚实边界**：libgee 本 run 独立图全链 Build（glib 为 Build 节点、pcre2/libffi 被
require、有真实 package_folder），守卫在本 run CI 为**防御性执行**——这正是机理修正
的结论：全新全链构建不触发 Skip，崩溃需要"SHARED×STATIC + 中间节点 Cache"的消费图
（granite 实例）。崩溃路径的回归实证在 granite run ci-run2/ci-run3（无守卫 0.20.8
配方）。"自身 CI 过 ≠ 消费图安全"是本条的核心教训。

## 关系

- principles: P-BUILD-001（平台/工具链级限制降级而非绕过；判空跳过 = 降级到可用方案）。
- similar_to: E396（graph info package_folder=null 语义层）、E473（单一具名依赖判空
  防御）——差异见查重节。
- 交叉引用：DRAFT-conan-shared-pkgconfig-requires-drop（同一 Skipped 机制的
  PkgConfigDeps 失效面，互补条目）。
- prerequisite_of: 无；conflicts_with: 无。
