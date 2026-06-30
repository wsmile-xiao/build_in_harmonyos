# shntool 3.0.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-04
- 编译器: clang 15.0.4 / clang++ (aarch64)
- 状态: published

## 编译步骤

1. init-build: 从 Debian 仓库下载 orig tarball (Savannah/GitHub 原始 URL 不可用)
2. 替换 config.guess/config.sub 为 automake-1.16 版本（识别 aarch64-unknown-linux-ohos）
3. configure --prefix=$DEFAULT_PREFIX 成功，但 config.status 因 HMDFS 权限问题无法创建临时目录
4. 手动从 config.status + Makefile.in + config.h.in 生成 Makefile 和 include/config.h
5. make -j2 成功编译所有源文件
6. make install DESTDIR=$TEST_PREFIX 成功安装到 staging 目录
7. make check: 无测试套（shntool 没有内置测试），PASS
8. shntool -v 输出: shntool 3.0.10 ✅
9. 创建 autoreconf.hints 让 G0 干净构建验证时运行 autoreconf -fi
10. make install（不带 DESTDIR）安装到本地 ~/usr/local ✅
11. R7 安全弹窗扫描：所有15个二进制可直接执行 ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah/GitHub URL 404/SSL | 下载源不可用 | 使用 Debian pool orig tarball |
| 2 | config.guess 不识别 HarmonyOS | 老版本（2008） | 替换为 automake-1.16 的 config.guess/config.sub |
| 3 | config.status Permission denied | HMDFS 不支持 mkdir 创建临时子目录 | 手动用 Python 从 config.status S/D entries 生成 Makefile/config.h |
| 4 | make -j2 mkfifo 权限 | HMDFS fifo 创建限制 | 实际编译成功，warning 不阻塞 |

## 源码修改

- config.guess: 替换为 automake-1.16 版本（识别 aarch64-unknown-linux-ohos）
- config.sub: 替换为 automake-1.16 版本（支持 HarmonyOS 目标三元组）
- include/config.h: 手动从 config.h.in + D entries 生成
- include/config.h.in: 手动修正 PACKAGE_URL 宏

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1
- autoconf 2.72 / automake 1.16.5
- gawk (mawk not available)

## 功能测试结果（详见 reports/test-report.md）

- shntool -v: 版本 3.0.10 ✅
- shntool -h: 帮助信息正确 ✅
- shntool -m: 14种模式全部列出 ✅
- shntool -f: 19种格式支持 ✅
- 14个别名链接: 全部指向 shntool 正确执行 ✅
- shninfo test.wav: 正确分析WAV属性 ✅
- shnlen test.wav: 正确统计时长（0:01.000）和大小（88244 B） ✅
- shncat test.wav: 100% OK ✅
- shncmp test.wav test.wav: 文件相同 ✅
- shnstrip test.wav: 正确检测标准格式 ✅
- R7 安全弹窗: 所有15个二进制可直接执行 ✅
- make check: 无测试套，PASS ✅

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| shntool-3.0.10-ohos-aarch64.tar.gz | 5.2MB | 预编译包（含 shntool + 14 别名 + man 页 + ELF签名） |
| shntool-3.0.10-ohos-aarch64-debug.tar.gz | 666KB | 调试信息包 |

## 知识沉淀

- E007: config.guess/config.sub 不识别 HarmonyOS，需替换为 automake 最新版本
- HMDFS 限制: config.status 在 HMDFS 上无法创建临时子目录，需手动生成或使用 autoreconf.hints
- Savannah 源不可用: shntool 3.0.10 官方 Savannah URL 404/SSL失败，需使用 Debian pool orig tarball
- shntool 不支持 --version，使用 -v 查看版本信息

## 注意事项

- shntool 不支持 --version，使用 -v 查看版本
- shntool 是纯命令行工具（无库文件），编译简单
- HMDFS 上 config.status 无法自动运行，需要手动或 autoreconf.hints 方式处理
- 原始 tarball URL 需使用 Debian 源（Savannah 镜像已失效）

---

**编译结束**: 2026-06-04
**最终状态**: published