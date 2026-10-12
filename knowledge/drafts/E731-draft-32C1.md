# E731 — 遗留交互式 configure 脚本硬编码 g++/cc 且无测试目标

## 错误特征

- 仓库自带 `configure`，但它不是 autotools 生成的——脚本内部以 `read`/提示交互（内存上限、地形数据选项等），随后直接写着 `g++ -O2 ...` / `cc -O2 ...`。
- 在 CI 中以 `./configure` 非交互调用时：要么因等待 stdin 永久阻塞（直到 W3/CI 超时预算耗尽），要么在 zsh here-doc 场景下因临时文件落到只读 `/tmp` 直接报 `can't create temp file ... read-only file system`。
- 全仓库检索 `make check` / `make test` / `ctest` 均无命中，即**上游不存在正式测试套件**（本模式常与之伴生）。
- 日志指纹：`Interactive (Y/N)`、`Invalid entry`、`g++ -I`、`cc -I ... .c`。

## 触发条件

- 构建系统: custom（手写 configure/build/install shell 脚本，非 autotools/CMake/Meson）
- 阶段: configuration
- 典型包：遗留科研/工程类软件（如 SPLAT! 1.4.2），通常还带样本数据但无测试目录。

## 根因分析

上游 `configure` 只是"交互式问答 + 打印硬编码编译命令"的封装：

1. 问答部分需要 stdin 输入，无法在无人值守环境驱动；
2. 命令部分写死 `g++`/`cc`，完全不感知交叉工具链（等价于违反 R33：裸用 shell 编译器，在 release worker 上会静默编出宿主架构对象）；
3. 脚本本身不产出 Makefile，构建步骤写死在 `build` 脚本里，无法通过 `--host`/`--prefix` 参数重定向到 Conan。

因此**不能用常规 autotools 办法（改 config.guess/config.sub）绕过**，必须在配方侧接管构建。

## 解决方案

### 推荐方案

在 `conanfile.py` 的 `build()` 中**绕开交互脚本、复刻其非交互等价选择**：

1. 用与上游问答一致的保守默认值写配置头（示例：`MAXPAGES=4`），等价于"替用户答完问卷"；
2. 用 `tools.build:compiler_executables` 提供的 `CC`/`CXX` 直接编译同一批上游源文件（include/lib 路径全部取自 Conan 包元数据）；
3. 若上游同一源码用宏切换出多个可执行文件（示例：`HD_MODE 0/1` 分别产出 `splat` 与 `splat-hd`），**按宏各编译一次**，保证产物集合与上游 `build` 脚本一致，不漏命令。

```python
# 伪代码：绕开 interactivity，但保持上游等价语义
self.run(f"cp -f {src}/Makefile.ohos .")
self.run(f"${{CXX}} ${{CXXFLAGS}} -DHD_MODE=0 ... -o splat ...")   # CC/CXX 来自 Conan toolchain
self.run(f"${{CXX}} ${{CXXFLAGS}} -DHD_MODE=1 ... -o splat-hd ...")
```

### 回退方案

若脚本确实无法绕开，用 stdin 管道喂答案（`printf '1\n1\n1\n' | ./configure`）并后处理其生成的命令行替换编译器。**脆弱**（提示语一变即失效），仅在无法复刻构建时使用。

### 禁止做法

- ❌ 在 `build()` 里直接 `./configure`——交互式脚本会阻塞至超时（W3/CI 直接判失败）。
- ❌ 保留脚本里硬编码的 `g++`/`cc` 调用——编出宿主对象，链接或设备运行必炸（R33）。

## 验证

```bash
grep -nE 'read |g\+\+|cc ' configure | head -20     # 确认是交互式+硬编码
grep -rn 'make check\|make test\|ctest' . | head    # 确认无正式测试目标
```

## 关联条目

- 相关: E002（`/tmp` 只读，here-doc 临时文件踩坑同源）
- 原则: P004、P011
