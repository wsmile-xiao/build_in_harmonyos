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
