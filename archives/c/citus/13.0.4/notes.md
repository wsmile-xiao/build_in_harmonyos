# citus 13.0.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- PostgreSQL版本: 17.0
- 状态: built

## 编译步骤

1. 下载源码：https://github.com/citusdata/citus/archive/refs/tags/v13.0.4.tar.gz
2. 修改 config/config.guess，添加 HarmonyOS 支持（E007）
3. 修改 configure，将 umask 077 改为 umask 022（E011）
4. 创建 cpp 符号链接指向 clang-cpp（解决 cpp 命令缺失）
5. configure 配置：`./configure --prefix=$DEFAULT_PREFIX --without-libcurl --without-lz4 --without-zstd`
6. make 编译：`make -j2`
7. make install 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 HarmonyOS 检测 | 添加 __OHOS__ LIBC 检测和 HarmonyOS case 分支（E007） |
| 2 | libcurl/lz4/zstd 库缺失 | 可选依赖未安装 | 使用 --without-* 参数禁用可选功能 |
| 3 | config.status 创建临时文件失败 | HMDFS umask 077 权限问题 | 修改 configure 中 umask 077 为 umask 022（E011） |
| 4 | Citus 14.0.0 与 PostgreSQL 17 不兼容 | systable_inplace_update_* 函数缺失 | 使用 Citus 13.0.4（支持 PostgreSQL 17） |
| 5 | cpp 命令缺失 | SQL 文件预处理需要 cpp | 创建 cpp 符号链接指向 clang-cpp |

## 源码修改

### config/config.guess
- 第 143-150 行：添加 `__OHOS__` LIBC 检测
- 第 158-167 行：添加 HarmonyOS case 分支，输出 `aarch64-unknown-linux-ohos`

### configure
- 第 5616、5621 行：将 `umask 077` 改为 `umask 022`

## 依赖版本

- PostgreSQL 17.0（已预编译安装）
- clang 15.0.4
- make 4.4.1
- autoconf 2.72
- automake 1.16.5
- libtool 2.4.7

## 验证结果

```bash
# 检查编译产物
ls -la src/backend/distributed/citus.so src/backend/columnar/citus_columnar.so
# 输出：
# citus.so: 1645056 bytes
# citus_columnar.so: 182656 bytes

# 检查安装产物
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/lib/postgresql/*.so
# 输出：
# citus.so
# citus_columnar.so
# citus_pgoutput.so
# citus_wal2json.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| citus.so | 1.6 MB | Citus 分布式扩展主库 |
| citus_columnar.so | 183 KB | 列式存储扩展 |
| citus_pgoutput.so | 27 KB | CDC pgoutput 解码器 |
| citus_wal2json.so | 27 KB | CDC wal2json 解码器 |

## 注意事项

1. Citus 是 PostgreSQL 扩展，需要 PostgreSQL 开发头文件（pg_config）
2. Citus 14.0.0 不兼容 PostgreSQL 17，需要使用 Citus 13.0.4
3. 可选依赖（libcurl、lz4、zstd）可使用 --without-* 参数禁用
4. SQL 文件预处理需要 cpp 命令，需确保 clang-cpp 可用

---
**编译结束**: 2026-06-02 14:10
**最终状态**: built
---

**编译结束**: 2026-06-02 14:10
**最终状态**: built
