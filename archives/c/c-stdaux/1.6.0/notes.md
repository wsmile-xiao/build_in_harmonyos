# c-stdaux 1.6.0 适配笔记

## 编译环境
- 构建系统: meson（meson_version >= 0.60，纯头文件库，无编译产物）
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4（OHOS aarch64 原生工具链）
- 状态: built

## 编译步骤

```bash
# conan create 内部等价流程（tool_requires meson/1.11.0 提供 meson 可执行）
meson setup build .                      # MesonToolchain 生成 native/cross 文件
meson compile -C build -j1               # 默认目标=上游 2 个测试程序（无库可编）
meson test -C build --no-rebuild         # 上游测试套件真实执行
meson install -C build                   # 装 4 个头文件 + lib/pkgconfig/libcstdaux-1.pc
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI worker 无全局 meson 可执行 | OHOS worker 沙箱不自带 meson | `tool_requires("meson/1.11.0")`（ohpcd 制品仓已发布的工具包，canfigger 0.3.2 先例；1.11.0.1 无预编译二进制故锚定 1.11.0） |
| 2 | 下游 c-util meson 项目读 `dep.get_variable('cflags')/'version_scripts'`，Conan PkgConfigDeps 生成的 .pc 无这些自定义变量 | 上游 libcstdaux-1.pc 用 unescaped_variables 导出 | `cpp_info.defines=["_GNU_SOURCE"]` + `pkg_config_custom_content` 写入 cflags 与 version_scripts=no 两个变量，等价上游契约 |
| 3 | tarball 无 LICENSE 文件 | 上游仅在其 git 仓库外声明（meson.build license: 'Apache'） | license 字段按 meson 声明写 Apache-2.0，licenses/ 不强拷 |

## 源码修改

无补丁、无源码修改。

## 依赖版本

- 构建工具: meson/1.11.0（tool_requires，非库依赖）
- 库依赖: 无

## 测试统计（四口径）

| 口径 | 数量 | 说明 |
|------|------|------|
| 上游源码静态声明 | 2 | src/meson.build 两个 meson test() 注册：API Symbol Visibility（test-api）、Basic API Behavior（test-basic） |
| 上游套件实际执行 | 2 | meson test 在 build() 内真实执行（结果以 meson 汇总 Ok/Fail 计数输出 HMBS_UPSTREAM_TEST_RESULT 标记） |
| 跳过/未执行 | 0 | OHOS 原生构建，测试可执行 |
| 新增 test_package 消费者测试 | 7 | c-stdaux_test.c：c_assert、C_ARRAY_SIZE、c_memzero、c_memcpy+c_memcmp、大小端 c_load、c_container_of |

## 验证结果

- conan-verify: G0-G4 + L2/L4/L5（详见 reports/conan-verify-report.md）
- 上游测试: 2/2 通过（meson test 汇总）
- 消费者测试: c-stdaux_test 7 项断言全部 PASS

## 交付物

| 文件 | 说明 |
|------|------|
| include/c-stdaux.h、c-stdaux-generic.h、c-stdaux-gnuc.h、c-stdaux-unix.h | 公共 API（4 个头） |

观察：meson install 在 Conan 布局下未把 libcstdaux-1.pc 装入包内（仅生成于 build/meson-private）；下游契约不受影响——本配方以 cpp_info.defines=["_GNU_SOURCE"] 与 pkg_config_custom_content（cflags、version_scripts=no）承载，Conan PkgConfigDeps 为下游消费者生成等价 .pc。

## 注意事项

- 本包是 c-util 家族依赖底座：c-utf8/c-rbtree/c-siphash/c-shquote/c-list/c-ini 等均通过 `dependency('libcstdaux-1', version: '>=1.x')` 消费本包。本包先行发布后，全家族适配的依赖链即打通。
- version_scripts 变量上游默认特性探测（auto→yes/no），Conan 包内固定为 no（禁用链接版本脚本，对头文件宏使用无影响）；下游若强依赖 version-script 链接，需其配方自行处理。
- 消费者测试二进制经 CONFIG_SHELL（profile buildenv 提供）以 shell 包装执行，规避 OHOS 对新二进制直exec 的执行门控（R7 场景）。
---

**编译结束**: 2026-09-06 01:41
**最终状态**: built
