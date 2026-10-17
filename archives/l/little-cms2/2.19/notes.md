# little-cms2 2.19 — HarmonyOS PC (aarch64) 适配笔记

- 上游：Little CMS 2（LittleCMS），Marti Maria Saguer
- 仓库：https://github.com/mm2/Little-CMS
- 版本：2.19（tag `lcms2.19`；头文件 `#define LCMS_VERSION 2190`）
- 许可证：MIT
- 构建系统：autotools（发布 tarball 自带 `configure` / `Makefile.in` /
  `config.guess` / `config.sub`，无需 autoreconf）
- 依赖：**无**（见 §2 的取舍）
- 包形态：`lib/liblcms2.a` + `include/lcms2.h`、`lcms2_plugin.h`
  + `bin/{linkicc,transicc,psicc}`（应用级工具 → 软件级 commands.json，R38）
- 状态：**READY_FOR_HARMONY** —— WSL 侧完整 `conan create` 已跑通（见 §5），
  HarmonyOS 真机尚未执行

## 1. 上游测试清点（R51 三步法第 1 步）

| 项 | 值 | 依据 |
|---|---|---|
| `upstream_test_targets` | **1** | `testbed/Makefile.am:10` `check_PROGRAMS = testcms` |
| `upstream_test_files` | **3** | `testbed/Makefile.am:19` `testcms_SOURCES = testcms2.c testplugin.c zoo_icc.c testcms2.h` |
| `upstream_case_total` | **163** | `testcms2.c` 的 `main()` 注册块中 `Check("…", Fn);` 调用计数 |

`testcms` 的检查框架（`testcms2.c:300`）：成功不打印内容，失败打印 `FAIL!`
并自增 `TotalFail`；`main()` 以 `TotalFail` 作为**退出码**——所以"退出码 0"
就等于全部通过，可直接作为判定依据。

### 两个必须说清楚的数：163 ≠ 157 ≠ 运行数

- 注册数 **163**（源码枚举，可靠）；
- 默认执行 **157**：其中 6 条（`Exhaustive 1D/3D 插值扫描`）位于
  `if (Exhaustive)` 运行时开关之后（`testcms2.c:9706`），而该开关只由
  `./testcms --exhaustive` 打开（`testcms2.c:9651`）；
- 本配方**显式传 `--exhaustive`**，覆盖全部 163 条，不把 157 冒充总数。

## 2. 依赖取舍

| 开关 | 作用 |
|---|---|
| `--without-jpeg` | 跳过 `utils/jpgicc`（需要 libjpeg） |
| `--without-tiff` | 跳过 `utils/tificc`（需要 libtiff） |
| `--without-zlib` | 关闭 ICC profile 压缩，不依赖 zlib |

这三个工具/特性是 lcms2 里唯一需要第三方库的部分；关掉之后本包**零依赖**，
而核心库、完整测试套件与另外三个工具（linkicc / transicc / psicc）不受影响。
已实测：本地构建后 `utils/jpgicc/`、`utils/tificc/` 下只有 Makefile、没有二进制，
而 `linkicc` / `transicc` / `psicc` 正常生成。

## 3. 平台适配点（3 个补丁，均只改生成的 autotools 脚本）

| 补丁 | 文件 | 内容 |
|---|---|---|
| 0001 | `config.guess` | 该版本是 **2018-02-24** 版，结构与 2024 版不同：`Linux\|GNU` 分支的 `dummy.c` 只有 uclibc/dietlibc/gnu 三分支，且**无条件** `#include <features.h>`。补丁把 `__OHOS__ → LIBC=ohos` 放在 `#include` **之前**并用 `#else` 包住原有分支；另加 `*:HarmonyOS:*:* → $UNAME_MACHINE-unknown-linux-ohos`（该版本用 `echo …; exit ;;` 风格） |
| 0002 | `config.sub` | ① 新增 `ohos-linux → linux-ohos` 归一化；② OS 白名单接受 `ohos*`；③ kernel-os 校验接受 `linux-ohos*-` |
| 0003 | `configure` | `config.status` 私有临时目录 `umask 077 → 022`（HMDFS 下 077 目录不可用） |

`__OHOS__` 只出现在 libc 探测分支，是"被测平台自身的能力探测"，不是空壳。

### WSL 侧三元组干跑（实测）
```
config.sub aarch64-unknown-linux-ohos -> aarch64-unknown-linux-ohos
config.sub aarch64-linux-ohos         -> aarch64-unknown-linux-ohos
config.sub aarch64-linux-gnu          -> aarch64-unknown-linux-gnu   (回归不受影响)
config.guess (uname 伪造成 HarmonyOS)  -> aarch64-unknown-linux-ohos
```

## 4. 两个 out-of-source 相关的真坑（都是本地 conan create 抓到的）

### 4.1 `Autotools.make()` 到底在哪运行 —— 取决于有没有 configure
- **有 configure 的项目**（本包）：`Autotools.configure()` 会**从 build 目录**
  调用 `"<source>/configure"`，于是 Makefile 生成在 build 目录（out-of-source），
  随后默认也在 build 目录执行的 `autotools.make()` / `install()` 正好找得到。
  这是仓库里 aalib / a52dec / libpipeline 的标准写法。
- **只有 makefile、没有 configure 的项目**（本批的 triangle / tradcpp / unlzx /
  unzoo）：build 目录里没有 Makefile，必须
  `self.run("make -j1", cwd=self.source_folder)`。

两种情形结论相反，混用必炸——`make: *** No targets specified and no makefile found`。

### 4.2 testbed 的 ICC 数据不会自动进 build 目录
上游 `testbed/Makefile.am:33` 的 `check:` 规则里有：

```make
if [ $(top_srcdir) != $(top_builddir) ]; then \
    cp $(top_srcdir)/testbed/*.ic? $(top_builddir)/testbed; \
fi
```

直接跑 `make testcms` + `./testcms` 会**跳过这一步**，于是测试停在第一条读
profile 的用例：

```
Checking Multilocalized profile ...
File 'crayons.icc' not found
EXIT=1            ← 只跑完 88/163 就退出，且 FAIL! 计数为 0（看起来像"没错但没跑完"）
```

配方里显式做了同样的拷入。**这个坑很阴**：退出码非 0 但 FAIL! 为 0，
若只看 FAIL! 计数就会误判为通过。

## 5. WSL 侧完整 `conan create` 实测（本机原生 Linux profile）

```
little-cms2/2.19: RUN: "<build>/configure" --disable-shared --enable-static --prefix=/ ...
little-cms2/2.19: RUN: make -j1
little-cms2/2.19: RUN: make -j1 testcms
little-cms2/2.19: little-cms2 upstream tests: 163/163 cases ran, 0 FAIL (testcms exit 0)
little-cms2/2.19: Package '65f26548cd6813b23b0051b0e790c19e81a7817f' created
test package: RUN: ./test_lcms2
ok × 11  (all little-cms2 consumer checks passed)
```

### 关于 `-static`
`testbed/Makefile.am:16` 是 `testcms_LDFLAGS = -static`（因为要用未导出的库
内部符号）。已实测 OHOS SDK sysroot 里存在
`.../sysroot/usr/lib/aarch64-linux-ohos/libc.a`，因此 **OHOS 上 `-static` 可用**，
不需要改上游 Makefile。

## 6. test_package（L1 消费者测试，11 项断言）

`test_package/src/test_lcms2.c` 做真实的色彩管理往返：

1. `cmsGetEncodedCMMversion() == LCMS_VERSION`（头/库一致性）
2. 该值 == 2190（2.19）
3. `cmsCreate_sRGBProfile()` 成功
4. sRGB 色彩空间 == `cmsSigRgbData`
5. profile description 标签可读
6. `cmsCreateLab4Profile()` 成功
7. `cmsCreateTransform(RGB_8 → Lab_DBL)` 成功
8. 白点映射到 L* ≈ 100
9. 白点映射到 a* ≈ b* ≈ 0
10. 黑点映射到 L* ≈ 0
11. 白比黑更亮（单调性）

## 7. 待真机验证内容（READY_FOR_HARMONY 清单）

1. `conan create`（clang 15 / aarch64-ohos）：三个补丁后 configure 能否识别
   三元组、HMDFS 下 config.status 临时目录是否可用
2. `make -j1 testcms` 的 `-static` 全静态链接在 aarch64-ohos 上是否成功
   （sysroot 有 libc.a，预期可以）
3. `./testcms --exhaustive` 真机 163 条的执行结果与耗时
4. test_package 的 11 项色彩断言（尤其白点/黑点在 aarch64 浮点下的取值）
5. 软件级 commands.json（linkicc/transicc/psicc）是否被 CI L0k 接受
