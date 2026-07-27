# ttaenc 3.4.1 — 适配笔记

> 档案创建时间: 2026-07-15
> 最后更新: 2026-07-15
> 状态: built

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | ttaenc |
| 版本 | 3.4.1 |
| 状态 | ✅ built |
| 构建系统 | makefile |
| 源码路径 | https://downloads.sourceforge.net/tta/ttaenc-3.4.1-src.tgz |

## 二、编译阶段

### Phase 1: 环境准备
- [x] ohc-run.py init-build 完成 / 源码下载解压

### Phase 2: 编译
- [x] make 编译完成 (clang, -Wall -O3 -fPIC)
- [x] make install 完成 (DESTDIR staging)

### Phase 2.5: 独立目录安装验证
- [x] 干净源码 + 补丁应用
- [x] 独立 TEST_PREFIX make install
- [x] 功能回归测试 (ttaenc -h / -v)

### Phase 3: 测试验证
- [x] ttaenc -h (help) 正常输出
- [x] ttaenc -v (version) 正常输出
- [x] 安全弹窗触发确认

### Phase 5: 归档收尾
- [x] 补丁生成 (refresh-patch --auto)
- [x] manifest.yaml / README.md 更新
- [x] conan-verify 质量门禁通过
- [x] W3 本地 CI 模拟通过

## 三、源码修改清单
| 文件 | 原因 | 补丁 |
|------|------|------|
| Makefile | 使用 $(CC) 代替 gcc, 添加 DESTDIR/PREFIX 支持, 移除 strip | 0001-Makefile.patch |
| ttaenc.c | 替换 __inline 为 static inline (C99 合规) | 0002-ttaenc.c.patch |
| ttaenc.h | 添加 stdint.h, 替换 __uint32_t/__uint64_t | 0003-ttaenc.h.patch |

## 四、编译问题与修复

### 问题 1: __uint32_t/__uint64_t 不可用
- **原因**: clang 在 OHOS 上不提供 GNU 扩展类型 __uint32_t/__uint64_t
- **修复**: 添加 #include <stdint.h>, 使用 uint32_t/uint64_t

### 问题 2: __inline 不可用
- **原因**: __inline 是 MSVC/GCC 特有的, clang 在 C99 模式下需要 static inline
- **修复**: 替换所有 __inline 为 static inline

### 问题 3: Makefile 硬编码 gcc
- **原因**: 原始 Makefile 使用 gcc 编译, 不支持通过环境变量传递编译器
- **修复**: 使用 $(CC) 代替 gcc, 添加 DESTDIR 和 PREFIX 支持

## 五、结束记录
- **最终状态**: built
- **结束时间**: 2026-07-15
