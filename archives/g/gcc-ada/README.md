# GCC Ada/GNAT

GCC Ada/GNAT 9.5.0 is a native HarmonyOS AArch64 compiler package. It
provides `gcc`, `gnatmake`, `gnatbind`, and `gnatlink` for building Ada
programs and libraries.

## 已编译版本

- `9.5.0`：`built`

## OHOS 适配要点

- GCC Ada 前端由 Ada 编写，构建期使用固定校验和的 Alpine AArch64/musl
  GNAT seed；seed 不进入最终安装包。
- seed 通过签名的 OHOS XPM musl loader 和 native proxy 执行，避免把
  Linux/musl 二进制直接当作普通宿主工具使用。
- GCC/Ada 链接阶段按需注入 OHOS SDK AArch64 `libunwind.a`，编译阶段不注入。

## 验证结果

- 按最新审查统计，上游测试入口清单为 `N=4315`；这是清单统计上界，不是
  通过率分母，也不把未执行入口计为 PASS。
- 按 R51 口径，实际运行量为 `N'=3542`，已运行结果通过率为
  `3542/3542（100%）`；清单与结果记录差额 `773` 项不计为已通过。
- CI `#42755`：完整 build-tree GNAT/ACATS 上游测试 `3542/3542`。
- CI `#42923`：最新轻量门禁通过 Conan `test_package`、L0、L1 和 cleanup；
  门禁测试契约包含安装后上游子集 `41/41` 和 OHOS/消费者断言 `16/16`。
- 完整测试、安装后子集和消费者断言的分母关系见
  `9.5.0/reports/test-report.md`。

## 参考

- [GCC Ada](https://gcc.gnu.org/gcc-9/)
- [GCC 9.5.0 源码](https://ftp.gnu.org/gnu/gcc/gcc-9.5.0/)
