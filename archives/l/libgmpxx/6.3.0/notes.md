# libgmpxx 6.3.0 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 任务定位：libgmpxx 是什么

libgmpxx 不是独立上游项目，是 GMP 源码树内 **C++ 绑定**的打包名：

- 公开头：`gmpxx.h`（mpz_class / mpq_class / mpf_class / gmp_randclass）
- 非内联实现：`cxx/*.cc`（dummy + is*/os* 等 11 个翻译单元，含 ostream 插入器）
- 源码与 gmp 6.3.0 为**同一份官方 tarball**（sha256 `a3c2b8…8898`，与 archives/g/gmp/6.3.0 conandata 逐字一致）

## 与既有 gmp 包的生态分工（W0b 历史核验）

仓库已有两版 gmp（见 archives/g/gmp/manifest.yaml 与 6.3.0.1/notes.md）：

- `gmp/6.3.0`：`--disable-shared` 纯静态 C 包，**无 --enable-cxx**，不产 gmpxx.h / libgmpxx
- `gmp/6.3.0.1`：同一 tarball + `--enable-cxx` + shared=True 的**整包**（libgmp.so + libgmpxx.so + gmpxx.h）

本包 `libgmpxx/6.3.0`（积分赛任务目标，C++ 绑定独立成包）：require `gmp/6.3.0`（静态 C 库），
构建 `--enable-cxx` 完整树后**只安装 gmpxx.h / libgmpxx.a / libgmpxx.pc**，裁剪 libgmp 本体：

- C 接口下游继续用 gmp/6.3.0；C++ 下游可选 libgmpxx/6.3.0（静态绑定包）或 gmp/6.3.0.1（共享整包）
- 不重复安装 libgmp，避免双份 libgmp 符号冲突；不提供共享构建路径——配方按 Conan 2 要求
  声明 `shared` 选项（默认 False），`shared=True` 在 configure() 阶段即抛
  ConanInvalidConfiguration 指向 gmp/6.3.0.1，不用静默无效选项冒充共享支持

## 关键适配事实

1. **cxx/*.cc 全部 include 内部头 gmp-impl.h**（依赖 config.h 与内部符号声明），
   无法绕过 configure 只挑头文件打包——必须完整 configure 后随树构建。
2. 配置与 gmp/6.3.0 完全同构 + `--enable-cxx`：`--enable-static --disable-shared --with-pic ABI=64`。
   config.h 同源 ⇒ cxx 对象引用的 libgmp 内部符号（`__gmp_doprnt_*` 等）与依赖包 ABI 一致。
3. 复用 gmp/6.3.0 的 3 个可移植性补丁（configfsf.guess/sub 识别 OHOS、configure 临时目录用
   TMPDIR），内容零改动；补丁无 `__OHOS__` 平台宏（PF5/R8 口径）。
4. **make -j1**：HMDFS 禁止 make 4.4 jobserver 的 mkfifo（实测 `jobserver mkfifo: Operation
   not permitted`），与 gmp 配方 -j1 先例一致。
5. package 阶段删除 `lib/libgmp.a`、`include/gmp.h`、`*.la`、`lib/pkgconfig/gmp.pc`
   （.la 烤死 libdir 绝对路径会把下游 libtool 引到 `//lib` 死路，gmp/6.3.0.1 同法删除）。

## 上游测试（R51 三步法）

1. **清点（N = 上游总数，框架注册口径）**：GMP 6.3.0 官方 tarball 的 `tests/**` 各
   `Makefile.am` 的 `check_PROGRAMS` 注册项共 **200** 个：

   | 目录 | check_PROGRAMS | 其中 `t-*` | 本次运行 |
   |------|---------------:|-----------:|---------:|
   | tests/（根） | 8 | 8 | 0（NOT_RUN） |
   | tests/cxx | 22 | 22 | **22（全部 PASS）** |
   | tests/misc | 3 | 3 | 0（NOT_RUN） |
   | tests/mpf | 28 | 27 | 0（NOT_RUN） |
   | tests/mpn | 53 | 52 | 0（NOT_RUN） |
   | tests/mpq | 15 | 13 | 0（NOT_RUN） |
   | tests/mpz | 64 | 58 | 0（NOT_RUN） |
   | tests/rand | 7 | 7 | 0（NOT_RUN） |
   | **合计** | **200** | **190** | **22** |

   自洽式：`TOTAL 200 = PASS 22 + FAIL 0 + SKIP 0 + NOT_RUN 178`。

   - 190 个 `t-*` 命名项 = 外部审查的「实测 N=190」口径（逐字映射）；本表取候选数法
     **最大值** 200，多出的 10 个具名项为 mpz 的 reuse/dive/dive_ui/convert/io/logic、
     mpq 的 io/reuse、mpn 的 logic、mpf 的 reuse——同样在 `check_PROGRAMS` 内、随
     `make check` 运行，与 190 项同单位，不是另一套口径。
   - 范围边界（不计入 N）：`tests/devel` 只有 `EXTRA_PROGRAMS`（不属 `make check`）；
     `mini-gmp/tests` 的 31 个 `t-*` 用独立手写 Makefile + `run-tests`（非
     `check_PROGRAMS` 注册、主 configure 不构建）。
   - 取数命令（设备可直接执行，`S` = GMP 官方 tarball 解包根，sha256 `a3c2b802…8898`）：

     ```sh
     python3 -c "
     import os,re
     S='<gmp-6.3.0 解包根>'; tot=0; t=0
     for dp,_,fs in os.walk(os.path.join(S,'tests')):
         if 'devel' in dp.split(os.sep) or 'Makefile.am' not in fs: continue
         x=open(os.path.join(dp,'Makefile.am')).read().splitlines()
         for i,l in enumerate(x):
             if re.match(r'\s*check_PROGRAMS\s*=',l):
                 b=l.split('=',1)[1]
                 while b.rstrip().endswith('\\'): i+=1; b=b.rstrip()[:-1]+' '+x[i]
                 p=[w for w in b.split() if '$' not in w]; tot+=len(p)
                 t+=len([w for w in p if w.startswith('t-')]); break
     print('TOTAL=%d T_STAR=%d'%(tot,t))"
     ```

     实测输出：`TOTAL=200  T_STAR=190`。
2. **实测（N′ = 本次实际运行数）**：**22/22 全部通过**（2026-09-19，本机 OHOS 设备）。
   22 = `tests/cxx` 全部程序，即本包交付面（C++ 绑定）对应的上游测试。方法：设备 HMDFS
   的 `getcwd(2)` 间歇 EFAULT 使 libtool 链接测试可执行文件确定性失败（`make -C
   tests/cxx check` 在 t-binary 链接处 Error 1，单独重放复现），故用直接静态链接
   harness——以与 configure 相同的编译器/宏，把 22 个上游测试源逐一与同一构建树的
   `libgmpxx.a`/`libgmp.a`/`libtests.a` 链接后运行；逐程序 PASS 转录与原件哈希见
   reports/upstream-tests-cxx-log.md。
3. **未运行 178 项按 NOT_RUN 记账、不写 PASS**：其余 178 个上游程序（tests/ 根 8、
   misc 3、mpf 28、mpn 53、mpq 15、mpz 64、rand 7）的测试对象是 **libgmp C API**，
   不在本包 install 面——`package()` 裁剪 `libgmp.a`/`gmp.h`/`gmp.pc`，C 库由
   `gmp/6.3.0` 包交付（本包 require 它，`visible=True`）。替代验证：上述 22 个 C++
   程序全部链接**同源** `libgmp.a` 实跑通过，绑定层对 C API 的调用在链接期与运行期被
   完整覆盖。本条**不是"测试被删减"**，而是同一 tarball 内子库独立成包的交付面不同
   （同型先例：zfp 以审方 N 口径入表、通过率另按执行口径并显式换算）。
4. **回填**：PR 按实跑结果回填 N/N′/通过率，不用占位符。

## test_package（消费者视角）

`test_gmpxx.cpp` 5 项实质断言（比对计算结果本身，非链接空转）：

- mpz 大整数平方：12345678901234567890^2 逐位比对
- 2^100 的十进制位数 == 31
- mpq 1/3 + 1/6 == 1/2
- mpf 0.5 * 6 == 3
- operator<< 非内联插入器输出（缺 libgmpxx 链接时无法通过链接阶段）

## 版本号

上游即 6.3.0（GMP 版本号），首次适配无后缀；后续适配修复按 `.N` 递增（R37）。

## L5 基线口径说明（2026-09-19）

本包为纯静态库，L5 基线由 `reports/baseline.json` 承载（8 个条目：`conaninfo.txt`、
`conanmanifest.txt`、`include/gmpxx.h`（129502 B）、`lib/libgmpxx.a`（46468 B，
sha256_16 `1f36e7bd6806f4ac`）、`lib/pkgconfig/gmpxx.pc`、`share/info/gmp.info*`），
与 20:47 干净轮的安装树逐项一致；20:57 轮（finish 内嵌验证）报
`L5: ✅ PASS（产物与基线完全一致，8 个文件）`。

本轮另一次同源构建（20:58–21:07，finish 内嵌 W3）产出的 `lib/libgmpxx.a` 与上述基线
**字节级不同**（sha256 `05e4d2f8…`，大小同为 46468 B）——即同一配方/源码的两次构建
并非字节可复现，差异位于 ar 归档成员头（时间戳类元数据）。更早一轮曾按工具口径删除并
重立基线；该轮旧基线未留副本，其差异成因**无法用副本复核**，故此处只记录可核对的两次
构建实测值，不把历史解释当作已证事实。
