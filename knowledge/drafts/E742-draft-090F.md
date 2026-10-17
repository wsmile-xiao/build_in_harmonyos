# E742 — 零测试 autotools 解码库：测试面重建（最小合法输入合成 + 演示程序端到端断言）与 libtool 引导链

> 任务：libsmacker 1.1.1r35（分支 `feat/libsmacker-1.1.1r35`）｜草稿号 E742（`knowledge_id.py --claim` 三面回查）
> 状态：Draft，待人工/主编审核后转 `knowledge/graph/E742.kv` + `doc/E742.md` + `index.tsv`

## 错误特征

三段式，任一命中即可关联到本条：

1. 引导失败
   ```
   autoreconf: running: autoconf --force
   configure.ac:8: error: undefined or overquoted macro: AC_PROG_LIBTOOL
   ```
2. HMDFS 拦路
   ```
   ./config.guess[1612]: can't create .../dummy.c: Permission denied
   ./config.guess: unable to guess system type
   ./config.status[956]: can't create ./confPepfCp/subs1.awk: Permission denied
   config.status: error: could not setup config files machinery
   ```
3. 测试面为空
   ```
   $ make -n check
   make: Nothing to be done for 'check'.
   ```

## 触发条件

- 构建系统：autotools，**发行 tarball 不含 `configure`**（只有 `configure.ac` + `Makefile.am`）
- `configure.ac` 用已废弃的 `AC_PROG_LIBTOOL`（需要 `libtoolize` 提供 `m4/libtool.m4` + `ltmain.sh`）
- 目标：HarmonyOS PC / aarch64（HMDFS，`uname -s = HarmonyOS`）
- 上游**没有 `tests/`**，`Makefile.am` 没有 `TESTS` / `check_PROGRAMS`，只带 `noinst_PROGRAMS` 演示程序

## 根因分析

1. **引导链缺件**：`~/.harmonybrew/bin` 有 automake，但它**不在 CI worker 的 PATH 上**
   （device-facts §一.4「harmonybrew PATH 掩盖 CI 缺口」——设备全绿 ≠ CI 会绿）。
   `aclocal`/`automake`/`libtoolize` 三件在 worker 上都不存在，只有 `/data/service/hnp/bin`
   的 autoconf 家族。
2. **config.guess 在 HMDFS 上两头堵**：`uname -s` 返回 `HarmonyOS` 不在它的表里，而它的编译探针
   还要写临时目录，HMDFS 拒绝写 ⇒ `unable to guess system type`。
3. **`umask 077 && mktemp -d` 生成 `drwx--S---`**：HMDFS 把属主映射成共享属主（20001006），
   进程自己的 euid 是另一个号 ⇒ 目录**连创建者都写不进** ⇒ `config.status` 第一步
   `>"$ac_tmp/subs1.awk"` 就 Permission denied。
4. **测试面为 0 不等于可以空跑**：`driver.c` 是演示程序——打开失败 `return -1`，成功路径
   无条件 `return 0`，中间只 `printf` 与写 BMP，零断言。把它跑一遍不产生任何判据。

## 解决方案

### 推荐方案（四步）

1. **补齐引导链**（build profile 解析，故 `-pr:h` 与 `-pr:b` 都要传）：
   ```python
   def build_requirements(self):
       self.tool_requires("automake/1.18")
       self.tool_requires("libtool/2.5.4")
   ```
   ohpcd 制品仓两者均已发布；**不要** `tool_requires("autoconf")`——conan 的
   `autoconf/2.72` 会经 `PERL5LIB` 毒杀 HNP 自带 perl（device-facts §一.23）。
   另加 `_prepare_autotools_env()`，把 `AUTOCONF/AUTOHEADER/AUTOM4TE/SED` 指向 PATH 上真实存在的文件。

2. **绕过 config.guess、归一 umask**（都在 `build()` 内，不动上游 tarball、不进补丁面）：
   ```python
   tc.configure_args += ["--build=aarch64-unknown-linux-ohos",
                         "--host=aarch64-unknown-linux-ohos",
                         "--enable-static", "--disable-shared"]
   self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
   # configure 内两处：
   #   tmp=`(umask 077 && mktemp -d "./confXXXXXX")` → `(umask 022 && mkdir -p "./confXXXXXX")`
   #   (umask 077 && mkdir "$tmp")                   → (umask 022 && mkdir -p "$tmp")
   ```
   归一函数必须**打印命中数与残留数**并在不符时抛错（反静默：fix 静默 no-op 是本工作区反复踩的坑）。
   实测输出 `[umask-fix] targets=2 residual_umask077=0`。
   `config.status` 是从 `configure` 的内嵌模板生成的，所以改 `configure` 一处即可两者都修好。

3. **按四口径清点上游 N**（不要混用口径，差额逐项归因）：
   ```bash
   # ① 源码宏数  ② 框架注册数  ③ assertion 数  ④ 上游自带消费者断言数
   grep -rnE "\bassert\s*\(|#include <assert\.h>|EXPECT_|ASSERT_|CK_assert|cmocka|CuTest|TEST\(|START_TEST" \
        --include=*.c --include=*.h . | wc -l
   grep -nE "^(TESTS|check_PROGRAMS|check-local)" Makefile.am | wc -l
   make -n check            # -> "Nothing to be done for 'check'."
   ```
   四者皆 0 ⇒ `N = 0`，**如实申报 0/0 并写明「上游 0 个可运行测试入口」**，
   绝不把空 check 目标的 rc=0 记成通过。

4. **重建真测试面（两条腿，都是真断言）**：
   - **腿 A：读上游解析代码，逆向合成「最小合法输入」**，而不是自研完整对端编码器。
     本例按 `smacker.c::smk_open_generic()` 的字段顺序 + `smk_hufftree.c` 的
     `_smk_huff8_build`/`_smk_huff16_build` 位序（LSB-first，`_smk_bs_read_1` 取
     `1 << bit_num`），构造 8×8 / 1 帧 / 仅视频 / SOLID BLOCK 的 `.smk`：
     每棵 16-bit 树 = `1 | (1,0,L,0) | (1,0,H,0) | 3×16bit cache | 0 | 0`，位打包进字节。
     生成器放在 `test_package/gen_smk.py`，用 `export_sources()` 复用到 `build()`。
     这与 `DRAFT-7316`（自研对端编码器 + 标准向量 + round-trip）互为替代方案：
     **只需一个可解析输入时选本法（便宜、无双错抵消风险）；需要验证完整编解码语义时选 7316**。
   - **腿 B：上游演示程序端到端 + 产物断言**。在 `build()` 里跑 `./driver demo.smk`，
     然后**在配方进程内直接读产物字节**做断言（magic `BM`、尺寸 `1078 + w*h`、逐像素等于编码色），
     任何一条不符抛 `ConanException` ⇒ 构建失败。这样 demo 从「打印一下」变成硬判据。
   - **腿 C：`test_package` 消费者断言测试**，复刻 `driver.c` 的
     `open → info → enable → first → get_* → dump_bmp → close` 调用链，但把「写文件」换成
     「断言」，负例覆盖坏签名 / 截断 / 不存在文件。本例 41 条断言，`1..41 / 0 failures`。

### 禁止做法

- ❌ 把 `make check` 的 rc=0（`Nothing to be done`）写成「上游测试通过」。
- ❌ 把 `test_package` / 鸿蒙特有测试混进上游 N（分栏统计，适配后合计 = 上游合计 + 鸿蒙行）。
- ❌ 用「演示程序跑起来没报错」充当测试面（零断言 = 空跑凑数）。
- ❌ 用 `--no-preflight` 或改全局 PATH 来掩盖 worker 缺 automake/libtool 的事实。

## 验证

```bash
# 1) 上游 N 的四口径（设备可直接执行，源码在 .orig）
cd "$HOME/ws/tmp/builds/libsmacker-1.1.1r35.orig" && \
  grep -rnE "\bassert\s*\(|#include <assert\.h>|EXPECT_|ASSERT_|CK_assert|cmocka|CuTest|TEST\(|START_TEST" \
      --include=*.c --include=*.h . | wc -l          # -> 0
grep -nE "^(TESTS|check_PROGRAMS|check-local)" Makefile.am | wc -l   # -> 0

# 2) 端到端
conan create archives/l/libsmacker/1.1.1r35 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
# 期望关键行：
#   [umask-fix] targets=2 residual_umask077=0
#   [demo-check] OK magic=BM size=1142 pixels=64 colour=0x20
#   # libsmacker consumer test: 41 checks, 0 failures
#   rc=0
```

## 关联条目

- 相似/易混：`E074`（jobserver FIFO → `-j1`）、`E114`（HMDFS 0700 目录不可写）、
  `E421`（SourceForge 主站 403 / Cloudflare）、`E490`（辅助脚本缺执行位告警）
- 同类测试面重建：`DRAFT-7316`（decoder-only 自研编码器 + round-trip）、
  `DRAFT-cute_files-1.0.0-upstream-zero-test-ohos-validation`（零入口可审计证据口径）
- 设备口径：`notes/device-facts.md` §一.4 / §一.10 / §一.14 / §一.30
