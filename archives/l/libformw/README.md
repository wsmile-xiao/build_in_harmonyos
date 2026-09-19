# libformw 鸿蒙编译指南

libformw 是 ncurses 源码树 **form/ 子库**的打包名（宽字符版本），不是独立上游项目。
本包提供表单（form）用户界面能力：字段（FIELD）、字段类型与校验（fieldtype）、
页面（PAGE）与表单驱动器（form_driver）。

## 概述

- 公开头：`form.h`（含 `<eti.h>`）
- 产物：`libformw.a`（静态）+ `lib/pkgconfig/formw.pc`
- 源码：与 ncurses 6.6 为同一份官方 tarball
  （`ncurses-6.6.tar.gz`，sha256 与已发布 ncurses/6.6、libncursesw/6.6_p20260516 逐字一致）

## 与 ncurses 家族包的生态分工

| 包 | 提供物 | 角色 |
|----|--------|------|
| `ncurses/6.6` | libncursesw.a + formw/menuw/panelw 全家桶（6.6 基线） | 已发布整包 |
| `libncursesw/6.6_p20260516` | libncursesw.a 独立成包（审核中 PR） | 家族核心库 |
| `libformw/6.6_p20260516`（本包） | 只打包 form/ 子库产物 | form 独立成包 |

本包 `require ncurses/6.6`（visible）：下游链接静态 `libformw.a` 时同链取父包的
`libncursesw.a` 与 `curses.h`；本包裁剪全部 ncursesw 本体产物，避免双份符号。
form 对象与父包 ncursesw 同源编译（同一 tarball、同一补丁集、同一配置），
ABI 严格一致，由 test_package 静态链接实跑验证。

## 关键适配约束（沿用 ncurses/6.6 契约）

1. **只编译静态库**：`--without-shared`。鸿蒙 zsh 依赖系统 `libncursesw.so.6`，
   自建共享库会遮蔽系统库导致 shell 崩溃。
2. **宽字符**：`--enable-widec` 生成 `*w` 系列（libformw/formw.pc）。
3. **完整构建后裁剪**：form/*.c 包含内部头 `config.h`，必须完整 configure 后随树
   构建，再在 package 阶段只保留 form 产物。
4. **HMDFS**：构建在 `/data/storage/el2/base` 私有 build root 进行，configure 用
   hnp bash，`make -j1`（jobserver mkfifo 受限）。
5. **toybox expr**：复合表达式缺陷由 `0001-detect-compound-expr.patch` 拒绝退路，
   依赖设备 gawk/coreutils（与 ncurses/6.6 相同补丁集）。

## 上游测试

`conan create` 随构建执行 `make check`（ncurses 官方测试套件，86 项测试程序
清单核验 + 实跑），详见 notes.md 与 reports/。
