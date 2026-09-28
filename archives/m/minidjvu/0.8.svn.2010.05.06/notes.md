# minidjvu 0.8.svn.2010.05.06 适配笔记

## 编译环境

- 构建系统：Autotools（上游自定义 Makefile.in）
- 编译日期：2026-09-23
- 编译器：HarmonyOS Clang/Clang++ 15.0.4
- 目标平台：HarmonyOS 6.0，aarch64，libc++
- 状态：built

## 源码与版本

- 采用官方 SourceForge SVN r23 快照；该修订提交时间为 2010-05-06。
- 官方快照 URL 与 `svn export -r 23` 的全部文件内容逐文件一致。
- SourceForge 自动生成的 r23 ZIP 快照地址已失效并返回 404；配方改为从官方 SVN 的不可变 `!svn/rvr/23/trunk` 资源导出 116 个文件，并以规范化整树 SHA256 固定内容，不提交源码压缩包。

## 编译步骤

Conan 下载源码并应用两个可移植性补丁和一个上游缺陷修复；`AutotoolsToolchain` 注入 HarmonyOS 编译器、依赖头文件和库路径，随后执行：

```text
./configure --prefix=<package-folder> --disable-static
make -j1
make install
```

上游静态模式不会安装库文件，因此保留上游默认共享库模式。`libminidjvu` 与 `minidjvu` 命令行工具均被打包。

## 上游测试清点（R51）

| 清点项 | 结果 |
|--------|------|
| `tests/`、`test/` 目录 | 0 |
| 名称含 test 的测试源文件 | 0 |
| Autotools `check` / `test` 目标 | 0 |
| ctest/pytest 等测试注册 | 0 |
| 上游实际可运行测试 | 0 |

源码树仅有 `Makefile.in`、`src/Makefile.in`、`tools/Makefile.in` 和 `po/Makefile.in`，均未定义 `check` 或 `test` 目标。因此上游实测基线为 0/0，没有删减或修改上游测试。

## 补全测试

- `test_package/test.cpp`：覆盖 ABI 自检、位图创建、尺寸、行宽、索引、像素打包/解包、质量统计、克隆、清空、PBM/TIFF 保存与加载，以及命令行 `--version`。
- `test_package/test_ohos.cpp`：HarmonyOS 特有测试，编译期确认 `__OHOS__`、aarch64 与 64 位 ABI，并用跨 64 位边界的 65 像素位图验证公共 API。
- 两个程序都链接并调用 Conan 包中的真实 `libminidjvu`，不是空壳测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess` 无法识别 HarmonyOS | 上游携带的 GNU config 脚本版本为 2008 年 | 补充 `HarmonyOS` → `aarch64-unknown-linux-ohos` 检测，并让 config.sub 接受 `linux-ohos` |
| 2 | 命令行没有成功返回的版本查询 | 无参数或未知参数均打印帮助并返回 2，无法用于标准 smoke test | 新增 `--version`，输出编译进库的版本并返回 0 |
| 3 | `configure` 探针在 HMDFS 上误判 libc 函数缺失 | Autoconf 以 `umask 077` 创建的临时目录在 HMDFS 映射后不可访问 | 仅将两个配置临时目录创建点改为继承构建环境权限 |
| 4 | Clang 15 拒绝旧 Autoconf 的 K&R 风格探针 | 上游将所有 pedantic 警告提升为错误 | 保留 `-pedantic` 告警，但不再把上游生成的探针告警提升为错误 |
| 5 | 旧 libtool 无法在 HMDFS 上通过当前目录推断 C++ 标签 | HMDFS 的 `getcwd()` 行为使自动标签推断失败 | 在上游 Makefile.in 中为 C/C++ 编译和链接显式指定 libtool 标签 |
| 6 | 非 8 倍数宽度的 TIFF 回读会丢失尾部有效像素 | 上游按扫描行字节数而不是图像像素宽度计算尾部填充位 | 按像素宽度清除最后一个字节的填充位，并由 13 像素宽 TIFF 往返测试覆盖 |

## 依赖版本

- `libtiff/4.7.2`，其 libjpeg-turbo、xz、zlib、zstd 和 libwebp 传递依赖由 Conan 管理。

## 验证结果

```text
conan create: PASS
上游测试: 0/0（上游确无测试）
新增消费者测试: 2/2 PASS
HarmonyOS 特有测试: 1/1 PASS
```

## 注意事项

- 该快照的公开头文件内部版本字符串为上游开发版本 `0.9`，而发行/任务版本按 SVN 快照标识 `0.8.svn.2010.05.06`；配方未篡改上游版本 API。
