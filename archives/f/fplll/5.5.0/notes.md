# fplll 5.5.0 编译笔记（HarmonyOS PC · conan / autotools）
## 定位
格基约化库与命令行工具 — LLL / BKZ / HKZ 约化与 SVP、CVP 求解
产出库：`libfplll.so`。
产出命令行工具：`fplll`、`latticegen`。

## 源码
- URL：https://github.com/fplll/fplll/releases/download/5.5.0/fplll-5.5.0.tar.gz
- sha256：`f0af6bdd0ebd5871e87ff3ef7737cb5360b1e38181a4e5a8c1236f3476fec3b2`

## conan 依赖

- `gmp/6.3.0`
- `mpfr/4.2.2.1`

## 关键适配

- **必须源码内构建**：发布 tarball 里自带一份作者本机 configure 出的 `fplll/fplll_config.h`（`#define FPLLL_WITH_QD 1`），异地构建时它会遮蔽 configure 生成的正确那份，`--without-qd` 形同虚设 → `fatal error: 'qd/dd_real.h' file not found`。删掉它也不行（`enumerate_base.h` 用相对路径 `#include "../fplll_config.h"`），源码内构建让生成的那份原地覆盖
- aarch64 的 `long double` 是 **128 位四精度**，算术靠 compiler-rt 的 `__addtf3/__multf3/__trunctfdf2` 一组内建。只往 LDFLAGS 塞 `-rtlib=compiler-rt` 没用 —— libtool 只透传 -L/-l/-Wl,*，别的驱动级 flag 被丢掉（日志里 grep 不到 rtlib 即坐实）。两手：放进 CXXFLAGS + 把 `clang --print-libgcc-file-name` 报出的 builtins **绝对路径 .a** 加进 LDFLAGS。缺了它构建装包全绿，**加载 .so 时**才炸
- `--without-qd`（与 sage 的 spkg 一致，避免 C++ ABI 问题）
- 删除 `lib/*.la`：里面烤死 libdir 绝对路径（conan 按 prefix=/ 构建 → 写的是 `/lib`），下游 libtool 会去找 `//lib/libxxx.la` 而失败
- 修 configure 的 `umask 077` → `022`（HMDFS 上 077 会让后续步骤读不到自己刚建的临时文件）

## 真机验证（2026-08-17）

设备：HUAWEI MateBook（HAD-W32 / 2in1），OHOS aarch64。
`conan create . -pr ohos-native` 通过，test_package 断言：

1. 对刻意造坏的二维格基做 LLL 后 |det| 仍为 1（幺模变换，格没变） ✅
2. 约化后最短行的范数²严格小于原来的 ✅
3. 结果通过 fplll 自己的 `is_lll_reduced` 判据（δ=0.99, η=0.51） ✅

> 这个包一共重跑了 4 轮才通过，每轮换一个不同的真因（详见上面「关键适配」）。

## 状态

built —— 真机已验证；制品**尚未上传**（上传须单独过闸）。
