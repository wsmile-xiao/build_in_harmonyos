# avimetaedit 1.0.2 适配笔记

## 编译环境
- 构建系统: autotools（autogen.sh 生成 configure，无预生成 configure）
- 编译日期: 2026-08-22
- 编译器: clang/clang++ 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. 使用 cmd-pkgs 安装 autotools 构建工具链
#    automake 1.16.5, libtool 2.4.7, sed 4.10, autoconf 2.72
# 2. 进入 CLI 构建目录
cd $BUILD_SRC_DIR/Project/GNU/CLI
# 3. 生成 configure
bash autogen.sh
# 4. 配置 + 编译（DEFAULT_PREFIX 见 .build-context）
./configure --prefix=$DEFAULT_PREFIX
make -j2
# 5. staging 安装验证
make install DESTDIR=$TEST_PREFIX
```

产物：单个可执行文件 `avimetaedit`（ELF 64-bit arm64，动态链接）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `/storage/Users`（tmpfs hmmac=use_task）下 config.status 创建临时目录失败 `can't create ./confXXXXXX/subs1.awk: Permission denied` | autoconf 生成的 configure 用 `(umask 077 && mktemp -d)` 创建 `drwx--S---`(2700, setgid 强制继承) 目录；hmfs 上该目录对构建进程（gid 20020101，groups 含 1006）不可写 | build() 内 sed：configure 中两处 `umask 077` → `umask 022`（参考 a52dec 配方同型 patch） |
| 2 | conan create 的 Popen(shell=True) 子进程无法直接 exec hmfs 上的 shebang 脚本（`bad interpreter: Permission denied`） | hmfs 对 shebang 脚本的直接 exec 受限 | aclocal/automake 用 `perl` 显式解释，autoconf 用 CONFIG_SHELL(bash) 显式解释 |
| 3 | cmd-pkgs automake 1.17 的 aclocal 泄漏 `@am_AUTOM4TE@` 字面量 | 1.17 打包时 aclocal.m4 宏替换缺陷 | bootstrap 优先用 `aclocal-1.16`/`automake-1.16`（1.16.5 正常） |

## 源码修改

无静态补丁。bootstrap 生成的 configure 由 build() 内 sed 动态处理 umask
（内容级替换，对 automake/autoconf 版本差异稳健，避免针对生成文件打补丁的行号漂移）。

## 依赖版本

- 运行时：无第三方 conan 依赖（vendored ZenLib/TinyXml/MD5），仅系统 pthread
- 构建工具（tool_requires）：automake/1.18, autoconf/2.72, libtool/2.5.4（制品仓已发布）

## 验证结果

```bash
# test_package 功能测试：12/12 断言通过
# 覆盖：--Version, 解析官方 AVI 样本(AVC/AC-3/AAC), XMP 插入+导出回环,
#       aXML 插入, INFO 编辑(--ISFT), MD5 生成+嵌入, --simulate 不写盘,
#       编辑后媒体数据保持
```

## 注意事项

- 上游无自动化测试（make check 为空目标，无 tests 目录）；测试使用 MediaArea 官方
  RegressionTestingFiles 的 3 个 AVI 样本（AVC/AC-3/AAC）作为输入做完整功能断言。
- ElF 由 CI 流水线签名；本地验证可直接执行。
---

**编译结束**: 2026-08-22 21:58
**最终状态**: built
