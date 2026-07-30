# geos 3.13.1 编译笔记（HarmonyOS PC · Conan cmake）

## 产物
`libgeos.so`、`libgeos_c.so`（C API）。

## 版本选择说明
选 3.13.1 而非仓内已有的 3.13.0，是因为 **shapely 钉的就是 3.13.1**
（shapely 的 wheel 构建对 GEOS 版本有下限要求）。两版并存、互不影响。

## 关键适配
- 走本仓 cmake 模板的标准 OHOS 工具链路径，无需源码补丁。
- 产物 `.so` 经 `llvm-objcopy` 去旧签名后由 `binary-sign-tool` 自签
  （HarmonyOS XPM 拒绝未签名/被改动的 ELF）。

## 状态
built —— 真机 `conan create` 通过；test_package 做真实几何断言
（构造 WKT、求交、判面积），非仅链接成功。
