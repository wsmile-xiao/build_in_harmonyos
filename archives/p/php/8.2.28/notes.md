# PHP 8.2.28 适配笔记

## 编译环境
- 构建系统: autotools (需要buildconf)
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码包
   - URL: https://www.php.net/distributions/php-8.2.28.tar.gz (18M)

2. 初始化编译环境
   - 使用 ohc-run.py init-build 创建工作目录

3. 修复build目录
   - PHP需要build目录包含构建文件
   - 从orig目录复制完整的build目录

4. 运行buildconf生成configure
   - ./buildconf --force

5. 修复平台问题
   - 更新 build/config.guess/config.sub（支持 ohos）
   - 修改 configure 中的 umask 077 为 umask 022（E011）

6. 执行configure
   - ./configure --prefix=/storage/Users/currentUser/usr/local --disable-all --enable-cli --disable-phpdbg

7. 执行编译
   - make -j4
   - 成功生成 sapi/cli/php 和 sapi/cgi/php-cgi

## 遇到的问题

| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | build目录缺少文件 | 从orig复制完整build目录 |
| 2 | configure不存在 | 运行./buildconf --force |
| 3 | config.sub无法识别系统 | 更新为支持 ohos 的版本 |
| 4 | config.status权限失败 | 修改 configure 中 umask |
| 5 | pthread_cancel undefined | 禁用phpdbg |

## 验证结果

```bash
$ php --version
PHP 8.2.28 (cli) (built: May 26 2026 11:31:14) (NTS)
Zend Engine v4.2.28

$ php-cgi --version
PHP 8.2.28 (cgi-fcgi) (built: May 26 2026 11:31:17)
```

---
**编译结束**: 2026-05-26
**最终状态**: published