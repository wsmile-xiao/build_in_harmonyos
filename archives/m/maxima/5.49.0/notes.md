# maxima 5.49.0 编译笔记（HarmonyOS PC · conan / autotools）
## 定位
计算机代数系统（CAS）— 符号积分/求解/化简；本包为 ECL（Embeddable Common Lisp）构建
产出命令行工具：`maxima`。

## 源码
- URL：https://sourceforge.net/projects/maxima/files/Maxima-source/5.49.0-source/maxima-5.49.0.tar.gz/download
- sha256：`6d401a4aa307cd3a5a9cadca4fa96c4ef0e24ff95a18bb6a8f803e3d2114adee`

## conan 依赖

- `ecl/24.5.10`

## 关键适配

- sourceforge 的 URL 以 `/download` 结尾、没有扩展名，conan 按 URL 猜格式当 zip 解 → `BadZipFile` → conandata 显式给 `filename`
- **必须源码内构建**：configure 自己拦下异地构建（`For ECL out-of-tree builds aren't supported`）
- 构建期真的要跑 ecl：LD_LIBRARY_PATH 必须**遍历传递依赖**（libecl 还要 libgmp/libgmpxx）
- `Cannot open #P"SYS:CMP.NEWEST"` / `Unable to find include directory`：ECL 把安装前缀烤死在二进制里。出口是 `ECLDIR`；而找头文件的判据是 `SYS:ecl;config.h`，conan 包里头在 `include/ecl/` 两个判据都不命中 → **在自己的构建目录拼一个 ECLDIR**（软链过去，再补一条 `ecl` → `include/ecl`），不去改依赖包
- `--disable-build-docs` 管不到 `interfaces/emacs/imaxima`（还要 makeinfo）→ 顶层 Makefile 的 SUBDIRS 去掉 interfaces；已知取舍：启动时两条 `unable to set up the help system` 警告，`?` 帮助不可用，sage/passagemath 不用它
- 运行期同样要 `ECLDIR`/`MAXIMA_PREFIX`（否则 `Don't know how to REQUIRE SB-BSD-SOCKETS` —— 模块就在 ecl 包里，只是找不到），故 `runenv_info` 也暴露这两个变量
- 删除 `lib/*.la`：里面烤死 libdir 绝对路径（conan 按 prefix=/ 构建 → 写的是 `/lib`），下游 libtool 会去找 `//lib/libxxx.la` 而失败
- 修 configure 的 `umask 077` → `022`（HMDFS 上 077 会让后续步骤读不到自己刚建的临时文件）

## 真机验证（2026-08-17）

设备：HUAWEI MateBook（HAD-W32 / 2in1），OHOS aarch64。
`conan create . -pr ohos-native` 通过，test_package 断言：

1. integrate(x^2,x) = x^3/3（走真实消费路径 bin/maxima） ✅
2. build_info() 报告 Lisp 实现为 ECL ✅
3. lib/ecl/maxima.fas 在位（11.2 MB） ✅

> 这个包一共重跑了 13 轮才通过，每轮换一个不同的真因（详见上面「关键适配」）。

## 状态

built —— 真机已验证；制品**尚未上传**（上传须单独过闸）。
