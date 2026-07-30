# iozone 3.51 — Filesystem Benchmark Tool

## 版本信息
- 软件名称: iozone
- 版本: 3.51
- 架构: aarch64
- 构建系统: C + Makefile
- 许可证: custom (Iozone License)

## 构建说明
- 构建工具链: OHOS clang 15
- 编译参数: -DNO_THREADS -DPAGE_SIZE=4096 -DGOT_PAGESIZE (省略 ASYNC_IO/HAVE_PREAD)
- 补丁: 0001-fix-missing-includes.patch (3项修复: errno → <errno.h>，补充 <time.h>，asm/page.h 替换)

## 平台适配
- /tmp 只读: test_package 使用 $TMPDIR 或 fallback 可写目录 (E002)
- musl libc: 无 aio/pread 符号，默认 linux target 行为
- 类型: 叶子库/无第三方 Conan 前置

## 测试验证
- 上游测试: 无 make check/test, 验证入口为 iozone benchmark
- 受控 benchmark: -i 0..7 共 8 类场景，64KB 文件，4KB 记录
- 通过率: 8/8 (100%)

## 关闭
status: closed
COMPLETED
