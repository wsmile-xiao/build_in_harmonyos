# ninvaders 0.1.1 适配笔记

## 编译环境
- 构建系统: Makefile
- 编译日期: 2026-09-04
- 编译器: clang
- 目标平台: OHOS aarch64
- 状态: built

## 软件概况
nInvaders 是纯 C 的 ncurses 太空侵略者终端游戏（2002-2003 年，SourceForge 项目），
非库，`package_type = application`。上游发布包仅含 6 个 .c + 6 个 .h + Makefile +
README + ChangeLog + gpl.txt 共 12 个文件，无任何自动化测试。

## 编译步骤
1. 使用 Conan `get()` 下载上游 `ninvaders-0.1.1.tar.gz`（SourceForge 官方源，sha256 校验）。
2. ncurses 通过 Conan 依赖 `ncurses/6.4` 提供（OHOS 宽字符静态构建），构建时从
   `self.dependencies["ncurses"].cpp_info` 获取头文件与库路径。
3. 在 `build()` 中调用上游 Makefile，显式传入 `CC`、`CFLAGS`、`LDFLAGS`、`LIBS`、`OPTIONS`。
   - 关键点：上游 Makefile 默认 `LIBS=-lncurses`，但 OHOS 宽字符 ncurses 包只产出
     `libncursesw.a`，故用 `LIBS=-lncursesw` 覆盖（与 nsnake/avanor 等同类 ncurses 游戏一致）。
4. 在 `package()` 中安装生成的 `bin/nInvaders` 与 `gpl.txt`（许可证）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `LIBS=-lncurses` 链接失败 | OHOS ncurses 6.4 为宽字符静态构建，只产出 `libncursesw.a` | build() 中覆盖 `LIBS=-lncursesw` |
| 2 | nInvaders 无 `--version` 参数 | 上游 CLI 契约：未知选项打印版本+用法到 stderr 后 `exit(1)` | test_package 用 `-help` 路径真实执行二进制，断言版本横幅与 Usage 行，并接受上游约定的退出码 1 |
| 3 | 链接时报 `multiple definition of 'aliens'/'skill_level'/...` | 2002 年代源码在 `.h` 头文件中直接定义全局变量/数组，modern clang 默认 `-fno-common` 拒绝 common 符号合并 | CFLAGS 增加 `-fcommon`（本地用 vendored ncurses.h + gcc 实测验证通过） |

## 测试接入说明
- **上游测试**：上游无任何自动化测试。`test_package/MANIFEST.yml` 写入
  `upstream_tests_exist: false` + `upstream_test_audit`（Makefile 无 check 目标、
  发布包无 tests/ 目录）。conanfile/test_package 输出
  `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...}`。
- **test_package**：真实执行打包后的 `bin/nInvaders -help`，断言输出包含
  `nInvaders` 与 `Usage: nInvaders`，接受上游退出码 1；输出
  `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...}`。
- 游戏本体是交互式 ncurses 程序，CI/真机非交互环境不运行游戏循环（与
  nsnake/nethack/avanor 等终端游戏的处理方式一致）。

## 依赖版本
- ncurses: Conan 依赖 `ncurses/6.4`（静态宽字符构建，libncursesw.a）。

## 验证命令（HarmonyOS aarch64 真机）
```bash
conan create --build=missing -pr:h <profile> -pr:b <profile>
# 预期：编译成功，test_package 执行 nInvaders -help 通过，输出两行 HMBS 标记
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 配方，`LIBS=-lncursesw` |
| conandata.yml | SourceForge 官方源 + sha256 |
| test_package/conanfile.py | 真实执行二进制的 smoke test + HMBS 标记 |
| test_package/test.sh | CLI 契约断言脚本 |
| test_package/MANIFEST.yml | 上游测试审计（no_tests）声明 |
| commands.json | 软件级 CLI 工具声明（R38） |

## hmbs pre-build-check 失败诊断（环境配置问题，非配方问题）

### 现象
hmbs pre-build-check 多次失败，相同报错：`ncurses/6.4` 需从源码构建，而容器预检环境缺 `expr`、`gawk`。

### 根因
`/var/conan/ninvaders-0.1.1/profiles/default`（hmbs pre-build-check 容器使用的 profile）：
```ini
compiler.version=16
tools.build:compiler_executables={"c":"/data/service/hnp/bin/clang", ...}
```
实际工具链：`/data/service/hnp/bin/clang` 是 wrapper 脚本，指向 `/usr/bin/clang-15`（Alpine clang 15.0.7）。**profile 声明 v16，实际 clang 是 v15**。

制品仓 ncurses/6.4/6.5/6.6 的预编译二进制 **全部是 compiler.version=15**（无任何 v16 二进制）。

Conan 的二进制兼容性规则：compiler.version 不自动兼容 → v16 profile 找不到 v15 二进制 → ncurses 必须从源码构建 → 容器预检环境缺 gawk → 失败。

### 验证证据
1. 在 hmbs-box 容器内用 `compiler.version=16` profile 解析 ncurses/6.4 → `Main binary package missing` → 需 Build。
2. 用 `compiler.version=15` profile 解析 ncurses/6.4 → `Download (ohpcd)` → 命中制品仓 v15 二进制。
3. 用 v15 profile 完整跑 `conan create ninvaders/0.1.1`：ncurses 命中制品仓二进制、ninvaders 编译成功、test_package 真实执行 `-help` 通过、两行 HMBS 标记正常输出。

### 结论
**配方本身正确**。失败是 hmbs pre-build-check 容器 profile 配置与实际工具链不匹配导致的环境问题（profile 写 v16 但 clang 是 v15）。修复需要 hmbs 侧修正 pre-build-check profile 的 `compiler.version`（改为 15，与 `/data/service/hnp/bin/clang` wrapper 一致）。

### 与同类包对比
- nsnake/avanor 用 ncurses/6.4，pre-build-check 时若也用 v16 profile 会遭遇相同问题。
- no-more-secrets（ncurses/6.6，09-03 合入）通过时真机可用；真机下线后降级容器出现此 profile 不匹配。

### 建议
待 hmbs 环境修复 pre-build-check profile（`compiler.version` 改回 15）后，本配方即可正常通过。当前配方无需修改。

## 最新诊断（2026-09-07）

### 进展
- hmbs 已修复 profile，正确识别 `compiler.version=15`
- ncurses/6.4 可命中制品仓二进制（不再需要源码构建）
- ninvaders recipe 与远端一致（sha256: 35fe3148）

### 当前失败点
`pkgconf/2.0.3` 从源码构建时缺 `ar` 工具：
```
ERROR: Unknown linker(s): [['llvm-ar-15'], ['llvm-ar'], ['ar'], ['gar']]
Running `ar --version` gave "[Errno 2] No such file or directory: 'ar'"
```

### 根因
预检环境的 PATH 缺少 `/usr/aarch64-alpine-linux-musl/bin/`（含 `ar` 工具）。
这是 hmbs 预检环境 toolchain 配置问题，非 ninvaders 配方问题。

### 验证证据
- 容器内 `ar` 存在于 `/usr/aarch64-alpine-linux-musl/bin/ar`
- HMBS_BUILD_TOOLS 未包含 `ar`（只有 cmake/make/ninja/python3）
- 所有同类 ncurses 消费者（nsnake/nethack/avanor）都会触发相同依赖链

### 建议
hmbs 侧需在预检环境 PATH 中添加 `/usr/aarch64-alpine-linux-musl/bin/`
或提供 `binutils`/`llvm-binutils` 作为 build_requires。
