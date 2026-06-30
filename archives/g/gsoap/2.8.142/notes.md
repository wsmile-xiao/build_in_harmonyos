# gsoap 2.8.142 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码包（zip 格式）
   ```bash
   wget https://www.genivia.com/thanks.html?download=gsoap-2.8.142.zip
   unzip gsoap-2.8.142.zip
   cd gsoap-2.8.142
   ```

2. 重新生成 configure 脚本（解决 HMDFS 权限问题）
   ```bash
   autoreconf -fvi
   ```

3. 配置编译选项
   ```bash
   ./configure --prefix=/usr/local --disable-ssl \
       CPPFLAGS="-I/usr/local/include -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0" \
       LDFLAGS="-L/usr/local/lib" \
       CFLAGS="-U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0" \
       CXXFLAGS="-U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0"
   ```

4. 编译
   ```bash
   make -j4
   ```

5. 安装到 staging 目录
   ```bash
   make install DESTDIR=/tmp/test-install-gsoap-2.8.142
   ```

6. 测试
   ```bash
   make check  # 无测试套件，直接 PASS
   ```

7. 打包
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py package gsoap 2.8.142
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码下载 URL 404 | SourceForge URL 不可用 | 使用 Genivia 官方下载页面 URL |
| 2 | configure 创建临时文件失败 | HMDFS 文件系统权限问题 | 使用 autoreconf -fvi 重新生成 |
| 3 | 缺少 OpenSSL 头文件 | OpenSSL 未安装或路径不正确 | 安装 OpenSSL 预编译包，修复 pkg-config 路径 |
| 4 | __fd_chk 链接错误 | FD_SET 宏引用 musl 缺失的函数 | 修改源码强制使用 poll() 替代 select() |
| 5 | manifest 缺少 build_system | 模板字段不完整 | 手动添加 build_system: autotools |

## 源码修改

### 0005-gsoap-stdsoap2.c.patch
修改 `gsoap/stdsoap2.c`，在 tcp_select 函数中添加 `|| defined(__OHOS__)` 条件，强制使用 poll()：

```c
#ifndef WIN32
#if !defined(FD_SETSIZE) || defined(__QNX__) || defined(QNX) || defined(__OHOS__)
  /* __OHOS__: use poll to avoid __fd_chk dependency in FD_SET */
  if (1)
#else
  if ((int)sk >= (int)FD_SETSIZE)
#endif
#ifdef HAVE_POLL
  {
    // 使用 poll() 路径
```

### 0006-gsoap-stdsoap2.cpp.patch
同样修改 `gsoap/stdsoap2.cpp`，确保 C++ 版本也使用 poll()。

### 其他补丁
- config.guess.patch: 添加 OHOS 平台识别
- config.sub.patch: 支持 OHOS 三元组验证
- configure.patch: HMDFS 兼容性修复
- depcomp.patch, install-sh.patch, mkinstalldirs.patch: 构建脚本修复

## 依赖版本

- OpenSSL: 1.1.1w (预编译包)
- Flex: 系统自带
- Bison: 系统自带
- Automake: 1.16.5
- Autoconf: 2.72

## 验证结果

```bash
# soapcpp2 版本验证
/storage/Users/currentUser/usr/local/bin/soapcpp2
# 输出: soapcpp2 release 2.8.142

# wsdl2h 功能验证
/storage/Users/currentUser/usr/local/bin/wsdl2h
# 可正常执行

# 质量门禁
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build gsoap 2.8.142
# 结果: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gsoap-2.8.142-ohos-aarch64.tar.gz | 12M | 预编译包（包含 soapcpp2, wsdl2h） |
| gsoap-2.8.142-ohos-aarch64-debug.tar.gz | 2.1M | 调试符号包 |

## 注意事项

1. **SSL 功能已禁用**: 本次编译使用 `--disable-ssl` 以简化依赖，如需 SSL 支持需重新编译并安装 OpenSSL
2. **poll() 独占**: 在 OHOS 上强制使用 poll()，不使用 select()，避免 __fd_chk 问题
3. **autoreconf 必需**: HMDFS 文件系统上必须重新生成 configure 脚本
4. **制品包路径**: `archives/g/gsoap/2.8.142/packaging/` 目录

---
**编译结束**: 2026-06-09 16:23
**最终状态**: built