# rpm2cpio 1.4-r3 适配笔记

## 编译环境
- 构建系统: makefile（自定义）
- 编译日期: 2026-07-15
- 编译器: 无需编译器（shell script）
- 状态: built

## 编译步骤

1. 源码获取：从 FreeBSD ports 获取 rpm2cpio shell script
   - URL: https://cgit.freebsd.org/ports/plain/archivers/rpm2cpio/files/rpm2cpio

2. 创建自定义 Makefile（支持 DESTDIR 模式）

3. 安装到 staging 目录：
   ```bash
   make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
   ```

4. 安装到本地 PREFIX（模拟用户部署）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python 库依赖错误 | libiconv.so.2 未加载 | 设置 LD_LIBRARY_PATH=/data/service/hnp/python.org/python_3.12/lib |
| 2 | curl 库依赖错误 | libcurl.so 符号未找到 | 使用 wget 替代 curl |
| 3 | 硬链接失败 | HMDFS 文件系统限制 | 使用符号链接替代（R5 铁律: rm -f && ln -s） |
| 4 | manifest 缺少 build_system | 模板字段位置错误 | 在顶层添加 build_system 字段 |

## 源码修改

### Makefile（已移除）
- 二次校准：移除 build() 中动态创建的 Makefile（P3: 死代码）
- package() 直接处理文件复制和符号链接，无需 Makefile

## 依赖版本

无编译依赖（shell script）

运行依赖：bsdtar/libarchive v2.8+

## 验证结果

```bash
# Staging 验证
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/bin/
# 产物: rpm2cpio, rpm2cpio.pl -> rpm2cpio

# 本地验证
$DEFAULT_PREFIX/bin/rpm2cpio
# 输出: Usage: rpm2cpio [file.rpm]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| rpm2cpio-1.4-r3-ohos-aarch64.tar.gz | 4KB | 预编译包（shell script） |

## 注意事项

1. rpm2cpio 依赖 bsdtar/libarchive v2.8+
2. HMDFS 禁止硬链接覆盖，使用 rm -f && ln -s 方式
3. 无 configure 步骤，直接使用 make install
---

**编译结束**: 2026-07-15 21:41
**最终状态**: built
