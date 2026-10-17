# brial 1.2.15 编译笔记（HarmonyOS PC · conan / autotools）
## 定位
布尔环代数框架（PolyBoRi 的后继）— 布尔多项式环上的 Gröbner 基与化简
产出库：`libbrial.so`、`libbrial_groebner.so`。

## 源码
- URL：https://github.com/BRiAl/BRiAl/releases/download/1.2.15/brial-1.2.15.tar.bz2
- sha256：`1d0e7de01b1b60ad892dee6c02503f5932e2ed211f3f8dbdf1a3216c696ef201`

## conan 依赖

- `boost/1.91.0.1`
- `m4ri/20260122`
- `libpng/1.6.58.1(force)`

## 关键适配

- conan 图里 **libpng 版本冲突**（传递依赖钉 1.6.58，本包要 1.6.58.1）→ `force=True` 收敛；选版原则是「让最少的包重建」，判据看 conan 打的 `- Build` / `- Cache` 标记，别猜
- boost 的探测宏 `AX_BOOST_BASE` 只认 `--with-boost=<前缀>`，pkg-config 一眼不看
- 删除 `lib/*.la`：里面烤死 libdir 绝对路径（conan 按 prefix=/ 构建 → 写的是 `/lib`），下游 libtool 会去找 `//lib/libxxx.la` 而失败
- 修 configure 的 `umask 077` → `022`（HMDFS 上 077 会让后续步骤读不到自己刚建的临时文件）

## 真机验证（2026-08-17）

设备：HUAWEI MateBook（HAD-W32 / 2in1），OHOS aarch64。
`conan create . -pr ohos-native` 通过，test_package 断言：

1. 布尔多项式环上两条可手算恒等式（x*x = x 幂等、加法特征 2） ✅

## 状态

built —— 真机已验证；制品**尚未上传**（上传须单独过闸）。
