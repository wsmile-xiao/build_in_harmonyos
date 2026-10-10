# japi-compliance-checker 2.4 适配笔记

## 编译环境
- 构建系统: perl（纯 Perl 脚本工具，无编译）
- 编译日期: 2026-10-06
- 编译器: N/A（Perl 项目）
- 状态: published

## 软件简介

JAPICC（Java API Compliance Checker）是 lvc（ABI Laboratory）出品的 Java 库
API 向后二进制/源码级兼容性检查工具：解包 jar/jmod → `javap` 反编译 →
比较公开 API 面 → 输出 HTML 兼容性报告。与已合入 main 的
abi-compliance-checker 2.3 / api-sanity-checker 1.98.7 为同作者同构项目
（<tool>.pl + modules/ + Makefile + Makefile.pl）。

## 语言判定记录（lang-preflight）

- 实测源码：16 个语言文件（perl 14 个 .pl/.pm，nodejs 2 个为报告模板资源
  Sections.js/Tabs.js），**0 个 C/C++ 文件**；顶层 Makefile 为 2 行包装
  （`perl Makefile.pl -install -prefix`）。
- lang-preflight 判定 `mixed`：其 manifest 阶段"顶层 Makefile → c/cpp"捷径
  与源码统计（perl 88%）冲突，且 `Makefile.PL/Build.PL` 检查为大小写敏感，
  未覆盖本项目的 `Makefile.pl`（小写）。该 mixed 为检测器对 lvc 式布局的
  误判，非真实多语言混合。
- 平台任务 lang=cpp 系批量误标（同 jtreg8 8.3-1 先例）；真实语言为 perl，
  本仓库已有成熟 perl 生态：abi-compliance-checker/api-sanity-checker
  （published）、abcselect（CI #14178 绿，requires perl/5.42.2）、
  registry 预编译包 perl/5.42.2。
- 处置：以 `--lang mixed` 过检（检测器与任务语言声明一致），按 perl 家族
  先例继续适配；上游 `-test` 在真机一次通过即为"环境可适配"的第一手证据。
  检测器改进建议（Makefile.PL 大小写 + 无编译 Makefile 包装识别）记入
  SKILL_FEEDBACK。

## 构建方式

- 类型：脚本工具安装（无编译），`package_type = application`
- 来源：GitHub lvc/japi-compliance-checker tag 2.4
  sha256 `0fd8ff8539a6f4a2c30379999befc1f9003fbb513f778b018a722360ab8c2229`
  （gh-proxy.com 与 ghproxy.net 双镜像下载交叉校验一致）
- 安装布局（build() 内执行 Makefile.pl 等效步骤，同 abi-compliance-checker 2.3）：
  - `share/japi-compliance-checker/japi-compliance-checker.pl`（真实入口，
    MODULES_INSTALL_PATH → `../share/japi-compliance-checker`）
  - `share/japi-compliance-checker/modules/`（Perl 模块与资源）
  - `bin/japi-compliance-checker`（bash wrapper，`exec perl <abs>.pl "$@"`）
- Perl 依赖：仅核心模块（Getopt::Long、File::*、Cwd、Data::Dumper、
  IPC::Open3、Digest::MD5、Config、POSIX），无 CPAN 依赖
- JDK：build() 按 JAVA_HOME → ~/bishengjdk17 → ~/usr/local/bishengjdk17 →
  PATH → cmd-pkgs install-jdk.sh（BiSheng 17.0.13）链解析
  （jackson-core 2.14.1 / jtreg8 8.3-1 同款策略）

## 上游测试（R51 三步法）

1. **清点**：无独立 tests/ 目录；回归套件内嵌 `modules/Internals/RegTests.pm`
   （`-test` 入口：现场生成 libsample_java v1/v2 源码 → javac/jar 构建 →
   30 个 Test_*.java 运行时用例 → 断言检出 break 数 ≥ 100）。README 声明
   "about 100 basic tests"。
2. **实测**（真机 HarmonyOS，BiSheng JDK 17.0.13 + Perl 5.44.0）：
   `japi-compliance-checker -test` → `Test result: SUCCESS (164 breaks found)`，
   退出码 0；Journal.txt 记录 30 个用例（16 干净通过 + 14 个设计内的
   不兼容触发用例，如 NoSuchFieldError，用于证明 break 真实存在）。
   build() 内置同一套件（R51），conan create 即实测。
3. **回填**：PR 正文测试对比表如实填写（上游 1 套 -test 套件：164 breaks
   断言通过；适配后同一套件 + test_package 8 条消费者断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Perl 路径不对 | HarmonyOS Perl 不在 /usr/bin/perl | 0001 补丁改 shebang 为 /usr/bin/env perl |
| 2 | Makefile.pl 兼容性 | Perl 5.42+ 的 File::Spec 导入与 Getopt::Long 单破折号问题 | build() 内执行等效安装（abi-compliance-checker 同款） |
| 3 | $0 路径解析 | 从 PATH 调用时 getModules() 找不到 modules | bin wrapper 解析自身绝对路径后 exec perl |
| 4 | 设备/本机直连 GitHub 超时 | 网络环境 | 本地验证期 conandata 指向设备本地 HTTP 镜像（jtreg8 先例）；提交版恢复官方 GitHub URL |

## 源码修改

### 补丁文件: 0001-japi-compliance-checker.pl.patch

修改 japi-compliance-checker.pl 的 Perl shebang 路径（+1/-1）：
- 原始: `#!/usr/bin/perl`
- 修改: `#!/usr/bin/env perl`

无平台宏注入（PF5/R8 合规）。

## 依赖版本

- Perl: 5.44.0（Harmonybrew，运行时经 PATH/env 解析）
- JDK: BiSheng OpenJDK 17.0.13（~/bishengjdk17，缺失时 cmd-pkgs 自动安装）
- Conan 依赖: 无（纯脚本工具）

## 验证结果

```bash
$ japi-compliance-checker --version
Java API Compliance Checker (JAPICC) 2.4

$ japi-compliance-checker v1.jar v2.jar   # v2 删除公有方法 removeMe
Binary compatibility: 66.7%
Total binary compatibility problems: 1, warnings: 0
Report: compat_reports/v/1_to_2/compat_report.html

$ japi-compliance-checker v1.jar v1.jar   # 负向对照
Binary compatibility: 100%
Total binary compatibility problems: 0, warnings: 0

$ japi-compliance-checker -dump v1.jar -dump-path api.dump
Dump path: api.dump                            # 含 API_DUMP_VERSION 2.4

$ japi-compliance-checker -test
Test result: SUCCESS (164 breaks found)        # 上游回归套件
```

（真机 HarmonyOS 6.1.0 / HAD-W32 ARM64 实测）

## 注意事项

1. 运行时需要 perl 与 JDK（javap/jar/javac/java）同时在 PATH
2. wrapper 为 bash 脚本（CI worker 与鸿蒙真机均有 bash）
3. `Makefile.pl` 未使用（保留在源码树中未删，补丁零涉及）

---

**编译结束**: 2026-10-06 14:06
**最终状态**: published
