# DRAFT-PD-EXTERNALS：Pd externals 不链接 libpd，靠 dlopen 绑 Pd 运行时符号（pd-log 0.1）

- **来源**：pd-log 0.1 适配（2026-10-03），HarmonyOS PC / OHOS aarch64，零补丁；
  2026-10-08 增补真机 dlopen 失败形态（CI #73602）
- **报错特征**：`undefined symbol: logpost`｜`dlopen failed: undefined symbol`｜
  `Error relocating <lib>: <sym>: symbol not found`｜
  产物落在 `lib/pd-externals/log/log/`（多一层库名）
- **分类**：ohos / conan / build-system / testing / puredata
- **适用**：所有要打成 Conan 包的 Pure Data externals 库（pd-log、pd-creb、pd-smlib、pd-compos…）

## 现象

1. 想给一个「不含可执行文件、也没有可链接库」的 Pd externals 包写自动化测试。
   测试二进制不导出任何 Pd 符号就直接 `dlopen()`：在 glibc 上 `RTLD_LAZY`
   能过（假绿），`RTLD_NOW` 必挂 `undefined symbol: logpost`；在 **OHOS 真机**
   上 musl 没有惰性绑定，`RTLD_LAZY` 一样挂：
   `dlopen failed: Error relocating logpost.pd_linux: gensym: symbol not found`
   （CI #73602，5 个 externals 全部同报错，而产物本身完全正确）。
2. 配方里传 `objectsdir=/lib/pd-externals/log`，结果产物落在
   `lib/pd-externals/log/log/`，与 Pd 的加载路径对不上。

## 根因

Pd externals 是**运行时插件**，由 Pd 进程 `dlopen()`，并不链接 libpd。
以 pd-log 0.1 / puredata 0.54.1 实测（`readelf --dyn-syms` + `readelf -r`）：

```
$ llvm-readelf --dyn-syms lib/pd-externals/log/debug.pd_linux | grep -E 'debug_setup|logpost|UND'
  19: ... NOTYPE  GLOBAL DEFAULT  UND logpost      ← 18 个导入之一
  22: ... FUNC    GLOBAL DEFAULT 11 debug_setup    ← 唯一导出
$ llvm-readelf -d lib/pd-externals/log/debug.pd_linux | grep NEEDED
  (NEEDED)  Shared library: [libc.so]                                ← 没有 libpd
$ readelf -r lib/pd-externals/log/logpost.pd_linux
  .rela.dyn: R_AARCH64_GLOB_DAT  s_        ← 数据重定位：任何 libc 加载期必解析
  .rela.plt: 21 × R_AARCH64_JUMP_SLOT      ← 其中 17 个强绑定的 Pd 函数
```

每个 external 除 `<name>_setup` 外导入 **17 个 Pd API 函数**
（`gensym`、`class_new`、`class_doaddfloat`（`class_addfloat` 的宏展开）、
`class_addbang`、`class_addpointer`、`class_addanything`、`pd_new`、`logpost`、
`atom_getfloatarg`、`atom_getsymbolarg`、`binbuf_new/add/gettext/free`、
`resizebytes`、`freebytes`、`floatinlet_new`）**加 1 个数据符号 `s_`**
（`t_symbol` 对象，externals 取 `&s_` 当默认 tag）。
这些符号全部由 Pd 进程提供（pd 用 `-rdynamic` 链接、把它们发布进进程全局
符号表；`logpost(3)` 声明在 puredata 的 `m_pd.h:579`），不由 DT_NEEDED 满足。
加载器行为分两层：

- `s_` 走 `R_*_GLOB_DAT`：**急切重定位，glibc/musl 都在 dlopen 时刻解析**，
  宿主不导出它，任何 libc 都挂；
- 17 个函数走 `R_*_JUMP_SLOT`：glibc 在 `RTLD_LAZY` 下推迟（所以本地测试
  能假绿），**OHOS musl 没有惰性绑定，`RTLD_LAZY` 等价 `RTLD_NOW`**，
  加载时刻必须全部解析（与 E545 kamailio 模块的结论一致）。

**所以「测试不扮演 Pd 宿主」在 OHOS 上必然挂，而产物没有缺陷。**
`RTLD_LAZY` 只在 glibc 上掩盖问题——本地绿 ≠ 真机绿。

第二，stock 的 Pd "Makefile template" 里：

```make
objectsdir = $(pkglibdir)                      # pkglibdir = $(prefix)/lib/pd-externals
libdir_install: $(INSTALL_DIR) $(DESTDIR)$(objectsdir)/$(LIBRARY_NAME)
```

install 规则**自己会追加库名**，所以配方只能传父目录。

## 处置

1. **测试二进制扮演 Pd 宿主**：定义 externals 导入的全部符号（17 个函数桩 +
   `s_` 数据对象——用 `readelf` 从产物枚举，别凭记忆），编译命令加
   `-rdynamic` 发布进进程全局符号表（与 pd 本尊链接方式一致），然后对每个
   打包的 `*.pd_linux` 做 `dlopen(RTLD_NOW)` + `dlsym("<name>_setup")`
   并断言非空。`RTLD_NOW` 让 glibc 路径也做全量解析，本地与真机行为对齐。
   同时断言 `EI_CLASS == ELFCLASS64`、`e_machine` 等于目标值
   （183 = EM_AARCH64）。期望机器码由配方传入（`armv8 → 183`、
   `x86_64 → 62`），不要写死。
2. **同时断言安装路径**是 `<package>/lib/pd-externals/<name>/`，与 Pd 的搜索路径一致。
3. **配方传父目录**：`objectsdir=/lib/pd-externals`（不要带库名）。
4. 顺带：模板 install 规则里的 `strip` 在 OHOS 上要短路（`STRIP=:`），
   否则 OHOS clang wrapper 写入的 ELF code signature 失效
   （abduco / jamnntpd / tty-clock 同一处置）。

## 预防

- 遇到 `undefined symbol: logpost` / `Error relocating ...: gensym: symbol
  not found` 先跑 `readelf --dyn-syms` + `readelf -r`，确认符号是 `UND`
  而不是「链接漏了」——Pd externals 本来就该是 `UND`；再数清楚导入集合。
- **在 OHOS 上验证 dlopen 类测试，宿主符号契约必须由测试自己满足**；
  不要拿 glibc 的 `RTLD_LAZY` 通过当证据——musl 无惰性绑定，
  `RTLD_LAZY` 在真机上一文不值（本地假绿、真机真红，pd-log CI #73602 实证）。
- 断言要落在**产物本体**（ELF 头 + dlopen/dlsym）而不是「文件在不在」：
  文本占位、宿主架构产物都能骗过 `find` 式测试。
- 若目标机跑不了测试二进制（本地无 qemu binfmt、设备不可用），
  降级成静态 ELF 断言并**在 PR 里写明覆盖度下降**，不要含糊宣称跑过动态加载。

## 关键证据（可复现）

```bash
# 产物形态
llvm-readelf -h  lib/pd-externals/log/logpost.pd_linux | grep -E 'Class|Type|Machine'
#   ELF64 / DYN (Shared object file) / AArch64
llvm-readelf -d  lib/pd-externals/log/logpost.pd_linux | grep -E 'NEEDED|RUNPATH'
#   NEEDED libc.so ；RUNPATH [$ORIGIN]
# 宿主契约（测试必须满足的导入集合）
readelf -r       lib/pd-externals/log/logpost.pd_linux   # GLOB_DAT s_ + 17 JUMP_SLOT
```

- 落地配方：`archives/p/pd-log/0.1/conanfile.py`
- 落地测试：`archives/p/pd-log/0.1/test_package/pdlog_dlopen_test.c`
  （桩宿主 + `-rdynamic` + `RTLD_NOW`；每对象 3 条断言：ELF64+架构、
  dlopen、dlsym，5 个对象共 15 条）
