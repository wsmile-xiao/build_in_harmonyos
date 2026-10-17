# geos 3.14.1 编译笔记（HarmonyOS PC · Conan cmake）

## 产物
`libgeos.so`、`libgeos_c.so`（C API）、`bin/geosop`（命令行几何运算工具）。

## 版本选择说明
3.14.1 为上游当前 stable 系列版本，按需求新增；与仓内已有的 3.13.0 / 3.13.1
并存、互不影响，已依赖旧版本的构建不受影响。

## 关键适配
- 完全沿用 3.13.1 的配方（本仓 cmake 模板的标准 OHOS 工具链路径），无需源码补丁。
- geos 3.14.1 无外部 C 依赖（CMakeLists 中唯一 find_package 是内部 dist 模块）。
- 产物 `.so` 与 `bin/` ELF 经 `llvm-objcopy` 去旧签名后由 `binary-sign-tool` 自签
  （HarmonyOS XPM 拒绝未签名/被改动的 ELF）。

## 状态
built —— 真机 `conan create` 通过；test_package 做真实几何断言
（构造 WKT、求交、判面积、缓冲区、错误回调），非仅链接成功。
