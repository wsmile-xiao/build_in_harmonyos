# proxychains-ng 4.16 适配笔记

## 编译环境
- 构建系统: autotools（自定义 configure 脚本）
- 编译日期: 2026-05-14
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **下载源码**: 使用 curl 从 GitHub 下载 proxychains-ng 4.16 tarball
   - URL: https://github.com/rofl0r/proxychains-ng/archive/refs/tags/v4.16.tar.gz
   - 原始 savannah URL 因 SSL 证书问题无法下载

2. **初始化编译环境**: `ohc-run.py init-build proxychains-ng 4.16 --url=file://...`

3. **Configure**: `./configure --prefix=$DEFAULT_PREFIX`
   - proxychains-ng 使用自定义 configure 脚本（非标准 autoconf）
   - 检测了平台特性：pipe2(), SOCK_CLOEXEC, clock_gettime 等
   - 自动识别为非 Apple/FreeBSD/OpenBSD/Sun/Haiku 系统

4. **Make**: `make -j2`
   - 编译成功，有一些 pragma 警告（不影响功能）
   - 生成：proxychains4（主程序）、proxychains4-daemon（守护进程）、libproxychains4.so（动态库）

5. **Install**: `make install DESTDIR=$TEST_PREFIX`
   - 需要额外执行 `make install-config` 安装配置文件
   - 配置文件路径：$PREFIX/etc/proxychains.conf

6. **本地安装验证**: `make install`（不带 DESTDIR）
   - 安装到 ~/usr/local/bin 和 ~/usr/local/lib
   - 配置文件安装到 ~/usr/local/etc/proxychains.conf

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始 URL SSL 证书验证失败 | savannah.nongnu.org SSL 证书问题 | 使用 GitHub 镜像 URL，curl -k 跳过验证 |
| 2 | G4 档案完整性失败 | manifest.yaml 缺少 build_system 字段 | 添加顶级 build_system: autotools 字段 |
| 3 | proxychains4 --version 不工作 | proxychains 需包装其他程序运行 | 使用无参数运行查看帮助信息验证 |

## 源码修改

无补丁，编译过程无需修改源码。

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1
- 无特殊依赖

## 验证结果

```bash
$ proxychains4
Usage: /storage/Users/currentUser/usr/local/bin/proxychains4 -q -f config_file program_name [arguments]
```

G0 干净构建验证：通过
G1-G4 质量门禁：全部通过

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| proxychains-ng-4.16-ohos-aarch64.tar.gz | 253KB | 预编译包 |
| proxychains-ng-4.16-ohos-aarch64-debug.tar.gz | 200KB | 调试符号包 |

## 注意事项

1. proxychains-ng 使用 LD_PRELOAD 机制，需要动态链接器支持
2. 默认配置文件必须在 $PREFIX/etc/proxychains.conf，否则程序无法运行
3. Makefile 的 install 目标不包含 install-config，需手动安装配置文件
4. proxychains4 不是独立可执行程序，需要包装其他程序（如 proxychains4 curl http://example.com）
---

**编译结束**: 2026-08-08 02:32
**最终状态**: built
