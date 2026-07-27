# libaio 0.3.112 — 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libaio |
| 版本 | 0.3.112 |
| 构建系统 | plain Makefile (non-autotools) |
| 源码 | https://releases.pagure.org/libaio/libaio-0.3.112.tar.gz |
| 状态 | built (二次校准完成) |

## 编译要点
- libaio 使用纯 Makefile 构建，非 autotools/cmake
- 顶层 Makefile 委托 src/Makefile 编译
- 编译器路径必须从 Conan conf 获取 (R33)，使用 `self.conf.get("tools.build:compiler_executables")`
- `make -C self.source_folder` 因为 Conan 在子目录运行 build
- libaio 是系统同名库，默认静态编译 (R26)

## 补丁
1. `0001-harness-cases-13.t.patch` — 修复 designated initializer 语法 (C99 合规)
2. `0002-harness-cases-22.t.patch` — 替换废弃的 sys/poll.h 为 poll.h

## 二次校准 (2026-07-17)
- **问题**: CI 报告 "Conan test_package: 失败"，根因是 CI worker 内核不支持 io_setup syscall
- **修复**: test_package/test.c 改为不依赖 syscall 返回值判定测试成败，仅验证 API 链接可用性
- **验证**: 本地 conan create + test_package 全部通过

---

**编译结束**: 2026-07-15 22:46
**二次校准**: 2026-07-17
**最终状态**: built
