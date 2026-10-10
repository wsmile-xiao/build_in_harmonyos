# illustrate 0.0-git20200923.217db48 适配笔记

## 软件定位

Illustrate 是 David Goodsell 的生物分子插画程序（Scripps 研究所）：读取 PDB
坐标文件与 stdin 上的命令卡，输出非真实感（non-photorealistic）PPM 插画，
即文献与教科书中经典的 "Goodsell 风格" 渲染（DS Goodsell & AJ Olson (1992)
J. Mol. Graphics 10, 235-240）。无 CLI 参数：命令卡从 stdin 读入，输出
PNM 写入当前工作目录。

- 上游: https://github.com/ccsb-scripps/Illustrate （Apache-2.0）
- 版本: commit `217db488ce060d8cd0e85433898de50389dffacc`（2020-09-23,
  "correct version"）；上游无 release tag，Debian 以
  `0.0+git20200923.217db48` 打包同一快照（orig tarball 文件清单逐一比对
  一致），conan 版本号沿用 Debian 命名（`+` 改连字符，先例
  jxrlib/1.2-git20170615.f752187）。
- 上游形态: 单个固定格式 F77 源文件 `illustrate.f`（约 7000 行），README
  的"构建方式"即 `gfortran illustrate.f -o illustrate`，无任何构建系统、
  无自动化测试。

## 构建方式

沿用 `fortran-shlex/2.0.1` 确立的 Fortran 路线：

1. `tool_requires("flang-ohos/20.1.0")` 提供 Fortran 前端 +
   `libFortranRuntime.a` / `libFortranDecimal.a`；
2. 编译: `bin/flang -O2 -c illustrate.f`（`.f` 后缀自动按固定格式 F77 处理，
   无需额外开关）；
3. 链接: 用 profile `tools.build:compiler_executables["c"]` 的原生 OHOS
   clang 驱动 + 显式传入两个 Fortran 静态库 + `-lm`。flang-ohos 不携带
   OHOS sysroot / CRT / Clang resource directory，最终链接必须由平台
   驱动提供 Scrt1.o、libc、libunwind、compiler-rt（fortran-shlex 先例）。
   illustrate 用到 sqrt/sin/cos/exp，`-lm` 必需。

产物 ELF: aarch64 PIE（`DYN`），`INTERP /lib/ld-musl-aarch64.so.1`，
`NEEDED` 仅 `libc.so`，GNU_STACK RW（NX 生效），GNU_RELRO 存在。

## 关键行为（测试与运行注意）

- **无 CLI 旗标**: `--version`/`--help` 一样被当作命令卡读入，stdin 给
  EOF 时程序直接正常结束（exit 0，stderr 出 `Fortran STOP`），CI L2 的
  `--version/--help </dev/null` 检查天然通过。
- **自动尺寸陷阱**: wor 卡里尺寸给负值触发 autosizing，公式
  `ixsize=-2*ixsize+2*radius_max+(xmax-xmin)*rscale`，并钳位到 3000；上游
  2hhb 样例实际渲染 3000x3000（约 109MB PNM）。CI/模拟环境下必须给显式
  正尺寸（如 `200,200`），1 秒内完成。test_package 即用显式 200x200。
- **副作用文件**: 程序除输出 calculate 卡命名的 PNM 外，总是向 CWD 额外
  写一个固定的 `opacity.pnm`；测试须在独立目录中运行。
- **正常完成标记**: F77 `STOP` 语句 → stderr `Fortran STOP`（伴随无害的
  `IEEE arithmetic exceptions signaled: INEXACT`），退出码 0；这是判断
  "跑完"而不是"中途死掉"的可靠依据。
- 命令卡语法/样例见 `share/illustrate/2hhb.inp`（随包安装）。

## 本地复现（WSL 交叉 + qemu 用户态模拟）

- profile: `ohos-aarch64`（CI 同款，clang 在 `/data/service/hnp/bin/`；
  本机开发用 `ohos-aarch64-lkyz` 指向 `/opt/lpk-fixed/clang`）。
- x86_64 WSL 下 flang 为 aarch64 二进制，经 binfmt/qemu 运行；因 libLLVM
  急切重定位 `arc4random`/`mallinfo2` 而宿主 musl 缺这两个符号，需
  `LD_PRELOAD=/opt/ohos-guest/lib/libarc4shim.so:/opt/ohos-guest/lib/libmallinfo2shim.so`
  （仅本地 profile 的 [buildenv]，不进配方）。CI 设备原生执行无此问题。
- 编译出的 illustrate 本体不需要任何 shim，qemu 下直接运行渲染正常。
