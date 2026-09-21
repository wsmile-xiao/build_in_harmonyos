# rtklib 2.4.3.b34 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，无 configure / 无顶层 makefile；本包用补丁补一个顶层 makefile）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，OHOS sysroot，aarch64-linux-ohos）
- 目标: HarmonyOS PC / OpenHarmony 6.0，`arch=armv8`，`compiler=clang 15`，`build_type=Release`
- 状态: built
- 外部依赖: **无**（`requires()` 为空；默认构建不定义 `-DLAPACK`/`-DMKL`，RTKLIB 用自带矩阵例程；全部 `#include` 都是 libc 头）

## 编译步骤

```bash
# 1) 源码：官方 GitHub tag v2.4.3-b34（版本号 2.4.3.b34 为 Debian/上游惯例写法）
#    https://github.com/tomojitakasu/RTKLIB/archive/refs/tags/v2.4.3-b34.tar.gz
#    sha256 a9ce13293ef71b028036cb98a114b9bba96bdd439a0aeebca8e9c73156e461cf

# 2) 应用 patches/0001-makefile.patch：新增顶层 makefile（all / install / clean）

# 3) 构建 + 安装（配方里显式传全部构建变量，R33）
make -j2 CC=clang AR=llvm-ar RANLIB=llvm-ranlib CFLAGS="-O2" LDLIBS="-lm -lrt -lpthread"
make install DESTDIR=<package_folder> PREFIX=/
```

顶层 makefile 把 `src/*.c` + `src/rcv/*.c` 编成 `lib/libRTK.a` 一次，再让 5 个命令行程序链接它；
上游每个 `app/consapp/<app>/gcc/makefile` 各自重复编译一遍 `src/*.c`，这里不做重复。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 把 `app/consapp` 当成源码根提升，`.orig`/`.work` 只剩 48 个文件（真实源码 928 个） | 入口探测用 `_BUILD_MARKERS` 里的 `Makefile`，而设备文件系统**大小写不敏感**，`app/consapp/makefile`（小写）被判为命中；RTKLIB 根目录本身没有任何构建文件 | 按 `tar xzf ... --strip-components=1` 重建 `.orig` 与 `.work`，再用 `ohc.edit_tracker.snapshot()` 重建基线指纹（925 个文件） |
| 2 | 直接 `make -C app/consapp` 链接失败（找不到 `lib/iers/gcc/iers.a`） | 各 app 的 `LDLIBS` 无条件写 `../../../../lib/iers/gcc/iers.a -lgfortran -lm -lrt`，而 `iers.a` 只在 `-DIERS_MODEL` 下才有意义、上游 Linux 侧也不生成 | 命令行覆盖 `LDLIBS="-lm -lrt -lpthread"` |
| 3 | `src/stream.c` 编译失败：`gethostbyname` 隐式声明 → `incompatible integer to pointer conversion` | 上游 `CFLAGS` 带 `-ansi -pedantic`，定义 `__STRICT_ANSI__` 后 musl 的 `netdb.h` 不声明 `gethostbyname` | 用 `-std=gnu11`（去掉 `-ansi -pedantic`），31 个 `src/*.c` 全量通过 |
| 4 | 链接期 `input_cresf` / `input_stqf` / `input_javadf` … 未定义 | 接收机原始数据解码器不在 `src/`，在 `src/rcv/`（novatel/ublox/crescent/skytraq/javad/nvs/binex/rt17/septentrio/ss2） | 顶层 makefile 同时收集 `src/*.c` 与 `src/rcv/*.c` |
| 5 | `bin/convbin` 报 `No rule to make target` | GNU make 的 pattern rule **前提里只能有一个 `%`**，`app/consapp/%/%.c` 静默不匹配 | 每个应用写显式规则（6 条，rtkrcv 另带 `vt.c`） |
| 6 | 是否需要 `-lgfortran`/LAPACK/BLAS | `src/rtkcmn.c` 只在 `-DLAPACK`（或 `-DMKL`）下走 BLAS 分支 | 默认构建不定义，零外部依赖 |

## 源码修改

`patches/0001-makefile.patch`（新增文件，+129 行）：新增顶层 `makefile`，提供
- `all`：`lib/libRTK.a`（`src/*.c` + `src/rcv/*.c`）+ `bin/{convbin,pos2kml,rnx2rtkp,str2str,rtkrcv}`
- `install`：装到 `$(DESTDIR)$(PREFIX)/{bin,lib,include}`（`mkdir -p` + `cp -f`，**不 strip、不改写 RUNPATH**，链接器写入的 `.codesign` 段因此保持不变）
- `clean`

不改任何上游源码；不含任何平台宏（`__OHOS__` 等）。

## 依赖版本

无。`requires()` 为空，`tool_requires()` 为空。

## 验证结果

见 `reports/` 下的原始日志：`reports/conan-create.log`、`reports/conan-verify-report.md`、
`reports/w3-local-ci.log`、`reports/test-report.md`。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libRTK.a` | 静态 RTKLIB 库（`src/*.c` + `src/rcv/*.c`） |
| `include/rtklib.h` | 唯一公共头 |
| `bin/convbin` | 厂商原始日志 → RINEX |
| `bin/rnx2rtkp` | RINEX → RTK/PPP 后处理 |
| `bin/pos2kml` | 解算文件 → Google Earth KML |
| `bin/str2str` | 流服务器/客户端/中继 |
| `bin/rtkrcv` | 实时 RTK 服务（终端界面） |
| `licenses/LICENSE.txt` | BSD 2-clause |

**不构建**：`app/qtapp`（rtknavi/rtkplot/srctblbrows/strsvr，依赖 Qt）、`app/winapp`（Win32）。
两者都与无显示的目标平台无关，且上游把它们放在独立的 GUI 子工程里。

**不安装**：`data/`（22 MB 可选样例资产：天线 PCV、接收机命令文件、测站坐标）。
上游 Linux 侧的 `install` 目标也只装二进制，不装 `data/`。

## 注意事项

- 交付的 5 个二进制只静态链接 `libRTK.a`，`readelf -d` 显示 `DT_NEEDED` 仅 `libc.so`、无 `DT_RUNPATH`/`DT_RPATH`；
  因此不需要 `$ORIGIN/../lib` 之类的 rpath，也不存在"无 SONAME / 相对 RUNPATH 导致运行期装载失败"的面。
- `rtkrcv` 不带参数会进入交互模式；脚本化 smoke 一律用 `-h`（打印用法后退出）或 `-o <配置>` + 超时。
- `str2str` 的 test1–test3/test6、`rtkrcv` 的 test1/test2 需要真实串口或 TCP 端口，
  `convbin` 的 test21 需要 `/dev/ttyACM0`，在无接收机硬件的设备上无法运行。
