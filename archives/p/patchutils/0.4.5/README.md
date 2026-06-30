# patchutils 0.4.5 — HarmonyOS 预编译包

补丁文件操作工具集，提供以下命令：interdiff、filterdiff、lsdiff、grepdiff、combinediff、flipdiff、rediff、splitdiff、recountdiff、unwrapdiff、editdiff、dehtmldiff、espdiff、fixcvsdiff、move-to-front、patchview。

## 构建信息

- **版本**: 0.4.5
- **构建系统**: autotools
- **目标平台**: aarch64-unknown-linux-ohos (HarmonyOS)
- **编译器**: clang
- **状态**: published
- **许可证**: GPL-2.0-or-later AND LGPL-2.1-or-later

## 安装的可执行文件

| 文件 | 类型 | 说明 |
|------|------|------|
| interdiff | ELF 二进制 | 计算两个 diff 之间的差异 |
| filterdiff | ELF 二进制 | 按条件筛选 diff 中的内容 |
| rediff | ELF 二进制 | 重新计算 diff 的上下文 |
| combinediff | → interdiff 符号链接 | 合合两个 diff |
| flipdiff | → interdiff 符号链接 | 翻转两个 diff 的顺序 |
| lsdiff | → filterdiff 符号链接 | 列出 diff 中修改的文件 |
| grepdiff | → filterdiff 符号链接 | 搜索 diff 中匹配的行 |
| patchview | → filterdiff 符号链接 | 查看 diff 的视觉效果 |
| fixcvsdiff | Perl 脚本 | 修正 CVS diff 格式 |
| splitdiff | Perl 脚本 | 拆分 diff 为单文件 |
| editdiff | Perl 衣本 | 编辑 diff 的头部 |
| recountdiff | Perl 脚本 | 重计算 diff 行数 |
| unwrapdiff | Perl 脣本 | 解包 MIME 编码的 diff |
| dehtmldiff | Perl 脣本 | 从 HTML diff 提取纯文本 |
| espdiff | Perl 脣本 | 智能差异合并 |
| move-to-front | Shell 脚本 | 移动 diff 条目到前面 |
| patchview-wrapper | Shell 脣本 | patchview 的包装脚本 |

## 应用的补丁

1. **0001-config.guess.patch** — 添加 `__OHOS__` libc 检测和 HarmonyOS 系统标识（`*:HarmonyOS:*:*` 分支返回 `aarch64-unknown-linux-ohos`）
2. **0002-config.sub.patch** — 添加 `ohos-linux` 三元组支持（`basic_machine=$field1-unknown, basic_os=linux-ohos`）
3. **0003-configure.patch** — 修复 HMDFS 权限问题：`umask 077` → `umask 000`（临时目录创建处）

## 测试结果

| 类别 | 数量 |
|------|------|
| PASS | 135 |
| FAIL | 58 |
| XFAIL | 6 |
| TOTAL | 199 |

**通过的测试类别**: filterdiff（全通过）、lsdiff（全通过）、grepdiff（全通过）、rediff（全通过）、recountdiff（全通过）、git 相关（全通过）、whitespace/crlf/nul（全通过）

**失败的测试类别**: interdiff、combinediff、flipdiff、apply/revert — 均因 **toybox `patch` (v0.8.12)** 与 GNU `patch` 不兼容

## 已知限制

- **toybox patch 不兼容**: interdiff/combinediff/flipdiff 的完整功能需要 GNU `patch`。当前系统自带的是 toybox patch，无法正确处理 interdiff 生成的临时文件。
- **建议**: 安装 GNU patch (`gpatch/2.8`) 以启用 interdiff/combinediff/flipdiff 的完整功能。

## 配置选项

```bash
./configure --prefix=$DEFAULT_PREFIX HELP2MAN=/bin/true \
  ac_cv_sizeof_long=8 ac_cv_sizeof_long_long=8 ac_cv_sizeof_off_t=8 \
  ac_cv_sizeof_int=4 ac_cv_sizeof_void_p=8
```

编译时需设置 `AUTOCONF=true AUTOMAKE=true ACLOCAL=true AUTOHEADER=true` 以跳过 autotools 重生成。