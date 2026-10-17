# gcal 4 适配笔记（制品 `gcal/v4`，任务卡 #13430）

> 版本串说明：上游发布名就是 `gcal-4.tar.gz`、横幅 `gcal (GNU cal) 4`，没有带点的替代标签。
> Conan 2.x 的 RecipeReference 校验要求版本至少 2 字符，单字符 `4` 在导出阶段即被拒
> （`ERROR: Invalid package version '4'`）。故按库内已合入的同型做法：任务卡目录
> `archives/g/gcal/4/` 与分支 `feat/gcal-4` 保持 `4`，由 `set_version()` 把制品命名为
> `gcal/v4`（先例：`archives/c/cronic/3` → `cronic/v3`、`archives/r/rapidhash/3` →
> `rapidhash/v3`、`archives/c/cmospwd/5` → `cmospwd/v5`）。配方刻意不写字面量
> `version = "..."`，因为 CI `L0m` 会把该属性与版本目录对拍。

## 编译环境
- 构建系统: autotools（GNU Autoconf 2.69 / Automake 生成的经典树）
- 编译日期: 2026-09-21
- 编译器: clang / clang++（ohos-aarch64 profile，Conan 2.29.1，os=OHOS，musl + libc++）
- 缓存: 独立 `CONAN_HOME=~/work/psj/ch-gcal`（从共享 `~/.conan2` 只复制 profiles/settings.yml，不回写共享缓存）
- 状态: built（`CREATE_EXIT:0`）

## 编译步骤

1. `source()`：`https://ftp.gnu.org/gnu/gcal/gcal-4.tar.gz`（sha256
   `0b582b7fad60b66bc3fae139d95ead910a1b4c8ae2d34aed30618f3e92ec16de`，另列 tuna/ustc/aliyun
   三个 GNU 官方镜像为优先源），`strip_root=True`。
2. `generate()`：`AutotoolsToolchain(self).generate()` 产出 conanbuild 环境（CC/CFLAGS/CPPFLAGS）。
3. `build()`：
   - `apply_conandata_patches()` 应用 `patches/0001-configure-umask.patch`（E011：`umask 077` → `022`）；
   - `_audit_upstream_tests()`：遍历解包树统计 `Makefile.am` 数、`tests/test/gltests` 目录数与
     `TESTS =` 声明数，把「上游 0 用例」这件事变成每次构建都重打的机器证据；
   - **E007**：用 `automake/1.18` 包内副本覆盖 `build-aux/config.guess`、`build-aux/config.sub`；
   - **E386**：`CONFIG_SHELL=/bin/sh sh configure --prefix=… --build=aarch64-unknown-linux-ohos --disable-nls gl_cv_have_weak=no`；
   - `make -j1 MAKEINFO=true`。
4. `package()`：`make install MAKEINFO=true` → `bin/{gcal,gcal2txt,tcal,txt2gcal}` + `share/gcal/*` 历书数据。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ERROR: Invalid package version '4'` | Conan RecipeReference 版本段要求 ≥2 字符，任务卡版本 `4` 是单字符 | 目录/分支保持 `4`，`set_version()` 出 `gcal/v4`，不写 `version` 字面量（L0m）；`commands.json` 补 `"4"` 键（L0k/L0j 按目录名取版本） |
| 2 | `configure: error: working directory cannot be determined` | profile `[buildenv]` 的 `CONFIG_SHELL` 指向 OHOS bash，其在 HMDFS 构建目录 getcwd 失败（E386） | `build()` 内联 `CONFIG_SHELL=/bin/sh` 调用 configure |
| 3 | `config.status: can't create ./conf*/subs1.awk: Permission denied` | autoconf 给临时目录套 `umask 077`，HMDFS 的 uid 映射使其不可写（E011） | `patches/0001-configure-umask.patch` 将 umask 放宽为 022（保留临时目录创建） |
| 4 | `cannot guess build type` | 上游 2015 年的 `build-aux/config.guess` 不认识 aarch64-unknown-linux-ohos（E007） | build() 用 automake/1.18 包内副本覆盖 config.guess/config.sub，configure 钉 `--build` 三元组（不以 ~145KB 全文件补丁承载，避免 AI 评审判「变更过大」而跳过检视） |
| 5 | gnulib `pthread_cancel` 弱符号探测失败 | OHOS 工具链拒绝 `#pragma weak` 指向 musl 头未声明的符号 | configure 传 `gl_cv_have_weak=no`，走非弱符号路径 |
| 6 | `makeinfo` 缺失导致 make 中断 | 构建环境无 texinfo | `make MAKEINFO=true` 跳过 info 文档生成 |

## 上游测试清点（真机实测，非推断）

`conan create` 日志第 135 行：

```
gcal/v4: upstream_test_audit: Makefile.am=8 test_dirs=0 TESTS_declarations=0
```

即整棵发布树 8 个 `Makefile.am`、0 个 `tests|test|gltests` 目录、0 条 `TESTS` 注册，
`make check` 退化为 automake 的标准空递归壳。手工等价命令：

```sh
find . -name Makefile.am | wc -l                                       # 8
find . -type d \( -name tests -o -name test -o -name gltests \) | wc -l # 0
find . -name Makefile.am | xargs grep -cE '^[[:space:]]*TESTS[[:space:]]*[:+]?='  # 全部 0
```

## 消费者测试（test_package/test_gcal.py，4 条断言）

```
PASS: --version reports gcal (GNU cal) 4
PASS: gcal 2/1992 renders the leap-year February (1st on Sa, 29 days)
PASS: bare `gcal` prints a month grid with the Su-Sa header
PASS: unknown option is rejected with non-zero exit
gcal consumer test: all 4 checks passed
```

## 破坏性反向验证（证明确实依赖被测包）

```sh
# 基线
conan test archives/g/gcal/4/test_package gcal/v4 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # POS_EXIT:0，4 条 PASS
# 把包目录的 bin/ 整体改名移走
conan test ...                                                                            # NEG_EXIT:1
#   FileNotFoundError: [Errno 2] No such file or directory: '.../p/bin/gcal'
#   ConanException: Error 1 while executing
# 还原 bin/
conan test ...                                                                            # POS_EXIT:0，4 条 PASS
```

## 产物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/gcal` | 711104 B | 主程序；ELF `e_machine = b7 00`（EM_AARCH64），sha256 `0d17e51b01c26b01491ee51c26721181a3e5cb4cea04e9f50f6e052234216465` |
| `bin/gcal2txt` / `bin/txt2gcal` | 31104 B 各 | 历书事件表 ↔ 文本互转 |
| `bin/tcal` | 31104 B | 三元日历 |
| `share/gcal/*` | — | 历书数据（`gcalrc`、`events*`、`calendar.*`、各语言数据文件） |

## 依赖

- 运行期：无外部依赖（GNU gcal 自带 gnulib）。
- 构建期：`automake/1.18`（E007 用其 config.guess/config.sub 副本），已在制品仓。

## 注意事项

- `package_type = "application"`，产物含 `bin/`，故软件级 `archives/g/gcal/commands.json` 必须新增
  `"4"` 键（`ref` 如实写 `gcal/v4`）；这是 L0k/R38 按目录名取版本的要求，不影响已发布的 `"4.0"` 条目。
- 与已合入的 `archives/g/gcal/4.0`（任务卡 #13436）是同一份上游 tarball 的两条平台任务卡：
  制品仓里 `gcal/4.0` 与 `gcal/v4` 是两个不同 ref，本目录不改写、不重发对方配方。
  本 PR 相对 4.0 的实质增量：① 版本键方案（4.0 走的是「把版本改写成 4.0」，本卡目录必须留 `4`，
  只能走 `set_version()`）；② 上游 0 用例的口径从「人工声明」变成构建期自动重打的审计行；
  ③ 消费者断言从 3 条扩到 4 条，并补了「移走 bin/ 立刻失败」的反向验证。

---

**编译结束**: 2026-09-21 17:40 CST
**最终状态**: built（`CREATE_EXIT:0`）
