# jpdfbookmarks 2.5.4 适配笔记

## 编译环境
- 构建系统: custom (pre-compiled Java binary distribution)
- 编译日期: 2026-05-29
- 编译器: N/A (Java application, no native compilation needed)
- 状态: published

## 编译步骤

jpdfbookmarks 是一个预编译的 Java 二进制发行包，无需从源码编译。

1. 下载 release tarball (jpdfbookmarks-2.5.4.tar.gz)
2. 解压到源码目录
3. 安装文件到 DESTDIR 前缀:
   - bin/jpdfbookmarks → GUI launcher script
   - bin/jpdfbookmarks_cli → CLI launcher script
   - lib/jpdfbookmarks/ → jar files + dependencies + config + locales
   - share/jpdfbookmarks/ → documentation
4. 修改启动脚本适配 HarmonyOS（支持安装路径检测）
5. 安装到 DEFAULT_PREFIX（无 DESTDIR）用于用户验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Java找不到libz.so | JDK NEEDED为libz.so而非libz.so.1，系统只有libz.so.1 | 在干净环境(env -i)下Java可正常工作 |
| 2 | 启动脚本使用$SCRIPT_DIR引用jar | 安装后jar不在bin目录，在lib/jpdfbookmarks/ | 修改脚本支持APP_DIR检测：先检查$SCRIPT_DIR，失败则用$SCRIPT_DIR/../lib/jpdfbookmarks |
| 3 | verify-build报告缺少build_system | manifest.yaml中没有build_system顶层字段 | 添加build_system: custom |

## 源码修改

- 0001-jpdfbookmarks.patch: 修改GUI启动脚本，添加APP_DIR检测逻辑
- 0002-jpdfbookmarks_cli.patch: 修改CLI启动脚本，添加APP_DIR检测逻辑

修改核心：当jar文件不在脚本所在目录时，自动使用相对路径 `$SCRIPT_DIR/../lib/jpdfbookmarks`

## 依赖版本

- JDK 17.0.13 (BiSheng/BishengJDK)
- 无其他编译依赖（预编译发行包）

## 验证结果

```bash
$ jpdfbookmarks_cli --version
2.5.4

$ jpdfbookmarks_cli --help
usage: jpdfbookmarks <input.pdf> [--dump | --apply <bookmarks.txt> | ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jpdfbookmarks-2.5.4-ohos-aarch64.tar.gz | 9.8MB | 主包（Release制品） |
| jpdfbookmarks-2.5.4-ohos-aarch64-debug.tar.gz | 10KB | Debug包（Java应用无ELF符号） |

## 注意事项

- jpdfbookmarks 是 Java 应用，需要 JDK 17+ 运行时
- 需设置 JAVA_HOME 或确保 java 在 PATH 中
- BiSheng JDK 在某些 shell 环境下有 libz.so 加载问题，建议在干净环境运行
- 包含 CJK（中日韩）字体配置支持
- Windows .exe 文件未打包到 HarmonyOS 发行包中

**编译结束**: 2026-05-29
**最终状态**: published
---

**编译结束**: 2026-05-29 11:15
**最终状态**: published
