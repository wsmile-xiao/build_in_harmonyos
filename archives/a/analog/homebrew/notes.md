# analog homebrew 适配笔记

## 基本信息

- **软件名称**：analog (Analog CE)
- **上游版本**：6.0.18
- **Homebrew 版本映射**：homebrew → upstream 6.0.18
- **构建系统**：自定义 Makefile（bundled 子目录）
- **许可证**：GPL-2.0-only
- **难度标签**：high

## 依赖关系

| 依赖 | 版本 | 说明 |
|------|------|------|
| bzip2 | bundled | 源码内置子目录 src/bzip2/ |
| libgd | bundled | 源码内置子目录 src/libgd/ |
| libpng | bundled | 源码内置子目录 src/libpng/ |
| pcre2 | bundled | 源码内置子目录 src/pcre2/ |
| unzip | bundled | 源码内置子目录 src/unzip/ |
| zlib | bundled | 源码内置子目录 src/zlib/ |

## 适配要点

1. **构建系统**：analog 使用自定义 Makefile，通过环境变量 CC/CFLAGS/DEFS/LIBS/OS 传递编译参数
2. **Bundled 依赖**：上游 Makefile 默认使用 src/ 下的 bundled 子目录（SUBDIRS = bzip2 libgd libpng pcre2 unzip zlib），我们的配方不覆盖 SUBDIRS/SUBDIROBJS，使用上游默认值
3. **OS 取值**：OHOS 平台应传 OS=UNIX（analog 的 Unix 分支）
4. **DEFS 宏**：不定义 HAVE_GD/HAVE_ZLIB/HAVE_BZLIB/HAVE_PCRE（使用 bundled 版本而非外部库）
5. **LANGDIR 路径**：需通过 -DLANGDIR 指定语言文件运行时路径
6. **pcre2 子目录**：pcre2 使用 autotools（./configure），在 OHOS 上可能需要 config.guess/config.sub 补丁

## 修复历史

### 2026-07-17: pcre2 config.status temp 目录权限问题修复
- **问题**：CI 在 conan create 阶段失败，config.status 创建临时目录 `./confXXXXXX/subs1.awk` 时 Permission denied
- **原因**：CI worker 的 HMDFS 文件系统存在 UID 映射问题，config.status 使用 umask 077 创建 0700 权限的临时目录，但目录 owner 与进程 UID 不一致，导致无法在临时目录中写入文件
- **修复**：在 conanfile.py build() 中 patch pcre2 configure 脚本，将 `umask 077` 替换为 `umask 022`，使 config.status 创建的临时目录可被进程访问
- **证据**：Buildbot #7020，错误 `./config.status: line 823: ./confFbDlCH/subs1.awk: Permission denied`

### 2026-07-17: pcre2 config.guess tmp 权限问题修复
- **问题**：CI 在 conan create 阶段失败，pcre2 子目录的 config.guess 无法写入 tmp 目录
- **原因**：CI worker 的 /storage/Users/currentUser/tmp/ 目录不可写，config.guess 的 dummy.c 编译测试失败
- **修复**：在 conanfile.py build() 中 patch Makefile 的 pcre2 target，添加 --build=aarch64-unknown-linux-gnu 绕过 config.guess
- **证据**：Buildbot #7004，错误 `./config.guess: line 1547: /storage/Users/currentUser/tmp/cgGNlbEO/dummy.c: Permission denied`

### 2026-07-17: pcre2 PCRE2GREP_BUFSIZE 未声明错误修复
- **问题**：CI 在 conan create 阶段失败，pcre2grep.c 编译报错 use of undeclared identifier 'PCRE2GREP_BUFSIZE'
- **原因**：父级 Makefile 通过 DEFS='-DUNIX' 覆盖了 pcre2 autotools 生成的 Makefile 的 DEFS = -DHAVE_CONFIG_H，导致 pcre2grep.c 未包含 config.h，PCRE2GREP_BUFSIZE 等宏未定义
- **修复**：在 conanfile.py build() 中 patch Makefile 的 pcre2 target，向递归 $(MAKE) 传递 DEFS='-DHAVE_CONFIG_H'
- **证据**：Buildbot #7046，错误 `src/pcre2grep.c:235:30: error: use of undeclared identifier 'PCRE2GREP_BUFSIZE'`

### 2026-07-17: CI 依赖解析失败修复
- **问题**：CI 在 conan create 阶段失败，gd/2.3.3 等 6 个外部 Conan 依赖不在制品仓中
- **原因**：配方原本使用 Conan 管理的外部依赖，但这些依赖包尚未发布到制品仓（R36）
- **修复**：改用上游 Makefile 默认的 bundled 子目录编译方式，移除所有外部 Conan 依赖要求
- **证据**：Buildbot #5539，错误 `ERROR: Package 'gd/2.3.3' not resolved: Unable to find 'gd/2.3.3' in remotes`

## 状态

- 当前状态：built（归档已创建，CI Buildbot #7103 通过）
  - conan test_package: 已执行 ✅
  - L0 门禁（结构完整性）: 通过 ✅
  - L1 门禁（测试执行验证）: 通过 ✅
- 所有已知问题已修复，等待后续 PR 合并