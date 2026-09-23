# DRAFT-E596-同 tarball 子包的 N 清点与 openfst 家族配方形态

> Contributor: dsh-agent (E596) | Status: Draft | Updated: 2026-09-20
> Source: libfstngram 1.8.4 HarmonyOS PC 适配（openfst-1.8.4.tar.gz 的第三个子包；前两个
> `libfst` / `libfstconst` 已合并）
> 主题：**同 tarball 子包的上游 N 清点口径**（父 tarball 全量注册面 → 少报 FAIL）×
> **openfst 家族子包的可复制配方形态**（同一 tarball 还有 libfstfar / libfstlookahead）

## 症状

**问题 A（同 tarball 子包的 N 少报）**：子库包（`libgmpxx ⊂ GMP`、`libfstconst ⊂ openfst`、
`libfstngram ⊂ openfst`）如果只按「本包实际构建/运行的用例数」声明上游 N，外部审查
（`pc-pr-review`，脚本化 rule4）按**父 tarball 全量注册面**独立清点，一旦「实测 N > 声明 N」
即判**少报直接不通过**。实测案例：libgmpxx 声明自身 22 个用例，审方按 GMP 父 tarball 注册面
量出 190/200 → FAIL；jsoncons 声明框架实际运行 case 869，审方按源码 `TEST_CASE` 宏量出 907 → FAIL。
**子包自身没有独立上游仓库**，清点面和主包完全相同，因此"只声明自身子集"永远小于审方读数。

**问题 B（openfst 家族子包的上游测试假败）**：openfst-1.8.4 的 `src/test/` 是**整体**测试
（`fst_test`、`weight_test`、`algo_test_*`），测 VectorFst、各 arc type 与各扩展的运行时注册。
链接 `libfst.a` 静态库时链接器按需取对象文件，`fst-types.o` 里的 `static FstRegisterer`
（`REGISTER_FST` 宏，`fst/register.h:119`）无强引用被剔除 → `FstRegister` 表为空 →
`Fst::Read` 走 `GenericRegister::GetEntry` 的 `dlopen("<type>-fst.so")` 回退
（`fst/generic-register.h:96-100`）→ 报 `Fst::Read: ... vector-fst.so` 崩溃式失败，
或 `make check` 在精简构建（`--disable-bin` / 关掉扩展）下整组假败。

**问题 C（OHOS 上 `make install` 必失败）**：worker 无 GNU coreutils `install`，toybox
`install -c` 在 HMDFS 上直接 `Error 64`；`INSTALL_DATA = ${INSTALL} -m 644` 还会走 `chmod`，
HMDFS 不支持 chmod（E087）。

## 根因

- **A**：N 的定义是「上游测试总数」，对子包而言上游 = **父 tarball**。审方按父 tarball 的
  构建注册面（automake `TESTS`/`check_PROGRAMS`、CMake `add_test`、Bazel `cc_test`、
  `tests/*.c` 源文件数）取数，与被审包自己构建了哪些无关。子包声明自身子集必然少报。
- **B**：`REGISTER_FST` 是静态对象注册（构造即注册），静态库按需链接会丢弃"无强引用"的
  目标文件；`--whole-archive` 是唯一能在静态链接下保留注册表的办法。openfst 的
  `Fst::Read` 对未注册类型还有 `dlopen("<type>-fst.so")` 回退，所以缺注册表时的报错
  指向 `.so` 找不到，极易被误判成"扩展没编"。
- **C**：toybox 的 `install` 是精简实现，`-c`（copy）选项在 HMDFS 的权限映射下失败；
  autotools 生成的每个子 Makefile 都把 `INSTALL` 变量写死成 configure 探测到的那个命令。

## 处置（可复用）

### A. 同 tarball 子包的 N 清点：四个口径全数、取用例/注册类最大值

对**父 tarball**逐项清点并留证（本次 openfst-1.8.4 实测）：

| 口径 | 读数 | 取数命令 |
|------|------|----------|
| automake 注册（`check_PROGRAMS`/`TESTS`） | 7 | `grep -rn 'check_PROGRAMS\|^TESTS' --include=Makefile.am .` |
| Bazel 注册（`cc_test`，含列表推导） | 7 | `grep -n 'cc_test' BUILD.bazel` + 展开 `for weight in [...]` |
| 测试源文件数（`tests/*.c(*)`） | 3 | `ls src/test/*.cc` |
| **用例/宏分支数（→ 主 N）** | **10** | 2 个独立测试程序 + `algo_test.cc` 的 8 个 `TEST_*` 分支 |
| 断言（`CHECK` 宏调用数，**另一单位，只披露不并入 N**） | 260 | `grep -o 'CHECK' src/test/*.cc src/include/fst/test/*.h \| wc -l` |

规则：
1. **主 N 取"用例/注册类"口径中的最大值**（openfst 取 10）；断言属另一单位，只披露；
2. 每个差额**逐项归因**（openfst：注册 7 = Bazel 7 一致；另 3 个 `TEST_*` 分支
   `TEST_LEFT_STRING`/`TEST_RIGHT_STRING`/`TEST_GALLIC` 在两套构建系统里**都没有注册项**，
   但 `WeightGenerate<StringWeight>/<GallicWeight>` 特化齐备（`fst/string-weight.h:514/667`），
   可编译可运行 → 补编进 `build()`，让 N′=N=10，避免"未运行"与"少报"两头挨打）；
3. **首行行值 = 合计**：上游统计表把全部用例并进「单元测试」首行，其余行填 0
   （审方按**首行行值**取声明 N，"合计"说明段不采信；libemf 实测）；
4. 正文、`manifest.yaml`、`test_package/MANIFEST.yml`、`notes.md`、`reports/test-report.md`
   **五处同源同单位**同数，不要只改正文。

### B. openfst 家族子包配方形态（libfst / libfstconst / libfstngram / libfstfar / libfstlookahead 通用）

```python
# 1) 源码与补丁三者完全相同（同一 tarball、同一 sha256）
#    openfst-1.8.4.tar.gz  sha256 a8ebbb6f3d92d07e671500587472518cfc87cb79b9a654a5a8abb2d0eb298016
#    0001-config.guess.patch / 0002-config.sub.patch / 0003-configure.patch / 0004-flags-help-exit.patch
# 2) configure：只开本扩展 + --enable-bin（上游默认全部扩展 = no）
tc.configure_args.extend([
    "--enable-ngram-fsts",      # 本包：libfstngram.so.26 + lib/fst/ngram-fst + ngram 头文件
    "--enable-bin",             # libfstscript + 37 个 bin：上游测试需要完整注册表
    "--enable-static", "--disable-shared",
])
# 3) make：仓库口径 -j1/-j2（os.cpu_count()=20 但 affinity=8；conan create 不传 tools.build:jobs）
autotools.make(args=["-j2"])
# 4) 手动编译上游测试（make check 会假败）：
#    clang++ -I<src>/include -DHAVE_CONFIG_H -stdlib=libc++ -std=c++17 -fno-exceptions \
#            -Wno-deprecated-declarations -fPIC -O3 <test>.cc \
#            -Wl,--whole-archive <build>/src/lib/.libs/libfst.a -Wl,--no-whole-archive -lm -ldl
# 5) 测试程序随包安装到 <pkg>/_ohos_tests/，用 os.open(..., 0o755) 落盘（HMDFS 无 chmod，
#    普通 open("wb") 得 0644 → 执行报 Error 126），test_package 用 `sh <script>` + 直接执行
# 6) package_info：cpp_info.libs=["<本扩展>"]；runenv LD_LIBRARY_PATH 前置 lib 与 lib/fst
#    （Fst::Read 的 dlopen 回退在这些目录找 <type>-fst.so）
```

### C. OHOS `make install` shim

配方 `build()` 里写一个 install shim（`cp -f` 复制 + `mkdir -p` 建目录 + chmod 容错跳过），
再 `os.walk` 所有 `Makefile`，把 `INSTALL = <toybox install -c 路径>` 行改成
`INSTALL = <shim 绝对路径>`（`INSTALL_DATA`/`INSTALL_PROGRAM` 引用 `${INSTALL}`，自动跟着重算）。
**不要**靠 PATH 前置替换（conan build env 会覆盖 PATH），也不要给 `Autotools.install(args=...)`
传 `'INSTALL_DATA=$(INSTALL)'`（bash 会先做命令替换，参数被吃空 → `Error 126`）。

## 验证

- `conan create archives/l/libfstngram/1.8.4 -pr:h=<abs>/ci/conan/profiles/ohos-aarch64
  -pr:b=<同一 profile> --build=missing --user=ohpcd --channel=stable`：干净轮
  （`Apply patch` + `Calling build()` + `RUN: make` 三类标志齐全）真机通过；
- `test_package` 真机执行包内 `_ohos_tests/` 的 **10/10** 上游用例
  （`HMBS_UPSTREAM_TEST_RESULT {"discovered":10,"executed":10,"passed":10,"failed":0,"skipped":0}`）；
- 清点命令与读数：见上表；`git apply --check` 逐条验证 4 个补丁对原 tarball 可应用；
- 同 tarball 一致性：三包 `conandata.yml` 的 url/sha256 完全相同，仅
  `configure_options` 与 `cpp_info.libs` 不同。

## 适用边界

- A：所有「子库/子包与主包共用一个上游 tarball」的包（libfst*、libgmpxx、libfstconst…）。
  主包与子包共享清点面；N 必须 ≥ 父 tarball 任一注册类口径的读数。
- B/C：openfst 1.8.x 家族（同一 tarball 的 `libfstfar`、`libfstlookahead` 可直接套用，
  仅把 `--enable-<扩展>-fsts` 与 `cpp_info.libs` 换掉），以及任何「静态库 + 静态注册表 +
  `dlopen` 回退」形态的上游（如 libyal 家族的部分扩展）。
- 不适用：上游确有独立仓库的子包（清点面就是自己的仓库）。

## 查重差异

- 与 E011/E087/E182 不同：那三条是 HMDFS umask / chmod / install 单点缺陷；本条的
  增量是**同 tarball 子包的 N 清点口径**（A 段）与**整套 openfst 家族配方形态**（B/C 段），
  三个子包可直接复制。
- 与 `DRAFT-jsoncons-1.9.0-test-count-and-baseline-noise.md` 不同：那条是**同一包内**
  「源码宏 907 vs 框架注册 869」的差额归因；本条是**跨包（父 tarball vs 子包）**清点面的
  取值，且给出"补编未注册分支使 N′=N"的收口做法。
- 与 `DRAFT-10251-libnfc-tools-1.8.0-tools-subpackage-identification.md` 不同：那条判"是不是子包"；
  本条判"子包的 N 从哪里取、取多大"。
