# st — suckless terminal

## 软件简介

st（simple terminal）是 suckless.org 出品的极简 X11 终端模拟器。它刻意保持小而快：
只实现终端必需的功能，配置通过 `config.h` 编译期常量完成，不支持运行期配置文件，
也不做 scrollback / tab / 分屏等"重量级"特性。产物是单个 `st` 可执行文件。

**主要特性**：

- 基于 Xft 字体渲染，支持 Unicode 与宽字符（`x.c` / `st.c`）
- 支持 256 色与真彩色（真彩色需 terminfo `st-256color`）
- 外挂滚动、键盘/鼠标选择、URL 点击（`externalpipe` / `externalscroll` 由补丁提供，本包未启用）
- 编译期配置：`config.def.h` → `config.h`，`config.mk` 定义编译/安装变量
- 可执行参数：`st [-aiv] [-c class] [-f font] [-g geometry] [-n name] [-o file] [-T title] [-t title] [-w windowid] [[-e] command [args ...]]`

**上游无测试套件**（R51 清点，2026-09-29 实测）：源码 15 个文件、无 `tests/`/`test/` 目录、
`Makefile` 无 `check` 目标 ⇒ 消费者侧由 `test_package/test_st.py` 的二进制冒烟测试覆盖。

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 0.9.1 | built ✅ | 2026-09-29 | 0 |

## 使用方法

```bash
# 默认启动（读取 config.h 里的字体/颜色）
st

# 指定字体与标题
st -f "monospace:size=12" -T "my term"

# 直接执行命令并等待其退出
st -e htop

# 打印版本串（上游 x.c 走 die()，打印后 exit(1)，见下方"注意事项"）
st -v
```

## 平台适配说明

### 构建系统：纯 Makefile，不是 autotools

`st` **没有 `configure` 脚本**，`Makefile` 直接消费 `config.mk`。因此配方不使用
`Autotools` 助手族（`Autotools.configure()` 会去找 `./configure` 而失败），
改为显式 `self.run('make …', cwd=self.source_folder)`。

### 关键适配点

1. **`CC` 必须显式给出**：`Makefile` 带 `.POSIX` 目标 ⇒ make 在没有 `CC=` 时用默认
   `CC=c99`，而本机 `command -v c99` 为空（`Error 127`）。配方取
   `self.conf.get("tools.build:compiler_executables")["c"]`（缺省 `clang`）。
2. **`config.mk` 把路径烧死**：`PREFIX=/usr/local`、`X11INC=/usr/X11R6/include`、
   `X11LIB=/usr/X11R6/lib`，本机 `/usr/X11R6/*` 不存在。配方**只覆盖 `CC`/`INCS`/`LIBS`
   三个 make 变量**，不改上游文件；所有头/库路径全部来自 `.pc` 解析（`pkg-config` 等价实现，见 3），
   避免写死任何本机绝对路径。
3. **`INCS`/`LIBS` 必须在 Python 侧算好，且全程不 exec `pkg-config` 二进制**：`config.mk` 原式是
   `INCS=\`pkg-config --cflags fontconfig freetype2\``；若在 shell 里写成
   `PKG_CONFIG_PATH=… make INCS="\`pkg-config …\`"`，**同一条命令的反引号会在待定赋值生效前
   就被展开**（POSIX：待定赋值不参与本命令其它词的展开）⇒ pkg-config 拿不到 `.pc` 目录、
   返回空，表现为 `x.c:11:10: fatal error: 'X11/Xatom.h' file not found` ⇒ 配方在 Python 侧
   算好 `INCS`/`LIBS` 再拼进 make 命令。**2026-10-01 CI 返修**：`subprocess` 直调
   `pkg-config` 用的是 conan 客户端进程的 PATH，CI worker 上没有该二进制（本机交互 shell
   有 ⇒ 只在 CI 暴露），首轮 CI 报 `FileNotFoundError: 'pkg-config'`。改为纯 Python 解析
   PkgConfigDeps 生成的 `.pc`（`_pc_query`，口径与 pkg-config 不带 `--static` 一致）：
   对拍真实 pkg-config 0.29.2，`--cflags` 12/12、`--libs` 19/19 token 集合完全一致
   （仅顺序不同，我方为「被依赖者在后」拓扑序 + `-L` 前置），全平台零外部依赖。
4. **`PKG_CONFIG_PATH` 注入顺序**：`self.buildenv_info.append_path(...)` 必须写在
   `VirtualBuildEnv(self).generate()` **之前**；环境文件先生成则注入不生效
   （g2 轮实测报 `No package 'x11' / 'freetype2' found`）。
5. **`package_type="application"`**：产物是可执行而非库（R38 ⇒ 需软件级 `commands.json`；
   写成 `library` 且无 `shared` 选项会被 Conan 2.29.1 拒载）。
6. **运行期依赖签名（本设备特有）**：`libxft/2.3.9` 与 `fontconfig/2.18.3` 两枚**已发布**依赖
   包的 `.so` 所带 `.codesign` 在消费端设备上不被 `ld-musl` 接受，报
   `Error loading shared library libXft.so.2: (needed by …/st)` 且冒号后原因为空。
   这是**依赖包**问题、非本配方问题；处置见知识图谱 `E517`（`remove-then-resign-in-task-local-view`）
   与 `E077`（剥段→改 ELF→重签→`chmod` 四步顺序）。**本包 9 个文件未因该问题作任何改动。**

### 依赖关系

#### Conan 依赖（W0 preflight 实测全部已发布）

- `freetype/2.14.3`（与 `fontconfig/2.18.3` 的传递要求对齐；`2.14.3.1` 会 `Version conflict`）
- `fontconfig/2.18.3`
- `libx11/1.8.13`
- `libxft/2.3.9`

#### pkg-config 包名

`x11` / `fontconfig` / `freetype2` / `xft` —— 由 `PkgConfigDeps` 生成四个 `.pc`。

## 验证结果

- `conan-verify st 0.9.1` → **exit 0**（G0/G1/G2/G3/G4/L2/L4/L5 全 PASS）
- 本地 CI 模拟 `ci/conan/setup.sh` + `build_and_test.sh st/0.9.1` → **双过**
- 消费者测试 `test_package/test_st.py`（4 断言）：`PASS: st 0.9.1 消费者测试通过（真实执行二进制 + 版本串 + usage）`
- W2 PR 原子性：**仅含配方变更 9 文件、无框架文件**

## 注意事项

- **`st -v` / `st -h` 的退出码是 1，不是 0**：上游 `x.c` 走 `die()`（`x.c:2075`），
  打印版本串/usage 后 `exit(1)`。因此所有断言都必须落在**输出**上，不能把非 0 退出码当失败。
  同理，框架 Step8 staging 验证用的 `--version`（实测 rc=1）对本包结构性不成立。
- 上游配置是**编译期**的：改字体/颜色需要改 `config.def.h` 后重新编译。

## 参考资料

- **官网**: https://st.suckless.org/
- **代码**: https://git.suckless.org/st/
- **源码包**: https://dl.suckless.org/st/st-0.9.1.tar.gz
- **许可证**: MIT
