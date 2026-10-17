# DRAFT-10101 — puredata 包不含 Pd API 头 m_pd.h：Pd 外部对象配方须在 source() 额外拉 pure-data 源码树

## 错误特征

`conan create`（pd-lib-builder 类 Pd 外部对象配方，OHOS aarch64）在编译第一个 `.c` 时失败：

```
source/defines.h:1:10: fatal error: 'm_pd.h' file not found
#include <m_pd.h>
```

或在配方前置断言处失败：

```
Invalid configuration: Pd API header not found: <build_folder>/pd-api/src/m_pd.h
```

## 根因

制品仓里的 `puredata/0.54.1` 走的是上游 pure-data 的 `make install`：只安装 `pd`
可执行文件与数据目录，`package_info()` 里 `includedirs = []`，**不安装 Pd API 头**
（`m_pd.h`、`g_canvas.h`、`m_imp.h` …）。

而 Pd 外部对象（`pd-smlib` / `pd-maxlib` / `pd-mjlib` / `pd-creb` …）用
`pd-lib-builder` 的 `Makefile.pdlibbuilder` 构建，源码第一行就是
`#include <m_pd.h>`，因此把 puredata 当成「提供头」的构建依赖必然失败。puredata
本身是**应用**，运行时只需要 `bin/pd`。

## 处置

配方 `source()` 里额外拉取与 `puredata/0.54.1` 同版本的 pure-data 源码树，把
`PDINCLUDEDIR` 指向其 `src`：

```python
PD_SRC_URL = "https://codeload.github.com/pure-data/pure-data/tar.gz/refs/tags/0.54-1"
PD_SRC_SHA256 = "19a0e2bfcbb5bad5e6dd016d1cda35464db6de008d1803a14c7e1f1625f31353"

def source(self):
    get(self, **self.conan_data["sources"], strip_root=True)
    pd_api = os.path.join(self.source_folder, "pd-api")
    os.makedirs(pd_api, exist_ok=True)
    get(self, url=PD_SRC_URL, sha256=PD_SRC_SHA256,
        filename="pure-data-0.54-1.tar.gz", strip_root=True,
        destination=pd_api)
```

`build()` 先断言 `pd-api/src/m_pd.h` 存在，再
`make -j1 CC=<conf> PDINCLUDEDIR=<source_folder>/pd-api/src`。

注意：`strip_root=True` + `destination=pd_api` 会把 tarball 的顶层目录去掉，
所以头在 `pd-api/src/`，**不是** `pd-api/pure-data-0.54-1/src/`（踩过一次）。

`CC` 必须从 `tools.build:compiler_executables` 取（R33）；`pd-lib-builder` 用
`$(CC) -dumpmachine` 判断目标系统，OHOS clang 报 `aarch64-...-linux-ohos` →
自动选 Linux 分支与 `pd_linux` 扩展名，正是 Pd 在 OHOS 上要找的扩展名。

## 预防

- 选「Pd 外部对象」这一类软件前先确认头文件来源，别默认 `requires` 会带头。
- 二次下载的头要与制品仓里应用包的版本严格一致（sha256 直接复用
  `puredata/0.54.1` 的 conandata 值），避免头与运行时版本漂移。
- 参考实现：`archives/p/pd-maxlib/1.6.0/conanfile.py`（已绿）、
  `archives/p/pd-smlib/0.13.0/conanfile.py`。

## 附：两个连带坑（同包实测）

1. SMLib 的 list 类只 `class_addlist`，**创建参数不触发** `[vmax 3 9 4]`，
   必须用 `[msg] list ...` 送列表；无参 `[vvplus]` 是标量版（`vvplus_scal_class`，
   右入口是 float inlet），向量加法要用 `[vvplus 10 20 30]` 才成立。
2. 本地 WSL 用 qemu 跑 OHOS musl 程序时缺 `__fd_chk`（guest musl 早于 glibc
   fortify shim），需 `LD_PRELOAD=/opt/ohos-guest/lib/libfdchkshim.so`；CI 原生
   OHOS 无需，故只在测试脚本里按文件存在与否条件注入。
