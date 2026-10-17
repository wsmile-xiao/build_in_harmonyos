# device-tree-compiler 1.7.2 适配说明

## 概述
DTC（Device Tree Compiler）用于在设备树源（.dts）与扁平二进制（.dtb）之间互转，
并提供 libfdt 库供上层访问 dtb。本包作为 CLI 工具集（type: tool）打包。

## 构建要点
- 纯 make 构建，无第三方编译依赖；libyaml 为可选（未装即不含 yaml 支持，属预期裁剪）。
- `STATIC_BUILD=1`：fdtget/fdtput/fdtoverlay 静态链接 `libfdt.a`，产物零 .so 运行时依赖，
  规避鸿蒙运行时路径查找与共享库签名面；静态工具链（musl）可由 clang 支持。
- `version_gen.sh` 在编译期由 `VERSION.txt` 生成 `version_gen.h`，`--version` 输出
  `Version: v1.7.2`（test 断言 `1.7.2`）。

## 产物清单
- bin/dtc, bin/fdtdump, bin/fdtget, bin/fdtput, bin/fdtoverlay（已代码签名）
- include/libfdt.h, include/libfdt_env.h, include/fdt.h
- lib/libfdt.a（静态库，供消费者链接）

## 风险与对策记录
| 风险 | 对策 |
| --- | --- |
| meson/ninja 依赖版本漂移 | 本配方不走 meson，直接 make 构建，构建面收敛 |
| 动态 libfdt.so 需要签名 + 运行时路径 | STATIC_BUILD=1 全静态，无 .so 产物 |
| GLIBC 依赖 | OHOS musl 静态 glibc 不可用，但全静态 musl 可编译，HNP 工具链实测通过即可 |
| -Werror 使告警即失败 | 上游默认严格；构建期未见告警 |

## QA 结论
- 本机产物 `fdtdump --version` 输出 `Version: v1.7.2`。
- test_package 以消费者视角：链接 libfdt 校验 magic，并 fork/exec `fdtdump --version` 断言版本。