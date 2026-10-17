# endlessh 1.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

endlessh 是单文件 C 程序，使用 raw POSIX Makefile 构建（无 configure 脚本）。
实际编译步骤如下：

1. **source 阶段**: `source .build-context-endlessh-1.1` 加载构建上下文后，Conan recipe 的 `source()` 方法调用 `get(self, **self.conan_data["sources"], strip_root=True, filename="endlessh-1.1.tar.gz")` 从 codeload.github.com 下载源码 tarball 并解压到 `$BUILD_SRC_DIR`。
2. **build 阶段**: `cd $BUILD_SRC_DIR && make CC=clang -j1`。从 Conan conf 字典中取出编译器路径后执行 make，使用 `-j1`（单文件程序足够且遵循 R9 规范）。
3. **package 阶段**: OHOS 平台无 `install` coreutils 命令，改用 Conan `copy()` 直接将 `endlessh` 二进制和 `endlessh.1` manpage 拷贝到 package 目录的 `bin/` 和 `share/man/man1/`。
4. **test_package**: test.sh 执行 `endlessh -h`，输出帮助信息，exit 0，验证二进制可运行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | BadZipFile: File is not a zip file | codeload URL `.../tar.gz/refs/tags/1.1` 末段是 tag 名 "1.1"（无扩展名），Conan get() 按末段推断文件名，默认用 zip 解码器解压 tar.gz 文件 | 在 `get()` 调用中显式传 `filename="endlessh-1.1.tar.gz"`，使 Conan 通过扩展名正确选择 tar.gz 解码器 |
| 2 | KeyError / AttributeError 获取编译器路径 | profile 中 `tools.build:compiler_executables` 是字典格式 `{'c': '...', 'cpp': '...'}`，而非单独的键，直接用 `self.conf.get("tools.build:compiler_executables")` 返回字典字符串或报错 | 使用 `check_type=dict` 参数整体获取字典，再 `.get("c")` 取出 C 编译器路径 |
| 3 | make: *** No targets specified. No makefile found | `self.run("make ...")` 默认在 `build_folder` 执行，但 endlessh 的 Makefile 在 `source_folder`（raw makefile 不生成到 build 目录） | 在 `self.run()` 中显式指定 `cwd=self.source_folder`，使 make 在源码目录执行 |

## 源码修改

无补丁。endlessh 源码无需任何修改即可在 OHOS 上编译。

## 依赖版本

无依赖。endlessh 是自包含的单文件 C 程序，仅依赖 POSIX 标准库。

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify endlessh 1.1
# G1: PASS — 配方完整性检查通过（name/version/source/build/package/package_info/export_sources/conandata/test_package 全部通过）
# G2: PASS — conan create 成功构建，test_package 测试通过
# G3: PASS — 无 lib/ 目录（纯可执行包），无系统同名库冲突
# G4: PASS — 程序包验证
# L2/L4/L5: PASS (跳过，无 cache 路径)

$ endlessh -h
Usage: endlessh [-vh] [-46] [-d MS] [-f CONFIG] [-l LEN] [-m LIMIT] [-p PORT]
  # exit 0 — 二进制可正常运行

# 二进制安全属性: NX/PIE/Full RELRO 合格
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan recipe，package_type=application，raw makefile 构建 |
| conandata.yml | 源码下载元数据，远程 URL + sha256 |
| manifest.yaml | 版本级 manifest，构建系统 makefile |
| notes.md | 本适配笔记 |
| test_package/conanfile.py | 测试包配方 |
| test_package/MANIFEST.yml | 测试包 manifest |
| test_package/test.sh | 测试脚本，执行 endlessh -h |
| patches/ | 空目录（无补丁） |
| reports/conan-verify-report.md | conan-verify 验证报告 |
| reports/conan-create.log | conan create 构建日志 |

## 注意事项

- endlessh 是 SSH tarpit，监听端口默认 2222，运行需要 root 权限绑定端口。测试仅验证 `-h` 帮助输出。
- conandata.yml 必须保持远程 URL（codeload.github.com），CI 的预下载和镜像注入机制会自动处理网络可达性。
- 知识图谱草稿 E321 已生成，记录了 3 个通用编译问题供后续软件复用。
---
**编译结束**: 2026-08-19 10:06
**最终状态**: built
---

**编译结束**: 2026-08-19 10:18
**最终状态**: built
