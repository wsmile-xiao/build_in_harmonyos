# pd-flext 0.6.4 — HarmonyOS PC (OHOS aarch64) 适配笔记

## 1. 这是什么软件

`pd-flext` 是 **flext**：Pure Data (Pd) 与 Max/MSP 外接对象的 **C++ 框架**。
它不是一组外接对象，而是外接对象所依赖的**框架库**：开发者继承
`flext_base` / `flext_dsp` 等基类写类，链上 flext 框架库，编出一个
`<class>.pd_linux` 交 Pd 在打补丁时 `dlopen` 加载。

- 上游发布形态：`pd-flext_0.6.4.orig.tar.xz`（Debian 官方源包名 `pd-flext`；
  上游主页 <http://grrrr.org/research/software/flext/>）。
- 构建系统：两套并行——autotools（`configure.ac` + `Makefile.am`，**不含**生成的
  `configure`）与上游自带 shell 构建系统（`build.sh pd gcc`）。
- 可选支持：SndObj（`--with-sndobjdir`）与 STK（`--with-stkdir`）**均为可选**，
  不启用时 `flsndobj.cpp`/`flstk.cpp` 不参与编译，因此本适配**无三方依赖**。
- 许可：GPL-2.0-or-later（`license.txt`）。

## 2. 上游测试清点（R51）

上游**没有任何自动化测试**：发布包只有构建脚本、框架源码与 `tutorial/` 下
若干示例外接对象；`Makefile.am` 的 `SUBDIRS = source tutorial` 只有编译目标，
没有 `check` 目标，无 `tests/` 目录。结论：上游测试用例数 **N = 0**，无可移植用例；
由本次适配新增**鸿蒙特有消费者测试**（见第 5 节，3 项断言）。

## 3. 构建：直接编译框架库（而非 autotools / build.sh）

两套上游构建系统对本环境都不合适：

- **autotools**：orig 包不含生成的 `configure`，需 `autoreconf -fi`（依赖
  autoconf/automake/libtool tool_requires，属 E178 族）；且 `config.guess` 不认
  HarmonyOS（E007 族），要显式 `--build/--host`。可用但笨重。
- **build.sh pd gcc**：依赖一套自带的 `buildsys/*.inc` + `config-*.def`，写死
  `PDPATH`/`FLEXPTPREFIX`，并用 `install`/`ldconfig`，在 HMDFS 上不友好。

本适配改为**直接编译 flext 核心**（即 `source/Makefile.am` 里 `SRCS_FLEXT` 列的 24 个
`.cpp`），用与上游 `pd-flext.pc` 相同的编译期选择符：

```
-DFLEXT_SYS=2 -DFLEXT_SHARED -DFLEXT_EXPORTS -std=c++17 -fPIC -O2
-I<source> -I<pd-api>/src
clang++ -shared -Wl,-soname,libflext-pd.so.0.6 ... -lpthread
```

- `-DFLEXT_SYS=2`：`flprefix.h` 依赖它区分 Pd/Max；不定义会 `#error`。
- `-DFLEXT_SHARED`：选定“共享 + 多线程”变体；见第 6 节 ABI 说明。
- `-DFLEXT_EXPORTS`：库侧导出（消费者侧**不能**带 `FLEXT_EXPORTS`）。
- `-I<source>`：flext 头之间的相对包含。

### 3.1 坑：`ld.lld` 不在编译器同级目录

OHOS clang（Harmonybrew `llvm 23.1.1`）的 `InstalledDir` 下**没有** `ld.lld`；
真正的链接器在 `ohos-sdk@*/native/llvm/bin/ld.lld`。直接用
`$HOME/.harmonybrew/bin/clang++` 链接会报：

```
clang++: error: unable to execute command: posix_spawn failed: No such file or directory
```

Conan 的 `ohos-aarch64` profile 已在 `[buildenv]` 里把
`.../opt/ohos-sdk@26.0.0.18/native/llvm/bin` 加入 `PATH`（并设 `LD=ld.lld`），
所以配方里所有编译/链接都走 `env="conanbuild"` 即可，不需要手工改 PATH。

## 4. 依赖与头文件

flext 的头 `flext.h` 包含 `<m_pd.h>`（`flstdc.h`），此外
`flbase.cpp`/`flattr_ed.cpp` 还包含 **Pd 内部头** `<g_canvas.h>` 和 `<m_imp.h>`
（不只是公开的 `m_pd.h`）。来源有两处：

1. 制品仓的 `puredata/0.54.1` 是 **application**，虽然 package folder 里物理存在
   `include/m_pd.h` 与 `include/pd/{g_canvas.h,m_imp.h,...}`，但
   `package_info()` 把 `cpp_info.includedirs` 置空，**拿不到** `-I`。
2. 因此本配方在 `source()` 里额外拉取**同一上游版本** `pure-data 0.54-1`
   （`sha256` 与 `puredata/0.54.1` 相同）到 `pd-api/`，构建时 `-I pd-api/src`，
   并把公开 API 头随包安装到 `include/puredata/`，供下游外接对象编译使用。

> 只按公开 `m_pd.h` 判断“头够了”会漏：flext 还需要 `g_canvas.h` / `m_imp.h`
> 这些内部头；缺任一个都会在编译到 `flbase.cpp`/`flattr_ed.cpp` 时才炸。

## 5. 产物

| 路径 | 说明 |
|------|------|
| `lib/libflext-pd.so.0.6.4` | 框架库实体（ELF `ET_DYN`，aarch64） |
| `lib/libflext-pd.so.0.6` | 运行时 soname（`DT_SONAME`） |
| `lib/libflext-pd.so` | 开发链接名（`-lflext-pd`） |
| `include/flext/*.h`、`*.cpp`、`lockfree/*.hpp` | flext 头（含 `FLEXT_INLINE` 用的 `.cpp`） |
| `include/puredata/*.h` | Pd 公开/内部 API 头（`m_pd.h`/`g_canvas.h`/`m_imp.h`…） |
| `lib/pkgconfig/pd-flext.pc` | 携带 `Cflags/Libs`（含 `-DFLEXT_SYS=2 -DFLEXT_SHARED`） |

`shared` 选项目前只产出共享库；`package_type = "library"`，无 `bin/`，故无需
`commands.json`（L0k 判为库类型）。

## 6. 两个真实坑与补丁

### 6.1 `PDGUI_DELETEKEY` 宏形参错用（`0001`）

`source/flext.cpp:24-28`：

```c
#if PD_MAJOR_VERSION > 0 || PD_MINOR_VERSION >= 55
#define PDGUI_DELETEKEY(key) pdgui_stub_deleteforkey(key)
#else
#define PDGUI_DELETEKEY(cmd) gfxstub_deleteforkey(key)   // ← 应为 cmd
#endif
```

Pd < 0.55 分支的宏形参叫 `cmd`，宏体却用字面量 `key`。`pure-data 0.54-1`
(`PD_MINOR_VERSION = 54 < 55`) 走该分支，调用点 `PDGUI_DELETEKEY(thisHdr())`
展开成 `gfxstub_deleteforkey(key)` → `error: use of undeclared identifier 'key'`。
补丁把宏体改成使用形参 `cmd`（等价于上游对新版 `key` 分支的写法）。

### 6.2 OHOS 无 `pthread_cancel`（`0002`）

OHOS 的 `<pthread.h>` 定义了 `PTHREAD_CANCELED`，却**没有声明 `pthread_cancel`**
（同 musl：假装有宏、没有函数）。`source/flthr.cpp` 的线程超时硬终止回退路径
直接调用它 → 编译期 `use of undeclared identifier 'pthread_cancel'`。补丁把该调用
用 `#if defined(FLEXT_HAVE_PTHREAD_CANCEL)` 包起来（不定义即走“无法强制终止”分支，
协作式停止逻辑仍保留）。这与 E085/E127/E407/`HAVE_PTHREAD_CANCEL` 属同一
“bionic/musl 无 pthread 取消”族（路径 A，非新知识）。

## 7. 消费者测试（3 项断言，鸿蒙特有）

上游无测试可移植，新增 `test_package/`：

1. 用安装后的 **pd-flext**（框架库 + 头）编译一个真实 flext 外接
   `flextest`（`test_flext.cpp`，`FLEXT_NEW_1`），编译期带 `-DFLEXT_SHARED`；
2. 用真机 OHOS 的 `pd`（来自 `puredata/0.54.1`）无头加载该外接并驱动：

| 断言 | 期望 |
|------|------|
| 构造 `[flextest 100]` | `FLEXT_TEST_INIT: 100` |
| 送入 float `5`（100+5） | `FLEXT_TEST_RESULT: 105` |
| 结果到 `[print]` | `FLEXT_TEST: 105` |

真机 `conan create`：`CREATE_RC=0`，消费者 **3/3**。

## 8. 环境 / 验证

- 交叉工具链：OHOS clang（Harmonybrew），target `aarch64-unknown-linux-ohos`，
  profile `$HOME/.conan2/profiles/ohos-aarch64`（host/build 同 profile，与 CI 一致）。
- `conan create archives/p/pd-flext/0.6.4 --name=pd-flext --version=0.6.4
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 -pr:b=$HOME/.conan2/profiles/ohos-aarch64
  --build=missing` → 成功，消费者 3/3。

---
**编译结束**: 2026-10-12
**最终状态**: built
