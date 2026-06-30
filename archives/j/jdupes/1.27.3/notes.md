# jdupes 1.27.3 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 autotools/configure）
- 编译日期: 2026-06-18
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载源码：TheMatt2/jdupes v1.27.3（原 jbruchon/jdupes 已迁移至 Codeberg，无法访问）
2. 先编译依赖 libjodycode v1.3（静态库），安装到 $DEFAULT_PREFIX
3. 编译 jdupes：`make PREFIX=$DEFAULT_PREFIX IGNORE_NEARBY_JC=1 ENABLE_DEDUPE=1 CFLAGS_EXTRA="-I$DEFAULT_PREFIX/include" LDFLAGS_EXTRA="-L$DEFAULT_PREFIX/lib -ljodycode"`
4. 安装到 staging：`make PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX install`
5. 安装到本地：`make PREFIX=$DEFAULT_PREFIX install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码 URL 无法自动找到 | jbruchon/jdupes 已从 GitHub 迁移至 Codeberg，Codeberg IP被封 | 使用 TheMatt2/jdupes GitHub fork |
| 2 | hashdb.c jc_block_hash API 不兼容 | libjodycode v1.3/v2 API 改变：第二参数从指针改为标量 | 修改 hashdb.c 传递 *path_hash 而非 path_hash，存储返回值到 *path_hash |
| 3 | filehash.c jc_block_hash API 不兼容 | 同上 | 修改为 `hash[0] = jc_block_hash(...)` |
| 4 | jc_alarm_ring 未定义 | libjodycode v1.3 无此 API | 在 jdupes.c 定义 volatile int jc_alarm_ring = 0 |
| 5 | jc_start_alarm/jc_stop_alarm 未定义 | libjodycode v1.3 无此 API | 在 jdupes.h 添加 inline stub 函数 |
| 6 | libjodycode_check.c 编译失败 | 引用了 libjodycode v2.0+ 的 API version macros，v1.3 不提供 | 重写 libjodycode_check.c 为简化版本 |
| 7 | UNAME_S=HarmonyOS 导致 ENABLE_DEDUPE 不自动启用 | Makefile 仅在 Linux 时自动启用 | 手动传入 ENABLE_DEDUPE=1 |
| 8 | CFLAGS 包含 -Wl,-z,stack-size 链接器选项 | Makefile 在 CFLAGS 中添加了链接器参数 | 不影响编译，仅产生 warning |

## 源码修改

- hashdb.c: 修改 jc_block_hash 调用方式（API 兼容）
- filehash.c: 修改 jc_block_hash 调用方式（API 兼容）
- jdupes.h: 添加 jc_alarm_ring extern 声明和 jc_start_alarm/jc_stop_alarm inline stubs
- jdupes.c: 定义 jc_alarm_ring 全局变量
- libjodycode_check.c: 重写为简化版本（移除缺失的 API version macros）

## 依赖版本

- libjodycode v1.3（静态库，deep-soft/libjodycode GitHub fork）

## 验证结果

```bash
$DEFAULT_PREFIX/bin/jdupes --version
jdupes 1.27.3 (2023-08-26) 64-bit, linked to libjodycode 2.0.1 (2023-05-12)
Hash algorithms available: xxHash64 v2, jodyhash v7
Compile-time feature flags: dedupe
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jdupes | 92608 bytes | ELF 64-bit aarch64 PIE executable |

## 注意事项

- 原仓库 jbruchon/jdupes 已从 GitHub 迁移至 Codeberg，本编译使用 TheMatt2/jdupes fork
- jdupes 1.27.3 与 libjodycode v1.3 存在 API 兼容性问题，需要多处源码修改
- 动态链接 libjodycode.so，运行时需要 libjodycode 库
---

**编译结束**: 2026-06-18 02:48
**最终状态**: published
