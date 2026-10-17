# DRAFT-E655-scheme-bootstrap-generated-artifact-patch

## 问题

自举式构建的上游项目（源码是 DSL/Scheme，需要先用「引导编译器」生成 C/宿主语言
文件，再编译最终产物）在打包移植时有两个特有坑：

1. 上游 Makefile 的构建期网络行为：bootstrap 编译器与附属库靠 `wget OWLURL` /
   `git clone` 现取（radamsa 0.7：`ol-0.2.2.c.gz` + `owl-lisp/hex`），CI 沙盒
   构建不可依赖这类行为，conandata 只登记主 tarball 会直接构建失败。
2. 平台补丁没有落点：目标文件（如生成的 `radamsa.c`）在构建开始时**不存在**，
   常规「源码补丁在构建前套用」的机制（conandata `patches:` +
   `apply_conandata_patches()`）对该文件必然失败。

```text
$ make            # 上游原版
... wget https://haltp.org/files/ol-0.2.2.c.gz
... git clone https://gitlab.com/owl-lisp/hex.git
$ patch -p1 < 0001-fix-generated-radamsa.c.patch   # 构建前套用
patch: **** Can't find file to patch: radamsa.c    # 文件尚不存在
```

## 根因

构建入口是「生成物 + 编译」两段式，而包管理器的补丁/源码机制默认所有输入
在构建前已存在；两段式把「源码身份」扩展到了「构建输入（bootstrap 工具 +
附属库）+ 确定性生成物」三个面。

## 修复（三输入预置 + 生成后套补丁 + 确定性自证）

以 radamsa 0.7 为参照实现（archives/r/radamsa/0.7）：

1. **三份输入全部 conandata 预置**：主 tarball 用 `sources:`；
   bootstrap（`https://haltp.org/files/ol-0.2.2.c.gz`，即上游 Makefile 自己 pin
   的 OWLURL）与附属库归档（owl-lisp/hex 仓库，pin 上游 clone 的 main tip
   commit）放自定义键（如 `owl_bootstrap:`/`hex_library:`），source() 里
   `download()` 原件下载（sha256 校验）、build() 里还原为上游 Makefile 使用的
   布局（`gzip -dc` 成 ol.c、`tar -xzf` 到 `lib/hex`）。
2. **build() 段顺序固定**：还原布局 → 编译引导器（bin/ol）→ 生成
   （`bin/ol -O1 -o radamsa.c rad/main.scm`）→ `patch -p1` 套平台补丁 →
   最终编译。conandata `patches:` 段只做登记（元数据可见），配方注释里写明
   **为什么不能**在构建前调 `apply_conandata_patches()`。
3. **确定性自证**：两次独立构建对生成物算 sha256，一致才声明「补丁可稳定
   套用」（radamsa 的 radamsa.c 两次均为 `2d70a4ce…014095`）。生成器不确定的
   项目不能走这条路，需先锁定生成器版本/输入。

## 验证

- 干净轮 conan create 通过；`RUN: patch -p1 < …` 与 `patching radamsa.c`
  行入档 reports/conan-create.log；上游 tests/run 28/28（补丁后）。
- GitLab 归档 URL 陷阱：`-/archive/` Web 端点对非浏览器 UA 实测 403
  （conan 下载器与 curl 复现），改用 API 端点
  `https://gitlab.com/api/v4/projects/<org>%2F<repo>/repository/archive.tar.gz?sha=<fullsha>`
  即 200；两端点解包内容一致、仅顶层目录命名与压缩字节不同，sha256 以实际
  使用端点为准。

## 适用范围

Scheme/Racket/自举 C（如某些 lisp、mlton、fpc 类）以及任何「DSL 生成 C/
源文件 + 平台补丁需要落在生成物上」的包；同时适用于上游 Makefile 把
bootstrap 依赖写死为构建期网络行为的所有项目。判据：构建日志出现
`wget/curl/git clone` 且产物在「生成步」之后才出现的，都按本套路重构。

```text
复现/参照命令（本机可执行）：
conan create archives/r/radamsa/0.7 -pr <profile> --build=missing
grep -nE "RUN: patch|patching radamsa.c" <conan-create 日志>
```
