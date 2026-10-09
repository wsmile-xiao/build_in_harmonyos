# reflex — HarmonyOS aarch64 预编译包

REFLEX（"relocalizable fast lexical scanner"）是 Thomas Dickey 维护的 **flex 2.5.4 分支**，
生成 C / C++ 词法分析器，并附带扫描器运行时库。

## 快速安装

```bash
tar xzf reflex-20241231-ohos-aarch64.tar.gz -C ~/usr/local

cd reflex-20241231-ohos-aarch64 && sh install-reflex-20241231.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 20241231 | built | 2 |

## 当前版本 (20241231) 详情

### 包内容
- 二进制: reflex（扫描器生成器，flex 的直接替代）、reflex++（C++ 模式的同一生成器）
- 库: librefl.a（静态库；等价于 flex 的 libfl.a，其中 `-lfl` 语义为 `-lrefl`，附带默认 `main()` 与 `yywrap()`）
- 头文件: reFlexLexer.h（C++ 扫描器类接口，即 FlexLexer.h 经 GNU `transform` 重命名后的产物）
- 手册页: share/man/man1/reflex.1
- 依赖: 无外部运行期依赖（静态库自足）；构建期需要 bison（yacc）与 diffutils（`make check` 比对）

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS（conan-verify G0–G4 + L2/L4/L5；本地 CI 模拟 JC_RESULT=pass）
- 补丁数: 2

### 补丁列表
- 0001-skel.c.patch — 上游缺陷修复（**非平台专用**）：骨架把 C-only 的 `yy_init_globals()` /
  `yylex_destroy()` 排在 non-C++ 守卫区块之外，导致 `reflex++` 生成的**所有** C++ 扫描器
  无法编译；用骨架的 `%-` … `%*` 标记把两个函数包进 non-C++ 区
- 0002-configure-hmdfs-tmpdir.patch — 平台适配：`config.status` 自建临时目录后立即写入，
  在 HMDFS 用户卷上第一次写入即 `Permission denied`；去掉 `umask 077` 依赖并显式
  `chmod 700 "$tmp"`，使权限位确定生效

## 使用提示

- **C 扫描器**：`reflex -o scanner.c scanner.l`，链接 `-lrefl`。
- **C++ 扫描器**：必须用 stdout 形式
  `reflex++ -t scanner.l > scanner.cc`。
  用 `-o scanner.cc` 时 `#include <reFlexLexer.h>` 会在输出文件被打开之前写到 stdout
  而丢失，生成物缺少类声明无法编译。

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
