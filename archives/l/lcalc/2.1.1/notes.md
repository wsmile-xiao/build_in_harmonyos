# lcalc 2.1.1 编译笔记（HarmonyOS PC · conan / autotools）
## 定位
L 函数计算库与命令行工具 — 零点、特殊值、Riemann zeta 与一般 L 函数
产出库：`libLfunction.so`。
产出命令行工具：`lcalc`。

## 源码
- URL：https://gitlab.com/-/project/12934202/uploads/487082fc3449dea93e9b85904a589742/lcalc-2.1.1.tar.xz
- sha256：`e513995b2ee9df8447e13dbdecce3cfb2eb66d9cf09a3b0e6603c736ebadb945`

## conan 依赖

- `pari/2.17.4`
- `gengetopt/2.23`

## 关键适配

- configure 里 `AC_PATH_PROG(GENGETOPT, gengetopt)` 是硬性要求，且 2.1.1 的 tarball **不带预生成的 cmdline.c** → 顺手新做了 `gengetopt/2.23`
- gengetopt **不能用 `tool_requires`**：那会走构建上下文（default profile，不是 ohos-native），conan 会按另一套设置把它重建一遍并挂掉 → 改普通 `requires` + 手动把它的 bindir 塞进 PATH
- 删除 `lib/*.la`：里面烤死 libdir 绝对路径（conan 按 prefix=/ 构建 → 写的是 `/lib`），下游 libtool 会去找 `//lib/libxxx.la` 而失败
- 修 configure 的 `umask 077` → `022`（HMDFS 上 077 会让后续步骤读不到自己刚建的临时文件）

## 真机验证（2026-08-17）

设备：HUAWEI MateBook（HAD-W32 / 2in1），OHOS aarch64。
`conan create . -pr ohos-native` 通过，test_package 断言：

1. ζ(2) = π²/6（对上闭式解，10 位小数） ✅
2. ζ(4) = π⁴/90 ✅

## 状态

built —— 真机已验证；制品**尚未上传**（上传须单独过闸）。
