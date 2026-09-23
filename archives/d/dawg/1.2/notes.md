# dawg 1.2 适配笔记

## 编译环境

- 目标平台：OpenHarmony / HarmonyOS PC（aarch64）
- 构建系统：CMake（上游 `CMakeLists.txt`，声明下限 2.6）
- 编译器：clang 15.0.4（OHOS SDK）+ libc++，`compiler.cppstd=17`
- Conan：2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 构建工具：bison/3.8.2、flex/2.6.4、m4/1.4.19（均 `tool_requires`，来自 ohpcd 制品仓）
- 编译日期：2026-09-11　状态：built（`conan-verify` 通过，未确认 release upload）

## 编译步骤

```bash
# 1) 原生探索（裸 cmake，未加 -std，clang 15 默认 gnu++14）
cmake -S dawg-1.2 -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release
make -C build -j1

# 2) 上游测试（脚本读 top_srcdir/DAWG/DIFF 环境变量）
DAWG=build/src/dawg DIFF=diff top_srcdir=dawg-1.2 sh dawg-1.2/tests/test0.sh

# 3) Conan 干净构建（同一 profile 作为 host+build）
conan create archives/d/dawg/1.2 \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方侧关键点：

- `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})` —— 上游声明
  `CMAKE_MINIMUM_REQUIRED(VERSION 2.6 FATAL_ERROR)`，CMake 4.x 已移除 <3.5 兼容策略；
  该策略检查在 `CMakeLists.txt` 首行执行，早于 toolchain 文件加载，故必须走命令行缓存变量。
- `tool_requires("bison/3.8.2")` + `tool_requires("flex/2.6.4")` + `tool_requires("m4/1.4.19")`
  —— `src/CMakeLists.txt` 第 10-12 行缺 bison/flex 任一即 `SEND_ERROR`。
- `BISON_PKGDATADIR` / `M4` 重定向 —— 见问题 #1。
- `CMAKE_SYSTEM_NAME=Linux` —— CMake 无 OHOS 平台模块；不设置时每次探测都打印
  "System is unknown to cmake, create: Platform/HarmonyOS"（探测结果本身正确）。
- `BUILD_SHARED_LIBS=OFF`（R26：终端工具不做动态库交付）。上游 CMakeLists 不消费该变量，
  配置期会打印 "Manually-specified variables were not used by the project" 属预期。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `bison: /share/bison/m4sugar/m4sugar.m4: cannot open: No such file or directory`（conan create G2 首次失败） | ohpcd 的 bison/3.8.2 包构建时使用 `--prefix=`，把 pkgdatadir 硬编码成绝对路径 `/share/bison`；conan 缓存中的实际位置是 `<bison_pkg>/share/bison`，运行时找不到 m4 宏库 | 配方 `build()` 内用 `Environment` 定义 `BISON_PKGDATADIR=<bison_pkg>/share/bison` 与 `M4=<m4_pkg>/bin/m4`，包住 configure/build/test（与仓库 `archives/b/ball` 同一处置，也是 bison 自身 test_package 的做法）；同时把 m4 加入 `tool_requires` |
| 2 | `error: no template named 'auto_ptr' in namespace 'std'`（C++17 编译期，tree.h 4 处） | 上游是 2009 年代码，使用 `std::auto_ptr`；该模板在 C++11 弃用、**C++17 移除**。profile 强制 `compiler.cppstd=17`。裸 cmake 探索（clang 15 默认 gnu++14）只报 deprecated 警告，因此该错误只在 Conan 路径暴露 | 补丁 `0002`：`std::auto_ptr<T>` → `std::unique_ptr<T>`（这些成员只做 `.get()`/`.reset()`/解引用，无所有权转移式拷贝，语义等价；显式包含 `<memory>`） |
| 3 | `error: no member named 'unary_function' in namespace 'std'`（同上，indel.h 1 处） | 同上：`std::unary_function` 亦在 C++17 移除 | 补丁 `0002`：`LinearFunc` 去掉基类，自带 `argument_type`/`result_type` typedef，保持原有调用接口（无 `bind1st`/`ptr_fun` 用法） |
| 4 | 上游唯一测试入口 `tests/test0.sh` 失败（输出与 `tests/test0.fasta` 不一致） | **上游基准过期**，非平台差异：v1.1 起 RNG 语义由 ILP32 位拼接改为 `(double)u/2^32`、比较由 `<=` 改为 `<`，基准从未重生成；且上游 CMake 化时没有迁移该测试（`tests/CMakeLists.txt` 为 0 字节、ctest 注册数 0），失败被长期隐藏 | 补丁 `0001` 用实测确定性输出刷新基准；判别证据见下节 |
| 5 | `make: jobserver mkfifo: ... Operation not permitted` 噪音 | 设备 HMDFS/权限限制 | 不影响构建结果，不处理（属预期噪音） |
| 6 | `-o out.fasta` 报 `Unknown file format, "%s".` | 上游按扩展名推断格式且大小写敏感（`fas`/`nex`/`phy`/`aln`/`poo`/`txt`/`out`），`fasta` 不在其中；且该诊断的 `%s` 未被格式化 | 测试脚本改用上游认可的 `.fas`（属上游行为，不改源码） |

## 上游测试基准过期（补丁 0001 的依据与判别过程）

这是本次适配最关键的判断，结论是**上游基准过期，不是 OHOS 输出错误**。判别分两步，
两步都有可复算的原始证据：

### 第一步：跨平台复现（排除"OHOS 输出错了"）

用**未修改**的上游源码在第二平台运行同一输入，与本机输出逐行比对：

- 本机：OHOS PC aarch64 + clang 15 + libc++ + musl
- 第二平台证据：Debian `dawg` 源码包（1.2-5）与 Debian Med 邮件列表归档。**原始字节已随本 PR
  入库**于 `reports/evidence/`（每份附来源 URL、抓取时 HTTP 状态码与 sha256），可离线复核：
  - `reports/evidence/debian-1.2-5-rules.txt` 第 24-30 行：`override_dh_auto_test` 里写着
    `cd tests && PATH=$$PATH:$(BINDIR) sh test0.sh || true`，并以注释
    `#  see https://github.com/reedacartwright/dawg/issues/56` 给出上游 issue 编号；
  - `reports/evidence/debian-med-2018-07-msg00017.html`：Debian Med 邮件列表（2018-07-05）
    贴出的 amd64/glibc/GCC 构建时该测试**实际 diff 输出**；
  - `reports/evidence/debian-bug-903886-2020-10-author-reply.html`：转发上游作者的 GitHub
    通知邮件（标题 `Re: [reedacartwright/dawg] Test script fails (#56)`），正文说明新代码库
    尚未迁移该测试脚本。

两份输出**逐行一致**（同样 5 条序列、同样 gap 位置），但都与签入的
`tests/test0.fasta` 不同 → 排除平台差异。

取证边界（如实说明）：本设备访问 `https://github.com/reedacartwright/dawg/issues/56` 返回
**HTTP 404**（响应体 9 字节 `Not Found`；同设备 `https://github.com/` 本身返回 200，
即失败的是该具体路径而非主机整体，9 字节响应体亦非 GitHub 常规 404 页面形态，疑与设备侧
出口网关有关）。因此本任务**未直接读到该 issue 页面**；该次失败抓取已原样留档为
`reports/evidence/github-issues-56-from-device.html`。issue 编号 `#56` 的采信依据是上述
**两条离线可复核来源**（Debian 官方包内 `debian/rules` 的注释 + 邮件列表归档里上游通知邮件的
标题与正文），而非对该链接的直接访问。

另外交叉核对了源码来源：Debian `dawg_1.2.orig.tar.gz` 与本包所用官方 tag tarball
**SHA-256 相同**（`0034d77309e538b34a395916326818a1a0d37cad789819178a905daabb41c9fe`），
即两端跑的是同一份代码。

### 第二步：旧语义还原实验（钉死基准归属旧版本）

只把 `rand_real()`/`rand_bool()` 还原为 v1.0.0 语义（union 位拼接 + `<=`）重新编译，
再与旧基准比较**最长公共前缀**：

| 序列 | 基准长度 | 当前 v1.2 输出 LCP | 还原旧语义后 LCP |
|------|---------|-------------------|-----------------|
| A | 102 | 0 | 2 |
| B | 102 | 0 | 26 |
| C | 102 | 0 | 10 |
| D | 102 | 0 | 50 |
| R | 102 | 0 | 50 |

当前输出与旧基准 LCP 全为 0，还原旧语义后立刻升到最长 50/102 —— 证明基准属于旧 RNG 语义。

该实验**可复算**：还原改动全文已随本 PR 入库为 `reports/evidence/rng-old-semantics.diff`
（仅 `src/rand.h` 的 1 个 hunk：`rand_real()` 改为 union 位拼接、`rand_bool()` 的 `<` 改为 `<=`，
即 v1.0.0 语义）。复算方式（不污染构建源码树，在上游原样树的临时副本中进行）：

```sh
cp -a <上游原样树> /tmp/rng-old && python3 -c \
  "import patch_ng; patch_ng.fromfile('reports/evidence/rng-old-semantics.diff').apply(strip=1, root='/tmp/rng-old')"
cmake -S /tmp/rng-old -B /tmp/b-old -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release
make -C /tmp/b-old -j1 && /tmp/b-old/src/dawg <上游原样树>/tests/test0.dawg > /tmp/old.out
# 再与旧基准 <上游原样树>/tests/test0.fasta 逐序列求最长公共前缀，即得上表
```

### 确定性与可比口径

刷新基准前先确认输出可复现，避免把抖动写进基准：

- 同 seed 重复运行：输出逐字节一致；
- `-O0`（Debug）与 `-O3`（Release）构建：输出逐字节一致；
- Golden 输出共 555 字节 / 5 条序列 / 比对宽度 105 列。

### 刷新后的真实计数

刷新基准并应用补丁后，在设备上实跑（Conan 干净构建轮，日志见 `reports/conan-create.log`；
该文件在 `.gitignore` 的 `reports/` 规则内，故本地可见、不进 PR diff，关键行已在下文原样引出）：

- `UPSTREAM RUN: test0.dawg records=5 alignment_length=105 raw_bytes=555`
- `UPSTREAM TEST: tests/test0.sh PASS 1/1`
- 上游测试入口计数：TOTAL=1 / PASS=1 / FAIL=0 / SKIP=0 / NOT_RUN=0
  （统计单位＝测试入口脚本；取数证据：`tests/CMakeLists.txt` 为 0 字节、
  `grep -c add_test tests/CMakeLists.txt` = 0，故无 ctest 注册用例）

## 源码修改

- `patches/0001-refresh-stale-test0-golden.patch`：刷新 `tests/test0.fasta` 基准
  （整文件替换，按仓库口径用 delete-item + add-item 形态，`patch_strip: 0`）。
  用 `patch_ng` 库调用在隔离树中验证：应用后该文件与实测输出逐字节一致（555 字节）。
- `patches/0002-cxx17-portability.patch`：`src/tree.h` 4 处 `std::auto_ptr` →
  `std::unique_ptr` 并显式包含 `<memory>`；`src/indel.h` 的 `LinearFunc` 去掉
  C++17 已移除的 `std::unary_function` 基类、自带同名 typedef。
  验证：应用后 C++17 构建通过，且**输出与补丁前逐字节一致**（可移植性补丁不改变行为）。

补丁应用验证（`patch_ng` 库调用，非仅 CLI）：`0001` 2 items/2 hunks、`0002` 2 items/4 hunks，
`strip=0` 与 `strip=1` 分别应用均返回 True，应用结果与包目录内补丁副本逐字节一致。

## 依赖版本

- `bison/3.8.2`（tool_requires，生成 `parser.tab.cpp/hpp`）
- `flex/2.6.4`（tool_requires，生成 `lex.parser.cpp`）
- `m4/1.4.19`（tool_requires，bison 运行时宏库）
- 运行期无第三方依赖（`readelf -dW bin/dawg` 的 `NEEDED` 实测仅两条：`libc++_shared.so` 与 `libc.so`；
  OHOS/musl 下 libm 符号已并入 libc，不单独出现在 NEEDED）

W0 检查：三者均以 `conan install --requires=... --build=never` 在当前 OHOS profile 下
验证 binary 可直接取得（非 `conan list` 推断）。

## 验证结果

```text
# 上游测试（Conan build() 内实跑，干净构建轮）
UPSTREAM RUN: test0.dawg records=5 alignment_length=105 raw_bytes=555
UPSTREAM TEST: tests/test0.sh PASS 1/1 (golden tests/test0.fasta, refreshed by patches/0001)

# test_package（消费者视角，针对已安装制品 bin/dawg）
TEST_PACKAGE_RESULT: PASS 16/16 assertions
```

test_package 断言覆盖：版本横幅自报 `dawg 1.2-release`、帮助文本、test0 配置输出与
golden 逐字节一致、比对结构不变量（5 条等长序列、字母表仅 ACGT-）、同 seed 两次运行
一致、换 seed 必变、Nexus/Phylip/Clustal 三种格式头、GapModel NB/PL/US 合法参数产出、
PL 非法参数被拒、CLI `-o` 写出 golden 内容、运行未改写输入夹具。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/dawg` | 唯一可执行产物（`package_type = "application"`） |
| `share/dawg-1.2-release/examples/*.dawg` | 5 个上游示例配置 |
| `share/dawg-1.2-release/{lambda.pl,outsplit.pl,nexus2fasta.pl,varrep.pl}` | 上游分析脚本 |
| `share/applications/dawg.desktop`、`share/pixmaps/dawg.png` | 桌面集成文件 |
| `doc/dawg-1.2-release/{copying.txt,readme.txt,changelog.txt}` | 上游文档 |
| `licenses/copying.txt` | 许可证（GPL-2.0-or-later） |

## 注意事项

- **不要用 `-o` 传长扩展名**：`-o x.fasta` 会被上游判 `Unknown file format`（见问题 #6）。
- **上游测试只在 `build()` 显式驱动**：`tests/CMakeLists.txt` 是 0 字节空文件，`ctest`
  没有任何用例；若只看 `ctest` 结果会误判"上游无测试"。本包在 `build()` 内实跑
  `tests/test0.sh` 并额外做输出回读断言（防空套件假绿）。
- `tools.build:skip_test` 为真时跳过上游测试执行，这是 Conan 的通用约定；采信轮日志中
  必须能看到 `UPSTREAM TEST: ... PASS 1/1` 才算真实执行。
- 基准刷新写入的是**本版本的确定性输出**，不是"放宽容差"：任何后续真正的输出回归
  仍会被 `tests/test0.sh` 拦住。
