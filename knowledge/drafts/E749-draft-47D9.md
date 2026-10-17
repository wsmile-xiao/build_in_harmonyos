# E749 — tool_requires autoconf 把 perl/5.42.2 的 PERL5LIB 灌进构建环境，与 HNP 非线程 perl 混用必炸 `Perl_my_cxt_init: symbol not found`

> Status: DRAFT（Reserved entry id **E749**，`tools/knowledge_id.py --claim --task tclap-1.2.5`）
> Source: tclap 1.2.5 HarmonyOS PC 适配（平台任务 id 14235，2026-09-26，采信轮 R1/R2 实测）
> Related: E540（HNP 路径遮蔽族，另一面）、设备事实 §一.4（harmonybrew 掩盖 CI 缺口）

## 错误特征

```text
# 形态 1（HNP autoreconf 先撞）：conan build() 内 `RUN: autoreconf -fi`
Can't load '/…/.conan2/p/perlbad…/p/lib/perl5/5.42.2/aarch64-linux-thread-multi/auto/Cwd/Cwd.so'
  for module Cwd: Error relocating …/Cwd.so: Perl_my_cxt_init: symbol not found
  at …/5.42.2/XSLoader.pm line 94.
 at …/5.42.2/Cwd.pm line 82.
Compilation failed in require at /data/service/hnp/bin/autoreconf line 48.

# 形态 2（PATH 前置 conan 工具后，仍然同样死在 aclocal）
… at …/autom…/p/bin/.aclocal-real line 31.
.autoreconf-real: error: …/autom…/p/bin/aclocal failed with exit status: 255
ERROR: … Error in build() method … self.run("autoreconf -fi") ConanException: Error 1/255
```

## 触发条件

- 构建系统: autotools（上游 git 树无 `configure`，需要 `autoreconf -fi`）
- 阶段: build() 的 autoreconf/aclocal 环节（configure 之前）
- 两个必要条件同时成立：
  1. 配方 `tool_requires("autoconf/2.72")` —— 它的 `requirements()` 连带 `perl/5.42.2`，
     buildenv 把 **线程版** perl 的 XS 目录（`aarch64-linux-thread-multi`）写进 `PERL5LIB`；
  2. 用 conan 的 `automake/1.18` 提供 `aclocal/automake` —— 其 `.aclocal-real` /
     `.automake-real` 的 shebang **写死** `#!/data/service/hnp/bin/perl`。

## 根因分析

HNP（`/data/service/hnp`）自带 `autoreconf/autoconf/autoheader/autom4te/m4/perl`
（perl 5.42.0，`archname=aarch64-linux`，**非线程**），但**不含** `aclocal/automake`
—— 这正是设备事实 §一.4 要求 `tool_requires("automake/1.18")` 的原因。

conan 侧：`perl/5.42.2` 是 `aarch64-linux-thread-multi`（**线程**）构建。线程版与非线程版
导出的解释器内部符号集合不同（`Perl_my_cxt_init` 是线程版 per-interpreter context 初始化
入口），两者的 XS `.so` **互不兼容**。于是：

1. `tool_requires autoconf/2.72` → buildenv `PERL5LIB` 含 conan perl 的 XS 目录；
2. `.aclocal-real` 由绝对 shebang 交给 **HNP perl**（PATH 前置改不掉绝对 shebang ——
   这是「名字对、实现不对」的第三种形态：**改 PATH 改不了 shebang**）；
3. HNP perl 按 `PERL5LIB` 先找到 conan 的 `Cwd.pm` → 加载 conan 的线程版 `Cwd.so`
   → `Error relocating … Perl_my_cxt_init: symbol not found`；
4. `aclocal` 第 31 行 `use File::Path`（→ `require Cwd`）中止 → `autoreconf` rc=255。

第二面（同时踩到）：OHOS profile 把 `/data/service/hnp/bin` 排在 PATH 最前，HNP 的
`autoreconf` 会遮蔽 conan 提供的同名工具；而设备上 `~/.harmonybrew/bin` 还有
autoconf 2.73 / automake 1.19 —— 不做 PATH 前置就会出现「设备全绿、CI 用 1.18」的
两套判据面（§一.4 同族）。

## 解决方案

### 推荐方案

**不 `tool_requires("autoconf/…")`**，直接用 HNP 的 autoreconf 链；只补 HNP 缺的
automake，并把每条 `self.run` 的环境收窄：

```python
def build_requirements(self):
    # HNP 有 autoreconf/autoconf/autoheader/autom4te/m4/perl；只缺 automake/aclocal
    self.tool_requires("automake/1.18")

def _build_env_prefix(self):
    bins = [os.path.join(d.package_folder, "bin")
            for d in self.dependencies.build.values()]      # = conan automake/bin
    perllib = sorted(glob.glob(os.path.join(pkg, "share", "automake-*")))
    return f'PATH="{":".join(bins)}:$PATH" PERL5LIB="{":".join(perllib)}"'

# 每条命令：
self.run(f'{env_pre} autoreconf -fi', cwd=work)
self.run(f'{env_pre} ./configure CC="{cc}" CXX="{cxx}"', cwd=work)
```

- `PATH` 前置：设备与 CI 都取 conan 的 `aclocal/automake 1.18`（同一判据面），
  `autoreconf/autoconf` 落到 HNP（两边同源）。
- `PERL5LIB` 收窄到 `share/automake-1.18`：`Automake::*` 是纯 perl 模块仍可加载，
  HNP perl 的 `@INC` 保留自己的核心 XS（`Cwd` 等）→ 符号失配消失。

### 禁止做法

- ❌ 保留 `tool_requires autoconf` 再去 `sed` conan 包里的 shebang（改缓存不可复现）。
- ❌ 靠 PATH 前置想「抢过」`.aclocal-real` 的绝对 shebang —— 无效，R1→R2 实测两轮同一行报错。
- ❌ 把 conan perl 的 XS 目录与 HNP perl 混在同一个 `PERL5LIB`（谁先加载谁炸）。
- ❌ 用 `unset PERL5LIB` 了事：那样 conan automake 的 `Automake::Config` 又找不到
   （包内 `@INC` 被 `--prefix=/` 烤成 `//share/automake-1.18`）。

## 验证

```bash
# 复现（应当失败）：线程版 PERL5LIB + HNP 非线程 perl
sh -c 'P=$(ls -d $HOME/.conan2/p/perl*/p/lib/perl5/5.42.2 2>/dev/null | head -1); \
       [ -n "$P" ] && PERL5LIB=$P /data/service/hnp/bin/perl -MCwd -e 1'
# → Error relocating … Cwd.so: Perl_my_cxt_init: symbol not found

# 修复后（应当成功）：收窄 PERL5LIB
sh -c 'unset PERL5LIB; /data/service/hnp/bin/perl -MCwd -e "print qq(ok\n)"'
# → ok
```

tclap 1.2.5 采信轮实测：R1（HNP autoreconf + conan PERL5LIB）红 → R2（PATH 前置但保留
autoconf tool_requires）同签名红 → R3 方案落地后 G2 PASS，`make check` 91/91。

## 关联条目

- 相似: E540（`/data/service/hnp/bin` 在 PATH 的遮蔽与次序问题，另一面）
- 同族: 设备事实 §一.4（harmonybrew 掩盖 CI 缺口）、§一.18（名字对、实现不对）
