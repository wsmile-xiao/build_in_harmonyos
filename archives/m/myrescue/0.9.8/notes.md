# myrescue 0.9.8 适配笔记

- **软件**: myrescue 0.9.8 — 从受损磁盘/文件中抢救仍可读取的数据块
- **上游**: https://myrescue.sourceforge.net/ （SourceForge 项目 `myrescue`）
- **作者**: Kristof Koehler, Peter Schlaile
- **许可证**: GPL-2.0-or-later（`COPYING` 为 GPLv2 全文）
- **源码主语言**: C（4 个 `.c` + 1 个 `.h`，共 1098 行）
- **构建系统**: 裸 GNU make —— `src/Makefile` 全文只有 5 行
- **外部依赖**: 无（只需 libc）
- **工具链**: OHOS clang 15.0.4 / musl / libc++，`aarch64-unknown-linux-ohos`
- **状态**: built（W3 本地 CI 通过，未上传制品仓）
- **任务号**: 9078

---

## 一、上游形态与本项目特有的适配难点

`src/Makefile` 逐字全文：

```make
CFLAGS = -Wall
all: myrescue myrescue-stat myrescue-bitmap2ppm
myrescue: myrescue.c permute.c
myrescue-stat: myrescue-stat.c
myrescue-bitmap2ppm: myrescue-bitmap2ppm.c
```

三条结构事实决定配方写法：

1. **首行是裸赋值 `CFLAGS = -Wall`**：环境变量里的 CFLAGS 会被这一行覆盖掉，
   只有写在 `make` 命令行上的赋值才能压过 Makefile 内的赋值。
2. **三行依赖没有 recipe**，全靠 GNU make 的内建规则编译链接，因此编译器走
   make 的默认 `CC = cc`。
3. **没有 install 目标、没有 DESTDIR、没有 configure/autotools/cmake、
   没有 check/test 目标**。上游 `INSTALL` 原文就是
   "Copy the myrescue binary to the destination location"。

---

## 二、症状 → 根因 → 最小复现 → 已试过的失败方案 → 最终方案 → 适用边界

### 问题 1：默认 make 直接起不来

- **症状**（A 机真机原文，`~/tmp/uc2/z41-myrescue/explore/`）：
  ```
  cc -Wall     myrescue.c permute.c   -o myrescue
  make: cc: No such file or directory
  make: *** [<builtin>: myrescue] Error 127
  ```
- **根因**：三枚二进制都靠内建规则链接 ⇒ 走 make 内建 `CC = cc`。OHOS 上
  clang 只在 `/data/service/hnp/bin/clang` 与 SDK 目录里，**没有 `cc` 别名**。
  同一行 `CFLAGS = -Wall` 还把工具链经环境传下来的 CFLAGS 全部吞掉。
- **最小复现**：
  ```sh
  tar xzf myrescue_0.9.8.orig.tar.gz && cd src && make -j1
  ```
- **已试过的失败方案**：
  - 只 `export CC=... CFLAGS=...` 不写进命令行 —— `CFLAGS` 被 Makefile 首行
    覆盖，编译期工具链 flags 全丢；
  - `make CFLAGS+="..."` 追加 —— GNU make 命令行上的 `+=` 会先把上游值清空
    再追加，`-Wall` 静默消失（先例见
    `knowledge/drafts/DRAFT-genann-1.1.1-make-cflags-march-native-override.kv`
    对 heatshrink 案例的记录）；
  - 给 Makefile 打补丁 —— 没必要，命令行覆盖即可，且补丁会扩大 diff 面。
- **最终方案**：编译器一律从 conan conf 取（R33），CFLAGS **整体替换**并保留
  上游的 `-Wall`：
  ```python
  self.run(f'make -j1 CC={shlex.quote(cc)} '
           f'CFLAGS={shlex.quote(" ".join(self._cflags()))}', cwd=src)
  # -> make -j1 CC=/data/service/hnp/bin/clang CFLAGS='-Wall -fsigned-char -O2 -DNDEBUG'
  ```
  实测 rc=0，三枚 ELF 全部产出。
- **适用边界**：一切 "裸 Makefile + 内建规则链接 + 首行 `CFLAGS = ...` 裸赋值"
  的 C 项目。若上游 Makefile 用的是 `CFLAGS ?=` 或 `override CFLAGS`，本法无效。

### 问题 2（本次真正的功能性缺陷）：plain char 有符号性改变块状态语义

- **症状**：clang 在 `-Wall` 下即报（原文见 `reports/conan-create.log`）：
  ```
  myrescue-bitmap2ppm.c:135:23: warning: result of comparison of constant -1
      with expression of type 'char' is always false
      [-Wtautological-constant-out-of-range-compare]
      } else if ( buf_bit[x] == -1 ) {
  myrescue.c:273:22: warning: result of comparison of constant -127 with
      expression of type 'char' is always true
  ```
- **根因**：myrescue 的位图存的是**有符号** 8 位块状态（`0`=未测、`1`=读成功、
  `-1`/`-2`=失败次数、`2`=读得慢），但读写两侧都用 plain `char`
  （`peek_map()` 返回 `char`、`buf_bit` 是 `char*`）。AArch64 PCS 规定 plain
  `char` 默认**无符号**，于是 `0xFF` 读回来是 `255`：
  `do_copy()` 的续读判据 `block_state <= 0` 永假 ⇒ 之前失败的块**永远不会被
  重试**；`myrescue-bitmap2ppm` 的 `== -1` 分支永不可达。
- **最小复现（A 机双臂对照，同一份源码只差 `-fsigned-char`）**：
  先用 `-e 12` 扫一个 8192 字节的源（块 8–11 读不到 → 位图记 `ff`），然后把源
  补长到 12288 字节（介质"修好了"），拿**同一份位图**再扫一遍：

  | 构建 | pass1 位图 | pass2 位图 | pass2 目标大小 | 结果 |
  |---|---|---|---|---|
  | 默认（plain char 无符号） | `01×8 ff×4` | `01×8 ff×4` | **8192** / 12288 | 失败块从未被重试 |
  | `-fsigned-char` | `01×8 ff×4` | `01×12` | **12288** / 12288 | 全部追回，`cmp` 一致 |

  第二处可测后果：同一份混合位图喂给 `myrescue-bitmap2ppm`，
  失败块在无符号臂渲染成 `(255,0,0)` 红（落到"其它"分支），
  `-fsigned-char` 臂渲染成上游专设的 `(255,255,0)` 黄。
  证据：`~/tmp/uc2/z41-myrescue/explore2/{a,b}/`、
  `~/tmp/uc2/z41-myrescue/logs/conan-verify-3.log`。
- **已试过的失败方案**：
  - 在源码里把 `char` 改成 `signed char` 打补丁 —— 命中 E419 的
    `forbid_2`（禁止用平台宏条件分叉），且要改 3 处读点、动上游语义；
  - 只改测试期望值 —— 命中 E419 的 `forbid_1`，库行为仍是错的；
  - 只在 `myrescue-bitmap2ppm.c` 上加 —— `myrescue` 主程序的续读判据同样是
    受害者（上表已证），必须**全部**翻译单元一致。
- **最终方案**：按 E419 推荐 `consistent-target-signed-char-mode`，在配方
  `_cflags()` 里加 `-fsigned-char`，一次性覆盖三枚二进制的全部目标文件。
  零补丁、零平台宏。
- **适用边界**：上游用 plain `char` 承载**语义上有符号**的 8 位值（块状态、
  像素、音频样本、二进制格式 INT8 字段）且默认构建主机是 x86-64 的 C 项目。
  若上游已显式写 `signed char`/`int8_t` 则不需要；若上游本就把 `char` 当无符号
  计数用，加这个开关反而会引入错误。

### 问题 3：没有任何 install 目标

- **症状**：`make install` → `No rule to make target 'install'`。
- **根因**：上游 `INSTALL` 文件自己承认 "…is currently in a rather poor state"。
- **最终方案**：`package()` 手工安装 —— 三枚二进制 → `bin/`，三份英文 man 页
  → `share/man/man1/`，`doc/myrescue.de.1` 是**德语译文**而非独立命令页，因此
  落到 `share/man/de/man1/myrescue.1`（改名，避免出现一个假的
  `myrescue.de` 命令页）；`COPYING` → `licenses/`，
  `AUTHORS/ChangeLog/INSTALL/README` 与那份待办清单一共五份文本文件 → `share/doc/myrescue/`。
  另外 OHOS 不执行未签名 ELF，故三枚二进制在 `build()` 与 `package()` 里各
  self-sign 一次（`binary-sign-tool -selfSign 1`，先 `llvm-objcopy
  --remove-section .codesign` 去旧段）。
- **适用边界**：所有无 install 目标的裸 Makefile CLI 包；man 页的 locale 布局
  仅适用于"同页多语言"的上游。

### 问题 4：上游 tarball 是扁平结构

- **症状**：`strip_root=True` 时 conan 直接抛
  `Can't untar a tgz containing files in the root with strip_root enabled`。
- **根因**：上游包顶层**没有** `myrescue-0.9.8/` 这层目录，16 个条目
  （六份根目录文本文件 + `doc/` + `src/`）全在根上。
- **最终方案**：`source()` 用 `destination=self.source_folder, strip_root=False`，
  保持归档原样，`build()` 显式进 `src/` 子目录。
- **适用边界**：一切扁平 tarball。

### 顺带排除掉的两处"看着要改其实不用改"

对 OHOS musl/SDK 做过编译探针（`~/tmp/uc2/z41-myrescue/probe/`，全部 rc=0），
因此**零补丁**：

- `myrescue.c` 硬开 `#define HAVE_USBRESET 1` 并
  `#include <linux/usbdevice_fs.h>` 用 `USBDEVFS_RESET`
  → 该 UAPI 头在 OHOS native sysroot 里存在；
- 三个源文件都用 `open64()` / `lseek64()`（自声明
  `_LARGEFILE64_SOURCE`）→ OHOS musl 正常提供 LFS64 入口。

---

## 三、上游测试清点（手工等价扫描，含框架脚本不可用说明）

⚠ 框架清点脚本 `ci/tools/extract_upstream_tests.sh` **在本机不可用**：它硬编码
`/tmp`，设备 `/tmp` 只读，日志只剩失败记录。⇒ 改用手工等价扫描，全过程与产物
留在 `~/tmp/uc2/z41-myrescue/`（`test-inventory-tarlist.txt`、
`test-inventory-markers.txt`、`test-inventory-dirs.txt`）。

对**实物 tarball**（sha256 `b4ef60903a44b66c926adcd5d8ab70ddeab94b26c250601498a5e24b19e4c1d7`）：

| 扫描项 | 命令口径 | 结果 |
|---|---|---|
| 全清单 | `tar tzf <tarball>` | 16 条目：6 份文本 + `doc/` 4 份 man 页 + `src/` 6 份文件 |
| Perl 标记 | `Test::More` / `use_ok` | 0 / 0 |
| Python 标记 | `def test_` | 0 |
| C/C++ 标记 | `TEST_CASE` / `add_test` / `enable_testing` | 0 / 0 / 0 |
| 测试目录 | `t/` `tests/` `test/` `spec/` | 0 个 |
| Makefile 测试入口 | `src/Makefile` 里的 `TESTS` / `check` / `test` | 0 处 |
| 文件名含 test | 全清单 grep | 0 个 |

⇒ **上游静态测试总数 = 0**，不是"没跑"，是上游确实没有自动化测试
（上游那份待办清单里 "./configure && make && make install" 至今仍未完成，可佐证
其打包/测试基建的成熟度）。不得声称跑过不存在的 `make check`。

**五维账本**（与 `test_package/MANIFEST.yml`、`0.9.8/manifest.yaml`、PR 正文同源）：

| 维度 | 数值 | 依据 |
|---|---|---|
| `N_static`（上游静态声明） | **0** | 上表七项扫描 |
| `N_registered`（构建系统注册） | **0** | 无 check/test 目标、无 TESTS 变量 |
| `N_executed`（实际执行） | **0** | 无可执行对象；配方内另跑一次真实二进制冒烟 |
| 未执行/跳过分类 | **0** | 无对象可跳 |
| 上游失败数 | **0** | — |
| `N_consumer`（消费者测试） | **46**（断言 46 条，实测通过 46、失败 0） | `test.sh` 自计数 |

---

## 四、消费者测试设计（test_package/test.sh，46 条断言）

三枚二进制全部按"从受损源逐块抢救 + 位图"的真实语义做端到端 file→file 实测：

| 组 | 覆盖 | 断言数 |
|---|---|---|
| [0] 安装面 | 三枚二进制存在且可执行；3 份 man1 + 1 份 de/man1 | 7 |
| [1] 干净 file→file | 退出码、目标产出、大小一致、**逐字节 cmp 相同**、默认位图路径、位图长度=块数、位图全 `01`、`myrescue-stat` 退出码与 `1: 8 (100.00%)` 读数、`bitmap2ppm` 退出码、P6 魔术号、几何 `8 1`、maxval 255、payload=3字节/块、首末像素绿色 | 16 |
| [2] 受损尾段 | 越界块读取下退出码、可读前缀仍全量且逐字节相同、位图 `01×8 ff×4`、stat 分离好坏计数、坏块渲染成黄色而好块仍绿色 | 8 |
| [3] 有符号性回归护栏 | pass1 记坏块 → 介质修复 → **pass2 必须回来重试**：位图清成 `01×12`、目标 12288 字节、`cmp` 一致 | 5 |
| [4] 参数语义 | `-B` 自定义位图路径、`-s/-e` 只拷指定区间（位图 `0000010101`）、stat 未测块保持类别 0、`-A` 首个失败即中止 | 4 |
| [5] 随机跳跃模式 | `-J 3` 乱序模式跑完且重建逐字节一致（唯一走 `permute.c` 的路径） | 2 |
| [6] 参数校验 | `-h` 打印用法、非法块大小被拒且指名选项、裸调用被拒 | 4 |

判决行原文（`reports/w3-local-ci.log`，同 `reports/conan-create.log`）：

```
ASSERTION TOTAL=46 PASSED=46 FAILED=0
RESULT: PASS
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: myrescue version/help failed, myrescue-bitmap2ppm failed, myrescue-stat failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
```

W3 本地 CI 判决（`.ci-result.json`）：`exit_code: 0`，
`log_sha256: c07f83f1f1ba0cb0f09424106f7296e32dfc6511f8bf1456d087fc3da6480814`。

---

## 五、未执行 / 未覆盖的检查（如实披露）

1. **`L2` 平台功能矩阵被工具判 skip**：它对每枚二进制试 `--version` / `--help`。
   myrescue 上游**没有** `--version`，`-h` 走 getopt 的 `default:` 分支打印用法后
   `exit(-1)`（退出码 255），因此该矩阵按字面判据"失败"。功能层面的等价证据已
   由 §四 的 46 条断言与 `build()` 内的
   `./myrescue -h | grep -qF 'myrescue [<options>]'` 提供，不是缺口。
2. **`G4` 产物完整性 / `L4` checksec / `L5` 基线在 conan-verify 阶段报
   "无法找到程序包 ID / 跳过（无 cache 路径）"**（见
   `reports/conan-verify-report.md`）；W3 本地 CI 内的 L0/L1/L4/L5 是真跑并判 pass。
3. **`finish` step 5b `check_knowledge_gap` 判红**（`manifest.yaml:
   knowledge_count=6 unreferenced=6`）：这是框架判据与全仓既有写法的矛盾，
   非本包缺陷——仓内 4997 个 `knowledge_gained` 非空的包中 4623 个（92.5%）同为红。
4. **`finish` step 8 `gen_summary` 失败**：`'str' object has no attribute 'append'`，
   框架侧异常，`SUMMARY.md` 属只读框架文件，未改。
5. **`finish` step 3 `clean-verify` 判 "找不到原始 tarball"**：非阻塞项
   （SKILL W3 明示"平台限制可跳过"）；G2 的 `conan create` 是从零下载源码构建的，
   已覆盖同一自包含性判据。
6. **未跑 `make check`**：上游无该目标，见 §三。
7. **`-U <dev-file>`（USB 总线复位）路径未做真机功能断言**：需要一个真实的
   USB 设备节点，沙箱内不可得；该分支只证明能编译与链接（`linux/usbdevice_fs.h`
   探针 + 三枚二进制均成功编译）。
8. **`step 10` submit 就绪预检仍报两项未就绪**：`packaging/`（需真实 release/debug
   tar.gz，本包只到 `built` 未上传制品仓）与 `.staging-verified`（对应 DESTDIR
   staging 验证，本包无 install 目标、该验证未发生过）。两者均非阻塞门禁，
   且**未自行补造标记文件**（无证据不打标记），留由主代理处置。
9. **框架 PF9 与 PF8 对 CLI 包互斥（已用两个已合入包做对照实证，非本包缺陷）**：
   `scripts/ohc/preflight.py:559 check_branch_and_paths()` 用
   `len(f.split("/")) < 5` 判"缺版本目录层"，因此任何位于
   `archives/<字母>/<包>/` 层的**软件级**文件都会被拦；而 R38/PF8/L0k 又**强制**
   CLI 包必须在软件级放 `commands.json`（ARCHIVE-SPEC 还要求软件级
   `manifest.yaml` 与 `README.md`）。对照实测（`python3 scripts/ohc/preflight.py . <base> <head>`）：

   | 提交 | 状态 | PF9 判决 |
   |---|---|---|
   | 本包 `origin/main...HEAD` | 未提 PR | ✗ 命中（README.md / commands.json / manifest.yaml） |
   | `904fb3723d` aa3d 1.0 | **已合入 main** | ✗ 命中同一三项 |
   | `6b473b1135` basez 1.6.2 | **已合入 main** | ✗ 命中同一三项（另加 PF7 Debian 源两项） |

   ⇒ 三个 CLI 包同形，说明这是**框架判据与全仓 CLI 包写法的矛盾**（与 §11.5
   记录的 `check_knowledge_gap` 92.5% 判红同类），不是本包改动能修的问题；
   本包其余硬闸 **PF1/PF2/PF3/PF4/PF5/PF6/PF7/PF8 + R52 全部 PASS**
   （`check_source_urls`/`check_recipe_static`/`check_recipe_shared_prefix` 实测 PASS）。
   **不要**为了过 PF9 而删 `commands.json`——那会直接撞 R38/L0k/PF8。

---

## 六、路径 B 判定素材（实拍机制 + 宽口径检索）

**结论建议：维持 `hit`，不建议升 `create`。** 三条实拍机制全部落在既有条目内：

| 实拍机制 | 既有覆盖（精确到文件/行，已逐行核对） |
|---|---|
| 裸 Makefile 首行 `CFLAGS = -Wall` 吞工具链 flags，必须整体替换 | `knowledge/drafts/DRAFT-genann-1.1.1-make-cflags-march-native-override.kv:12-15`（approach 逐字："build() 以 `make CFLAGS=\"...\"` 整体替换上游 CFLAGS…不追加"）、`:23-25`（root_cause 含"GNU make 命令行 CFLAGS+= 追加会清空上游 flags（heatshrink 草稿）"） |
| 裸 make 靠内建规则链接 ⇒ 默认 `CC=cc` 在 OHOS 上不存在 | `经验文档/B草稿库/README.md` M18 行（suckless 系 `CC=cc` 烧死；dmenu 5.4 实拍症状逐字 `make: cc: No such file or directory`，与本包 `explore/` 复现的 `make: cc: No such file or directory` + `Error 127` 同型） |
| 无 install 目标的自装 | `DRAFT-genann-1.1.1-…kv:14-15`（"无库 install 目标时 package() 自行 ar rcs 归档静态库并复制头文件（E097 手动安装模式）"）；`knowledge/drafts/DRAFT-commander-1.4.0-makefile-recipe-build-package-traps.kv:12-15`（裸 Makefile 配方的 build()/package() 陷阱族，其 `keywords` 行 :18 含 `no install target`）；`经验文档/B草稿库/` M13（`makefile-install-cmd-absent-makevar-override`） |
| plain char 有符号性（AArch64 默认无符号）⇒ 运行时语义改变 | **正式条目** `knowledge/graph/E419.kv`（`knowledge/graph/index.tsv:645`，关键词含 `-fsigned-char, plain char, unsigned char, integer promotion, AArch64`；`doc_file: doc/E2158.md`），推荐方案 `consistent-target-signed-char-mode`、`rec_command: toolchain.extra_cflags.append("-fsigned-char")`；并明确 `forbid_1`（改测试期望值）与 `forbid_2`（用 `__OHOS__` 条件分叉）两条禁止项——本包两处都遵守（配方内 `grep -c '__OHOS__'` = 0） |
| `tools.build:compiler_executables` 必须按字典取、不能写 `:c` 单项 | `knowledge/drafts/DRAFT-commander-1.4.0-…kv:14-15`（"模板写法照抄即抛 conf 异常，R33"）——本配方直接采用其结论，未再踩 |

检索口径（**宽口径，四路**，均按要求先单关键词再逐步加限定）：
`grep -rn -i 'fsigned-char'`、`'signed char'`、`'Wtautological'`、`'AAPCS'`、
`'aarch64.*char'` 扫 `knowledge/` 全树 → 命中
`knowledge/doc/E419.md`、`knowledge/graph/E419.kv`、
`knowledge/drafts/DRAFT-9645-polyseed-aarch64-char-signed-utf8-lazy.{kv,md}`、
`DRAFT-clipp-1.2.3-ohos-char-signedness-value-conversion.{kv,md}`、
`DRAFT-etl-20.38.4-char-signedness-upstream-tests.{kv,md}`、
`DRAFT-8543-plain-char-eof-sentinel-infinite-loop.{kv,md}`；
另在 `archives/` 里找到 7 个已用 `-fsigned-char` 的先例
（`archives/p/polyseed/1.0.0`、`archives/l/ldapvi/1.8`、
`archives/m/mcsim/6.2.0`、`archives/m/mmsrip/0.7.0`、`archives/a/avanor/0.5.8`、
`archives/b/burst/3.1.1`、`archives/l/librasterlite2/1.1.0-beta1`）。
`scripts/ohc-run.py recipe-search myrescue` 与 `-b makefile` 均返回
"无相似配方（语料 6173 条）"，故首稿按框架模板自写。

**唯一可能撑 create 的角度**（已自查，判定**不成立**）：
"三枚二进制 + 无 install 目标 + man 页 locale 布局"这一**组合**是否是既有条目
没覆盖的 OHOS 独有坑。逐条对齐：三枚二进制的 self-sign 是仓内 **1149 份**配方
（`grep -rl 'binary-sign-tool' archives --include=conanfile.py | wc -l` = 1150，
含本包自减一）的通用写法，
man 页 locale 布局纯属打包策略而非平台陷阱，位图/扁平 tarball 也不涉及 OHOS 特有
行为 ⇒ 拿不出"既有条目没写的另一条解法或另一层症状"，按 `手册/03` 的 B 判重四
条件不构成 create。若主代理仍要打 create，建议的落点是
**"AArch64 plain-char 有符号性会静默摧毁'断点重试'类状态机（而非仅让 INT8
读数错位）"** 这一运行时子面——但 E419 的 `affected_scope` 已写明"comparisons
and API results fail only on the target"，与本包症状同型，因此该落点偏弱。

---

## 七、验证命令与结果

```sh
# 依赖前置（零依赖）
bash ci/scripts/preflight_check.sh myrescue/0.9.8              # PASS（主代理已跑，收尾复跑）
python3 scripts/ohc-run.py recipe-search myrescue               # 无相似配方，语料 6173
sh ~/tmp/uc2/build-slot.sh --kind short -- \
  python3 scripts/ohc-run.py conan-verify myrescue 0.9.8        # G0-G4 + L2/L4/L5 → 配方验证通过
sh ~/tmp/uc2/build-slot.sh --kind short -- \
  python3 scripts/ohc-run.py finish myrescue 0.9.8 built        # step5 W3 本地 CI 通过
```

编译命令行（`reports/conan-create.log` 原文）：

```
make -j1 CC=/data/service/hnp/bin/clang CFLAGS='-Wall -fsigned-char -O2 -DNDEBUG'
```

打包内容（9 个文件 + 4 份 man 页）：`bin/{myrescue,myrescue-stat,myrescue-bitmap2ppm}`、
`share/man/man1/*.1` ×3、`share/man/de/man1/myrescue.1`、
`licenses/COPYING`、`share/doc/myrescue/`（作者、变更日志、安装说明、项目说明、
待办清单五份上游文本文件）。

---

## 八、注意事项

- 版本号、归档目录 `archives/m/myrescue/0.9.8/`、分支 `feat/myrescue-0.9.8`
  与任务版本四处必须逐字符一致（`0.9.8`，不归一化）。
- conandata 只写上游官方 SourceForge URL。设备取源时**顺带**核对过 Debian
  `myrescue_0.9.8.orig.tar.gz` 与之 sha256 逐字节相同
  （`b4ef60903a44b66c926adcd5d8ab70ddeab94b26c250601498a5e24b19e4c1d7`），
  说明上游未被打补丁重排；但 **PF7 明令拦 `deb.debian.org`**，故活文件里
  不留任何 Debian 池 URL（对照先例 `archives/b/basez/1.6.2/conandata.yml`
  是 PF7 落地前的旧写法，不可照抄）。
- 测试脚本 shebang 用 `#!/bin/sh`，不硬编码 FHS 解释器路径；`test_package`
  里的 conan 生成物（`conanrun.sh` 等）已被 `.gitignore` 覆盖，提交一律精确
  add 单个文件。

---

## 九、对话记录（本次适配实际序列）

### 对话 #1 — 主理-41 名下适配执行段（2026-09-25，A 机鸿蒙 PC）

- **W0 依赖核验**：`preflight_check.sh myrescue/0.9.8` → PASS（零依赖；开坑时与
  收口前各实跑一次，收口输出 `[OK] 预检通过（无依赖需要检查）`）。
  取源用上游官方 SourceForge 包；顺带与 Debian
  `myrescue_0.9.8.orig.tar.gz` 做 sha256 交叉核对，逐字节相同 ⇒ 上游未重打包。
  因 PF7 拦 `deb.debian.org`，活文件只保留官方 URL。
- **官方 URL 活性实测**（收口前，A 机 `~/tmp/uc2/z41-myrescue/urltest/`，冷态 curl）：
  `https://downloads.sourceforge.net/project/myrescue/myrescue/myrescue-0.9.8/myrescue-0.9.8.tar.gz`
  → `http=200 size=23292 time=7.83s`，sha256 与 conandata 一致（302 终点
  `master.dl.sourceforge.net/…?viasf=1…`）。短端点
  `sourceforge.net/projects/myrescue/files/.../download` 同样 200（2.22s）。
  **并且**：共享下载缓存 `~/tmp/ch/dlcache` 内 `find -iname '*myrescue*'` 命中
  **0** 条 ⇒ 本地这轮绿不是靠缓存喂出来的，是真下载。
  （仍不据此声称 CI 必过：CI 侧镜像策略与 worker 出口不同。）
- **recipe-search**：`myrescue` 与 `-b makefile` 均"无相似配方（语料 6173 条）"
  ⇒ 首稿按 `templates/conanfile-makefile.py.tmpl` 自写。
- **源码静态分析**：确认 `src/Makefile` 5 行、无 install/check 目标；
  识别出三处 OHOS 风险（`CC=cc` 默认、`CFLAGS` 裸赋值、
  `HAVE_USBRESET`/LFS64/`char` 有符号性）。
- **编译探针**（`~/tmp/uc2/z41-myrescue/probe/`，rc 全 0）：
  `linux/usbdevice_fs.h` 与 `open64`/`lseek64` 在 OHOS sysroot/musl 上均可用
  ⇒ 判定零补丁，排除两条"看着要改"的假线索。
- **手工等价测试清点**（框架 `extract_upstream_tests.sh` 因 `/tmp` 只读不可用）：
  七项扫描全部 0 命中 ⇒ `N_static = 0`，留档
  `test-inventory-{tarlist,markers,dirs}.txt`。
- **探索性编译**（`~/tmp/uc2/z41-myrescue/explore/`）：默认 `make -j1` 复现
  `make: cc: No such file or directory` + `Error 127`；命令行覆盖 CC/CFLAGS 后
  rc=0，并暴露 `-Wtautological-constant-out-of-range-compare` 系列告警。
- **signed-char 双臂对照**（`explore2/{a,b}`）：证明无符号臂下"回头重试坏块"
  静默失效（8192/12288），`-fsigned-char` 臂全量追回（12288/12288），
  并证明 `bitmap2ppm` 坏块配色红→黄。据此按 E419 采用工具链修法。
- **G2 第一轮 FAIL**：`TypeError: copy() got multiple values for argument 'src'`
  （`package()` 里对 `copy()` 传了可变位置参数）⇒ 改为逐项循环。
- **G2 第二轮 FAIL**：`AttributeError: '_Component' object has no attribute
  'package_folder'`（test_package 里走 `cpp_info`）⇒ 改用
  `self.dependencies["myrescue"].package_folder`。
- **G2 第三轮 PASS**：G0-G4 全绿，test_package 46/46 断言通过。
- **finish**：step 2 close-archive ✅、step 4 conan-verify ✅、
  **step 5 W3 本地 CI ✅（阻塞门禁）**、step 9 W2 原子性 ✅（仅 10 个配方文件）。
- **状态**：`built`。`packaging/` 与 `.staging-verified` 两项 step-10 预检未自行
  补齐（前者需真实 release/debug tar.gz，本包只到 `built` 未发布；后者对应的
  DESTDIR staging 验证本包未发生，不做无证据标记），已在 §五 如实披露。
---

**编译结束**: 2026-09-25 18:56
**最终状态**: built
