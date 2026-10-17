# thunk-gen

`thunk_gen` 是 stsp 维护的 **thunk 代码生成器**，供 dj64dev / comcom64 / fdpp
一类"在 64 位系统上运行 16/32 位 DOS 代码"的工程在**构建期**调用：它把一行
条的函数声明转换成调用桩（thunk）所需的派发表、m4 模板或 C++ 宏。

- 上游项目：<https://github.com/stsp/thunk_gen>
- 许可证：GPL-3.0-or-later

## 组件构成

thunk_gen 不是库，而是一组**构建期工具**：

| 产物 | 作用 |
|------|------|
| `thunk_gen` | 核心可执行文件，按 thunk_type 输出三种形态 |
| `parse_decls.sh` | 声明筛选器，7 个模式（调用侧/定义侧/plt.inc/plt_asmc/plt_asmp/h1） |
| `mkasmdefs.sh` | 由 `__ASM*(...)` 行生成 asm 侧符号宏 |
| `tg_m4` | 驱动 `thunks.m4` 做 m4sugar 展开 |
| `thunks.m4` / `thunks32.m4` | m4 模板（16 位 / 32 位） |
| `thunk_gen.mk` | 给下游 Makefile include 的构建片段 |

三种输出形态：

- `thunk_type=0` → C 派发表（`case N: _DISPATCH(...)`）
- `thunk_type=1` → m4 模板调用（`THUNK(n, void?, pascal?, suffix)`）
- `thunk_type=2` → C++ 宏调用（`_THUNK<n><suffix>(...)`）

## HarmonyOS PC 适配

- 目标平台：HarmonyOS PC / OpenHarmony，`aarch64`，musl。
- 构建系统：上游 Meson（仓库根的 `configure` 只是 `meson setup` 的 bash
  包装，不是 autotools）。
- 静态链接：终端工具按 R26 以 `-Ddefault_library=static` 构建。
- 两处上游可移植性缺陷已打补丁（见 `1.10/patches/`）：
  1. `parse_decls.sh` 模式 5 的 `sed` 替换串引用了不存在的第 3 个捕获组；
  2. `parse_decls.sh` 模式 2 用 GNU grep 的 BRE 扩展 `\|` 做交替匹配，
     OHOS 的 toybox `grep` 会把它当字面量，导致零输出。
- 随包 `lib/pkgconfig/thunk_gen.pc` 的 `prefix` 由 meson 烘成 `/`，已在
  `package()` 改写为 `${pcfiledir}/../..`，包目录整体搬移后仍然可用。

## 消费者契约

下游 `thunk_gen.mk` 通过 pkg-config 变量取用工具，因此 `package_info()`
用 `pkg_config_custom_content` 显式补出这 7 个变量：

```
binary / tgscript / pdscript / mkadscript / m4script / m4_32script / makeinc
```

## 验证

- 上游 1.10 **没有自动化测试套件**（无 `tests/` 目录、`meson.build` 未注册
  `test()`）。可核验的真实入口是 `./configure` → `meson compile`，配方
  `build()` 已等价执行。
- 本适配新增一套 OHOS 消费者测试（`1.10/tests/`），复刻
  `dj64dev / comcom64 / fdpp` 的实际调用管线，针对**本次构建出的**
  `thunk_gen` 真实执行：**65/65 通过**（见 `1.10/reports/test-report.md`）。
- `test_package` 只用包装好的产物再跑一遍消费者管线并真实编译/链接/运行
  C 探针：**49/49 通过**。

## 参考文献

- <https://github.com/stsp/thunk_gen>
- <https://github.com/dj64dev/thunk_gen>（上游开发分支来源）
- <https://github.com/stsp/dj64dev>
