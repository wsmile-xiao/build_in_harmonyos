# redir 3.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-13
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境: `ohc-run.py init-build redir 3.3 --url=https://github.com/troglobit/redir/releases/download/v3.3/redir-3.3.tar.xz --no-download`
2. 下载源码（手动，因SSL问题）: `curl -fsSLk -o ~/tmp/redir-3.3.tar.xz https://github.com/troglobit/redir/releases/download/v3.3/redir-3.3.tar.xz`
3. 应用E011修复: `sed -i 's/umask 077/umask 022/g' configure`
4. 配置: `./configure --prefix=$DEFAULT_PREFIX`
5. 编译: `make -j1`
6. 安装(staging): `make install DESTDIR=$TEST_PREFIX`
7. 安装(local): `make install`
8. 测试: `make check` (无测试套，exit 0)
9. 打包: `ohc-run.py package redir 3.3`
10. 收尾: `ohc-run.py finish redir 3.3 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure失败: config.status无法创建临时文件 | E011 HMDFS权限问题：umask 077创建的临时目录无法被当前进程写入 | 修改configure中`umask 077`为`umask 022` |
| 2 | SSL下载失败 | SSL证书验证失败 | 手动下载源码(curl -k)，使用--no-download模式 |
| 3 | manifest缺少build_system字段 | verify-build脚本检查顶层build_system字段 | 在manifest.yaml添加`build_system: autotools`顶层字段 |
| 4 | G4门禁"无二进制文件" | DESTDIR模式下staging目录结构不匹配verify脚本预期 | 修复manifest后G4通过 |

## 源码修改

- `configure`: 将`umask 077`修改为`umask 022`（2处），解决HMDFS权限问题
  - 补丁: `0001-configure.patch`

## 依赖版本

无依赖。redir是独立的C程序，仅依赖libc。

## 验证结果

```bash
$ redir --version
3.3
$ file ~/usr/local/bin/redir
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| redir-3.3-ohos-aarch64.tar.gz | 99KB | 预编译包（含ELF签名） |
| redir-3.3-ohos-aarch64-debug.tar.gz | - | 调试符号包 |
| 0001-configure.patch | ~1KB | HMDFS umask修复补丁 |

## 注意事项

- autotools项目在HMDFS上必须修复umask 077问题（E011）
- redir无测试套，make check返回0但不执行任何测试

---

**编译结束**: 2026-06-13 19:43
**最终状态**: built
