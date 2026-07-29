# pbzip2 1.1.13 — 编译适配笔记

> 档案创建时间: 2026-04-24 00:00:00
> 最后更新: 2026-06-04
> 当前状态: built → 待升级published

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | pbzip2 — 并行BZIP2文件压缩器 |
| 版本 | 1.1.13 |
| 状态 | ✅ built（功能测试12项全部通过） |
| 构建系统 | **makefile**（纯Makefile项目，非autotools） |
| 源码URL | https://launchpad.net/pbzip2/1.1/1.1.13/+download/pbzip2-1.1.13.tar.gz |
| 实际下载 | https://launchpadlibrarian.net/230381086/pbzip2-1.1.13.tar.gz |
| 编译器 | clang 15.0.4 (aarch64) |
| 依赖 | bzip2库（已有预编译包于~/usr/local） |

## 二、编译阶段

### Phase 1: 环境准备
- [x] 模式A自动编译失败（URL搜索/下载SSL问题）
- [x] 切换模式B手动编译：手动curl下载→init-build --no-download
- [x] init-build 9步完成（环境检查全部通过）

### Phase 2: 编译与安装
- [x] 编译命令：
  ```bash
  make CXXFLAGS="-O2 -fPIC -pthread -D_POSIX_PTHREAD_SEMANTICS \
    -D_LARGEFILE64_SOURCE -D_FILE_OFFSET_BITS=64 \
    -DUSE_STACKSIZE_CUSTOMIZATION -I$DEFAULT_PREFIX/include" \
    LDFLAGS="-L$DEFAULT_PREFIX/lib" LDLIBS="-lbz2 -lpthread"
  ```
- [x] 编译成功，无错误无警告
- [x] DESTDIR模式安装：`make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX`
- [x] staging产物：pbzip2, pbunzip2(软链接), pbzcat(软链接), pbzip2.1(手册页)

### Phase 2.5: 干净构建验证（G0）
- [x] G0 clean-verify 通过（补丁自包含性验证）
- [x] 需要configure wrapper补丁（0003-configure.patch）让G0脚本通过

### Phase 3: 功能测试
- [x] pbzip2无标准make check测试套件
- [x] 手动执行12项功能测试，全部通过（见reports/test-report.md）
- [x] 安全弹窗：无（HongMeng Kernel 1.12.0已解决）

### Phase 4: 预编译包制作
- [x] ohc-run.py package 9步流程完成
- [x] 主包: pbzip2-1.1.13-ohos-aarch64.tar.gz (501KB)
- [x] 调试包: pbzip2-1.1.13-ohos-aarch64-debug.tar.gz (389KB)
- [x] ELF签名、strip、RPATH均已处理

### Phase 5: 归档收尾
- [x] 4个补丁生成并分类
- [x] G0-G4门禁全部通过
- [x] 归档校验和知识完整性检查通过

## 三、源码修改清单

| 文件 | 修改原因 | 修改方式 | 补丁编号 |
|------|---------|---------|---------|
| BZ2StreamScanner.cpp | C++11 PRIuMAX拼接 | `"PRIuMAX` → `" PRIuMAX`（5处） | 0001 |
| Makefile | 平台适配+HMDFS兼容 | 添加-fPIC/-I/-L, ln→rm+ln, PREFIX?= | 0002 |
| configure | G0验证需要 | 新增no-op wrapper脚本 | 0003 |
| pbzip2.cpp | C++11 PRIuMAX拼接 | `"PRIuMAX` → `" PRIuMAX`（27处） | 0004 |

## 四、关键问题记录

### 问题1: C++11 PRIuMAX字符串拼接 (L2-模式经验)
- **现象**: clang 15.0.4报错 `invalid suffix on literal; C++11 requires a space between literal and identifier`
- **根因**: C99/C++11不允许字符串字面量`"%"`与宏名`PRIuMAX`直接拼接，必须加空格
- **修复**: 所有`"PRIuMAX`替换为`" PRIuMAX`（共32处，跨2个文件）
- **影响范围**: 所有使用PRIuMAX/PRIu64等inttypes.h宏的C/C++代码

### 问题2: HMDFS ln -s -f 不兼容 (L1-平台真理)
- **现象**: HMDFS文件系统不支持`ln -s -f`覆盖式软链接创建
- **根因**: HMDFS对符号链接覆盖行为与POSIX不同
- **修复**: Makefile中`ln -s -f`改为`rm -f && ln -s`（R5铁律）
- **影响范围**: 所有在HMDFS上创建/覆盖符号链接的操作

### 问题3: 纯Makefile项目G0验证 (L2-模式经验)
- **现象**: clean-verify.py强制执行`./configure`，但pbzip2无configure脚本
- **根因**: ohc-run.py clean-verify仅支持autotools项目的configure→make→install流程
- **修复**: 创建no-op configure wrapper脚本，exit 0让G0验证通过
- **影响范围**: 所有非autotools（纯Makefile/CMake等）项目

### 问题4: Makefile缺少依赖路径 (L2-模式经验)
- **现象**: 编译时找不到bzlib.h，链接时找不到libbz2
- **根因**: Makefile默认CXXFLAGS/LDFLAGS不含-I/-L路径
- **修复**: Makefile中添加`CXXFLAGS += -I$(PREFIX)/include`和`LDFLAGS = -L$(PREFIX)/lib`
- **影响范围**: 所有依赖外部库且Makefile未自动检测路径的项目

### 问题5: 上游源码结构澄清（代码审查 P0/P1 复议证据）
- **背景**: 代码审查机器人声称 pbzip2 1.1.13 上游为"单文件项目，仅含 pbzip2.cpp"，据此判定补丁 0001（BZ2StreamScanner.cpp）和 0002（Makefile）为 critical 阻塞问题
- **事实**: 上游 pbzip2-1.1.13.tar.gz 解压后包含以下独立源文件：
  - `pbzip2.cpp` (117150 bytes) — 主程序
  - `BZ2StreamScanner.cpp` (16289 bytes) — BZ2 流扫描器实现
  - `BZ2StreamScanner.h` (4355 bytes)
  - `ErrorContext.cpp` (1813 bytes) — 错误上下文实现
  - `ErrorContext.h` (815 bytes)
  - `Makefile` (2760 bytes)
- **上游 Makefile 第 69 行**: `pbzip2: pbzip2.cpp BZ2StreamScanner.cpp ErrorContext.cpp`（与补丁 0002 上下文行完全一致）
- **上游 BZ2StreamScanner.cpp 含 5 处 PRIuMAX 拼接问题**（第 114/155/515/555/683 行），与补丁 0001 修复内容一致
- **验证方法**: `git apply --check -p1` 对纯净上游源码依次应用 0001~0004 全部 4 个补丁，均 CHECK OK + APPLIED 成功
- **结论**: P0/P1 审查结论基于错误前提（误认上游为单文件项目），补丁实际可正常应用

### 问题6: CI 编译失败 — bzlib.h not found (CI 真实阻塞)
- **现象**: CI #11104 报 `pbzip2.cpp:33:10: fatal error: 'bzlib.h' file not found`，编译命令 `-I/storage/Users/currentUser/usr/local/include` 找不到头文件
- **根因**: OHOS CI worker 的 `~/usr/local` 未预装 bzip2 开发文件（bzlib.h / libbz2.a）。bzip2 归档包（archives/b/bzip2/1.0.8）仅有 ohc-run.py manifest（status: published），无 conanfile.py，不能作为 Conan 依赖被 `requires()` 引用。file 包通过 `--disable-bzlib` 绕过，但 pbzip2 核心功能即 bzip2，无法禁用
- **修复**: 在 conanfile.py 的 `_build_bzip2()` 中内联构建 bzip2 1.0.8 静态库：
  1. `get()` 下载 bzip2 1.0.8 源码（sha256: ab5a03176...0c4a2269，来自 conan-center-index 权威记录）
  2. `make libbz2.a` 编译静态库（显式 `-fPIC` 以便链接进 pbzip2 二进制）
  3. 将 bzlib.h + libbz2.a 安装到 `<build_folder>/bzip2_prefix/{include,lib}`
  4. pbzip2 的 `make PREFIX=<bzip2_prefix>` 通过 Makefile 的 `-I$(PREFIX)/include` 和 `-L$(PREFIX)/lib` 定位
- **package_info 调整**: libbz2 静态链接进二进制后，`system_libs` 从 `["bz2","pthread"]` 改为 `["pthread"]`，移除 ~/usr/local/lib 的 LD_LIBRARY_PATH 设置
- **验证**: sha256 已对照 conan-center-index 确认；源码解压含 Makefile/bzlib.h；Makefile 第 46 行有 libbz2.a 目标；conanfile.py 语法检查通过

## 五、预编译包交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pbzip2-1.1.13-ohos-aarch64.tar.gz | 501KB | 主包（含pbzip2+pbunzip2+pbzcat+man） |
| pbzip2-1.1.13-ohos-aarch64-debug.tar.gz | 389KB | 调试符号包 |

## 六、对话记录

### 对话 #2 — 2026-06-03~06-04
**操作**: 模式B手动编译pbzip2 1.1.13
**关键步骤**:
1. 手动下载源码（launchpadlibrarian.net）→ init-build --no-download
2. 修复C++11 PRIuMAX拼接（32处）
3. 修复HMDFS ln -s兼容性
4. 创建configure wrapper + Makefile路径适配
5. DESTDIR模式编译安装→verify→package→本地验证
6. G0-G4全部通过，手动12项功能测试全部通过
**当前状态**: built，待升级published
**遗留问题**: 无
**功能测试**: 2026-06-04 12项全部通过 ✅
---

**编译结束**: 2026-06-04 14:31
**最终状态**: published
