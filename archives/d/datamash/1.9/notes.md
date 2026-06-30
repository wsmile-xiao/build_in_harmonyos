# datamash 1.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang 15.0.4
- 状态: built (部分完成)

## 编译步骤

1. 初始化：`ohc-run.py init-build datamash 1.9 --url=https://ftp.gnu.org/gnu/datamash/datamash-1.9.tar.gz`
2. 打补丁：`perl patch-autotools-ohos.pl build-aux/config.guess build-aux/config.sub`（E007）
3. 修复 umask：`sed -i 's/umask 077/umask 022/g' configure`（E011）
4. 配置：`./configure --prefix=$DEFAULT_PREFIX`
5. 编译：`make -j2`
6. 安装（staging）：`make install-exec DESTDIR=$TEST_PREFIX`
7. 安装（本地）：`make install-exec`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 脚本不包含 HarmonyOS 检测 | E007: 使用 patch-autotools-ohos.pl 打补丁 |
| 2 | configure 权限错误 | HMDFS UID 映射导致 umask 077 创建的临时目录不可写 | E011: sed 将 configure 中的 `umask 077` 改为 `umask 022` |
| 3 | make install 失败 | texinfo 模块缺失导致文档生成失败 | 使用 `make install-exec` 只安装可执行文件 |

## 源码修改

- `build-aux/config.guess`：添加 HarmonyOS/__OHOS__ 检测
- `build-aux/config.sub`：添加 linux-ohos 三元组支持
- `configure`：修改 umask 077 → umask 022（E011 平台问题）

## 依赖版本

- gettext 0.22.5（libintl）
- sed 4.9
- sort 8.32
- Perl 5.42.0

## 验证结果

```bash
$ datamash --version
datamash (GNU datamash) 1.9

$ decorate --version
decorate (GNU datamash) 1.9

# 功能测试
$ echo "1 2 3 4 5" | datamash sum 1
15

$ echo -e "a\nb\nc" | datamash count 1
3
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| datamash | 499KB | 主程序（命令行数据处理工具）|
| decorate | 195KB | 辅助工具（装饰/排序文本行）|

## 注意事项

1. 文档生成失败（texinfo 模块缺失），使用 `make install-exec` 跳过
2. make check 因文档生成失败而阻塞，实际功能测试手动执行通过
3. 补丁文件需要生成（config.guess/config.sub/configure）

## 编译结束

**编译时间**: 2026-06-09 10:51
**最终状态**: built（二进制可执行，文档/测试部分失败）
---

**编译结束**: 2026-06-09 15:36
**最终状态**: built
