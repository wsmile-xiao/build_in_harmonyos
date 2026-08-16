# symmetrica 3.1.0 编译笔记（HarmonyOS PC · conan / autotools）
## 定位
对称群表示论与组合学 C 库 —— 分拆、Schur 函数、对称函数、杨表等
产出库：`libsymmetrica.so`。

## 源码
- URL：https://github.com/sagemath/sage-package/releases/download/tars/symmetrica-3.1.0.tar.xz
- sha256：`2efc4b1d047c6fe036453882a20e906ca2bedecae888356c7626447db2b10fd3`

## 关键适配

- **必须带 `-DFAST -DALLTRUE`**：少了 ALLTRUE，一大批组合学函数根本不编进库，而构建/装包全程成功 —— 是那种「装得上、下游才炸」的静默缺失
- 上游 tarball 来自 sage-package 的 tars 归档（与 sage 用的同一份，sha256 一致）
- 删除 `lib/*.la`：里面烤死 libdir 绝对路径（conan 按 prefix=/ 构建 → 写的是 `/lib`），下游 libtool 会去找 `//lib/libxxx.la` 而失败
- 修 configure 的 `umask 077` → `022`（HMDFS 上 077 会让后续步骤读不到自己刚建的临时文件）

## 真机验证（2026-08-17）

设备：HUAWEI MateBook（HAD-W32 / 2in1），OHOS aarch64。
`conan create . -pr ohos-native` 通过，test_package 断言：

1. 10! = 3628800（fakul 走对象系统真算） ✅
2. 0! = 1（边界，证明不是把输入原样返回） ✅

## 状态

built —— 真机已验证；制品**尚未上传**（上传须单独过闸）。
