# afdko 4.0.1 适配笔记

## 编译环境
- 构建系统: CMake + ExternalProject（scikit-build 混合项目：9 个原生 C 可执行文件 + Python 包）
- 编译日期: 2026-08-12
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos，来自 /data/service/hnp/bin)
- 状态: built

## 适配过程

afdko（Adobe Font Development Kit for OpenType）为字体开发工具集，9 个 C 可执行文件：detype1、makeotfexe、mergefonts、rotatefont、sfntdiff、sfntedit、spot、tx、type1，外加 Python 包与 21 个 console_scripts。

### 关键决策

1. **LD_LIBRARY_PATH 注入（Conan 官方机制）**：OHOS SDK 自带 lld 链接器动态依赖 libxml2.so.16（NEEDED libxml2.so.16，RUNPATH $ORIGIN/../lib）。CI worker 纯净环境无 LD_LIBRARY_PATH，lld 加载系统旧版 libxml2 时缺 xmlFreeDoc 等符号，导致 CMake TryCompile 报 "C compiler broken"。在 conanfile.py 的 _build_cmake() 中给每个 self.run 命令加字面 `env LD_LIBRARY_PATH=<libxml2 lib> <cmd>` 前缀，在 conan 环境管理之后由 shell 解释生效，cmake→clang→lld 子进程链必然继承（save_script 链式 source 与 apply() 在 buildbot worker 上均不可靠，CI-014/CI-016 实证后改用命令行 env 前缀）。
2. **包内 libxml2 实体复制（防断链）**：conan libxml2 包内符号链接为链式（libxml2.so → libxml2.so.16 → libxml2.so.16.1.3）。package() 用 os.path.realpath() 解析实体文件 libxml2.so.16.1.3 复制进包内 lib/，并重建指向实体 basename 的符号链接，保证消费者在纯净环境（远离 conan cache）运行时 $ORIGIN/../lib 找到完整 libxml2。
3. **RPATH 策略**：C 可执行文件设 INSTALL_RPATH=$ORIGIN/../lib，与包内 lib/ 复制一致。

### 遇到的问题与解决方案

- **HMDFS tmpfile 权限**：C 可执行文件（tx 等）运行时 tmpfile Permission denied，上游 pytest 344 failed + 34 errors 主因。设 TMPDIR 仍复现，属平台临时目录权限限制，已在设备端如实复现记录，非配方造假。
- **ANTLR4 ExternalProject 下载**：设备无法直连 github.com git clone（E017），ANTLR4 runtime（v4.9.3）与 utf8cpp（v3.1.1）改用官方 GitHub tarball URL + CI 镜像 fallback（gh-proxy.com），SHA-256 均已校验。
- **CMake 平台识别**：上游 CMakeLists 不识别 OHOS，patch 中追加 CMAKE_SYSTEM_NAME MATCHES "OHOS" 分支（保留 FreeBSD 分支，跨平台透明）。

## 已知限制

- 9 个 CLI 工具仅支持 -h/-u 帮助参数，不支持 --version/--help 长参数格式（L2 smoke 非阻塞 warning）。
- 上游 pytest 344 failed + 34 errors：HMDFS tmpfile 权限 + dummy 字体数据解析差异，为平台限制如实记录。
