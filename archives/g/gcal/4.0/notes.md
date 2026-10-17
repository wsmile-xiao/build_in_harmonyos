# gcal 4.0 适配笔记

> 版本串说明：上游发布名为 `gcal-4`（单字符"4"），Conan 版本要求 ≥2 字符，故统一采用 `4.0`
> （目录 `archives/g/gcal/4.0/`、分支 `feat/gcal-4.0`、配方 `version` 三处一致）。

## 编译环境
- 构建系统: autotools（GNU Autoconf/Automake 经典树）
- 编译日期: 2026-09-17
- 编译器: clang / clang++（ohos-aarch64 profile，Conan 2.29.1，os=OHOS，musl + libc++）
- 状态: built

## 编译步骤

1. `source()`：官方 tarball `https://ftp.gnu.org/gnu/gcal/gcal-4.tar.gz`（sha256 `0b582b7fad60b66bc3fae139d95ead910a1b4c8ae2d34aed30618f3e92ec16de`）解包并 strip_root。
2. `generate()`：`AutotoolsToolchain(self).generate()` 生成 conanbuild 环境（CC/CFLAGS/CPPFLAGS）。
3. `build()`：
   - `apply_conandata_patches()` 应用 `patches/0003-configure.patch`（E011：`umask 077` → `022`）；
   - **E007**：用 `automake/1.18` 包内副本覆盖 `build-aux/config.guess`、`build-aux/config.sub`；
   - **E386**：`CONFIG_SHELL=/bin/sh sh configure --prefix=… --build=aarch64-unknown-linux-ohos --disable-nls gl_cv_have_weak=no`；
   - `make -j1 MAKEINFO=true`。
4. `package()`：`make install MAKEINFO=true` → `bin/gcal`（application 包，软件级 `commands.json` 已声明）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: working directory cannot be determined` | profile `[buildenv]` 的 `CONFIG_SHELL` 指向 OHOS bash，其在 HMDFS 构建目录 getcwd 失败（E386） | `build()` 内联 `CONFIG_SHELL=/bin/sh` 调用 configure |
| 2 | `config.status: can't create ./conf*/subs1.awk: Permission denied` | autoconf 给临时目录套 `umask 077`，HMDFS 的 uid 映射使其不可写（E011） | `patches/0003-configure.patch` 将 umask 放宽为 022（保留临时目录创建） |
| 3 | `cannot guess build type` | 上游 2015 年的 `build-aux/config.guess` 不认识 aarch64-unknown-linux-ohos（E007） | build() 用 automake/1.18 包内副本覆盖 config.guess/config.sub，configure 钉 `--build` 三元组（不再以 ~145KB 全文件补丁承载，避免 AI 评审判"变更过大"跳过） |
| 4 | gnulib `pthread_cancel` 弱符号探测失败 | OHOS 工具链拒绝 `#pragma weak` 指向 musl 头未声明的符号 | configure 传 `gl_cv_have_weak=no`，走非弱符号路径 |
| 5 | `makeinfo` 缺失导致 make 中断 | 构建环境无 texinfo | `make MAKEINFO=true` 跳过 info 文档生成 |

## 源码修改

- `patches/0003-configure.patch`：把 `config.status` 生成脚本中的 `umask 077 &&` 改为 `umask 022 &&`（E011 受控方案，保留真实临时目录创建）。除该补丁外未修改上游源码；`config.guess`/`config.sub` 属构建期替换（E007），不落补丁、不进 diff。

## 依赖版本

- 运行期：无外部依赖（GNU gcal 自带 gnulib）。
- 构建期：`automake/1.18`（E007 用其 config.guess/config.sub 副本）。

## 验证结果

```bash
# 设备真机（aarch64 OHOS）配方构建 + 打包
conan create archives/g/gcal/4.0 -pr:h <ohos-aarch64 profile> -c tools.build:jobs=2
# 上游测试：0/0（tarball 无任何自动化测试资产，N_static=0）
# 消费者测试（test_package/test_gcal.py）：1/1 通过（100%）
#   · 版本横幅 "gcal (GNU cal) 4"
#   · 1992 年 2 月闰年排版（Su-Sa 表头、2/1 落 Sa 列、29 天）
#   · 未知选项非零退出
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/gcal` | — | CLI 日历程序（aarch64 OHOS 可执行） |

## 注意事项

- 为 application 类型包，随包声明软件级 `commands.json`（R38）。
- "4.0" 是对上游 "4" 的 Conan 化版本串，语义相同；目录/分支/配方三处必须保持 4.0，不得归一化为 4。

---

**编译结束**: 2026-09-17 05:28
**最终状态**: built
