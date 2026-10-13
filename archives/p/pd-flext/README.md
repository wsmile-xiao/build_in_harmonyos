# pd-flext — Pure Data 的 C++ 外接框架（flext）

`flext` 为 Pure Data（Pd）与 Max/MSP 的外接对象提供统一的 **C++ 抽象层**：
开发者继承 `flext_base`（消息）或 `flext_dsp`（信号）等基类写类，链上框架库
`libflext-pd.so`，编出 `<class>.pd_linux`，由 Pd 在打补丁时 `dlopen` 加载。

- 上游：<http://grrrr.org/research/software/flext/>
- 许可：GPL-2.0-or-later

## 用法

```sh
# 用 pkg-config 取编译期 ABI 选择符与包含路径
pkg-config --cflags --libs pd-flext
# 编译一个 flext 外接（示意）
clang++ -shared -fPIC -DFLEXT_SYS=2 -DFLEXT_SHARED \
        $(pkg-config --cflags pd-flext) myobj.cpp \
        $(pkg-config --libs pd-flext) -o myobj.pd_linux
# 运行时让动态加载器找到框架库
LD_LIBRARY_PATH=<pkg>/lib pd -path <objects-dir> -open mypatch.pd
```

## OHOS 适配要点

- 上游 autotools（orig 无生成的 `configure`）与自带 `build.sh` 都不适合本环境，
  改为**直接编译** `source/Makefile.am::SRCS_FLEXT` 的 24 个 `.cpp`，用上游
  `pd-flext.pc` 同款编译期选择符 `-DFLEXT_SYS=2 -DFLEXT_SHARED -DFLEXT_EXPORTS`。
- `ld.lld` 不在 OHOS clang 同级目录，而在 `ohos-sdk@*/native/llvm/bin`；Conan
  profile 的 `buildenv` 已把它加进 `PATH`，配方全部走 `env="conanbuild"`。
- `flext.h` 需要 Pd 内部头 `g_canvas.h`/`m_imp.h`，不止 `m_pd.h`；
  `puredata/0.54.1`（application）装了这些头但 `includedirs=[]`，故随包附带
  Pd 公开 API 头与 flext 头。
- 两个可移植性补丁：`PDGUI_DELETEKEY` 宏形参错用（Pd<0.55 分支）、
  OHOS 无 `pthread_cancel`。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/libflext-pd.so.*` | flext 框架共享库（soname `libflext-pd.so.0.6`） |
| `include/flext/*` | flext C++ 头 |
| `include/puredata/*.h` | Pd API 头（`m_pd.h`/`g_canvas.h`/`m_imp.h`…） |
| `lib/pkgconfig/pd-flext.pc` | 编译/链接元数据 |

## 参考

- 上游：<http://grrrr.org/research/software/flext/>
- 许可：GPL-2.0-or-later
