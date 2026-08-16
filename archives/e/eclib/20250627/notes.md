# eclib 20250627 编译笔记（HarmonyOS PC · conan / autotools）
## 定位
有理数域上椭圆曲线的算术 — 导子/Tate 算法、mwrank 求 Mordell-Weil 秩、模符号
产出库：`libec.so`。

## 源码
- URL：https://github.com/JohnCremona/eclib/releases/download/20250627/eclib-20250627.tar.bz2
- sha256：`b88d4b52612e491c5415946d9e35f2062ca1015ee7fbbe0b61f158fa74cb4bc9`

## conan 依赖

- `pari/2.17.4`
- `ntl/11.6.0.2`
- `flint/3.6.0`
- `gmp/6.3.0.1(force)`

## 关键适配

- configure **不看 pkg-config**，只认 `--with-ntl/pari/flint=<前缀>`（sage 的 spkg 也是这么传的）
- `fatal error: 'gmp.h' file not found`：头文件里直接 `#include <gmp.h>`，而 gmp 是 flint/ntl 的**传递依赖**、configure 又没有 `--with-gmp` 开关 → 把所有依赖（含传递）的 include 目录前置进 CPPFLAGS
- gmp 版本冲突（flint 钉 6.3.0、其余钉 6.3.0.1）→ force 到 6.3.0.1，只重建 flint 一个
- 删除 `lib/*.la`：里面烤死 libdir 绝对路径（conan 按 prefix=/ 构建 → 写的是 `/lib`），下游 libtool 会去找 `//lib/libxxx.la` 而失败
- 修 configure 的 `umask 077` → `022`（HMDFS 上 077 会让后续步骤读不到自己刚建的临时文件）

## 真机验证（2026-08-17）

设备：HUAWEI MateBook（HAD-W32 / 2in1），OHOS aarch64。
`conan create . -pr ohos-native` 通过，test_package 断言：

1. 曲线 11a1 的导子 N = 11 ✅
2. 曲线 37a1 的导子 N = 37 ✅

## 状态

built —— 真机已验证；制品**尚未上传**（上传须单独过闸）。
