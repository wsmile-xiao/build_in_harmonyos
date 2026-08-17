# ppl 1.2 编译笔记（HarmonyOS PC · conan / autotools）
## 定位
凸多面体等数值抽象库 — 约束↔生成元双描述转换、MIP 求解、格点与同余网格
产出库：`libppl.so`、`libppl_c.so`。

## 源码
- URL：http://deb.debian.org/debian/pool/main/p/ppl/ppl_1.2.orig.tar.xz
- sha256：`691f0d5a4fb0e206f4e132fc9132c71d6e33cdda168470d40ac3cf62340e9a60`

## conan 依赖

- `gmp/6.3.0.1`

## 关键适配

- 源码取 Debian 的 orig tarball：上游 bugseng.com 与 ftp.cs.unipr.it **都返回 403**（换浏览器 UA 也一样）。Homebrew 的 ppl formula 用的是同一份 Debian tarball，sha256 一致
- **必须用带 C++ 接口（gmpxx）的 gmp**：PPL 的系数类型就是 `mpz_class`。制品仓的 `gmp/6.3.0` 二进制是静态且不含 gmpxx（只有 libgmp.a + gmp.h），用它 configure 报的是 `Cannot find GMP version 4.1.3 or higher` —— 措辞像版本太老，config.log 里才是真话：`fatal error: 'gmpxx.h' file not found`。换 `gmp/6.3.0.1`
- PPL 的 GMP 检查是 `AC_RUN_IFELSE`（**真跑**一个程序比对头与库的版本/limb 位数），所以 LD_LIBRARY_PATH（跑 conftest 用）与 `-Wl,-rpath`（最终产物用）两手都要给
- 打上游提交 c39f6a07 的补丁：PPL 1.2 有两处模板省了 `typename`/`template`，GCC 放行、clang 报错。C++20 的 P0634R3 本可免掉，但设备上的 clang-15 还没实现（clang 16 才有）—— 实测 `-std=c++20` 报同样的错。补丁按真实文件用 difflib 重生成、并用 **patch_ng**（conan 自己的补丁引擎）验过：原始 diff 会被它判 can_patch=False
- `--enable-coefficients=mpz --disable-fpmath --enable-interfaces=c,c++`，与 sage 的 spkg 一致
- 删除 `lib/*.la`：里面烤死 libdir 绝对路径（conan 按 prefix=/ 构建 → 写的是 `/lib`），下游 libtool 会去找 `//lib/libxxx.la` 而失败
- 修 configure 的 `umask 077` → `022`（HMDFS 上 077 会让后续步骤读不到自己刚建的临时文件）

## 真机验证（2026-08-17）

设备：HUAWEI MateBook（HAD-W32 / 2in1），OHOS aarch64。
`conan create . -pr ohos-native` 通过，test_package 断言：

1. 单位正方形（0≤x≤1, 0≤y≤1）经双描述转换得到的生成元恰好 4 个（正方形的 4 个顶点） ✅
2. 这 4 个生成元的类型全是 POINT（有界多面体不该出现射线/直线） ✅
3. `ppl_Polyhedron_is_bounded` 判有界 ✅

> 这个包一共重跑了 4 轮才通过，每轮换一个不同的真因（详见上面「关键适配」）。

## 状态

built —— 真机已验证；制品**尚未上传**（上传须单独过闸）。
