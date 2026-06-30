# bibtex2html 1.99 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-06-17
- 编译器: OCaml 4.14.2 字节码 (ocamlc), clang 15.0.4 (OCaml 本身的 C 编译)
- 平台: aarch64-unknown-linux-ohos (HarmonyOS, HongMeng Kernel 1.12.0)
- 状态: built

## 编译步骤

### 前置依赖：编译安装 OCaml 4.14.2

bibtex2html 是 OCaml 程序，任务描述标注为"C/C++ 无外部依赖"不准确。实际需要 OCaml >= 3.07 编译器，cmd-pkgs 无 OCaml 预编译包。

```bash
# 下载 OCaml 4.14.2 源码
curl -fsSL -o ocaml-4.14.2.tar.gz https://github.com/ocaml/ocaml/archive/refs/tags/4.14.2.tar.gz
tar xzf ocaml-4.14.2.tar.gz && cd ocaml-4.14.2

# 修复 config.guess（平台识别）
cp ~/usr/local/share/automake-1.16/config.guess build-aux/config.guess
cp ~/usr/local/share/automake-1.16/config.sub build-aux/config.sub

# 修复 config.status umask 权限问题
sed -i 's/umask 077/umask 022/g' config.status  # 在 configure 生成后

# 编译安装
./configure --prefix=$HOME/usr/local
make world && make install
```

### 主编译：bibtex2html 1.99

```bash
cd $BUILD_SRC_DIR

# 1. 修复 config.guess
cp ~/usr/local/share/automake-1.16/config.guess .
cp ~/usr/local/share/automake-1.16/config.sub .

# 2. 配置
./configure --prefix=$DEFAULT_PREFIX
# → 发现 ocamlc: ocamlc (版本 4.14.2)
# → 仅字节码编译（无 ocamlopt）

# 3. 修复 config.status umask
sed -i 's/umask 077/umask 022/g' config.status
./config.status

# 4. 编译
make -j1
# → 生成 bibtex2html.byte 和 bib2bib.byte

# 5. 安装（Makefile 不支持 DESTDIR）
make install DESTDIR=$TEST_PREFIX  # DESTDIR 被忽略
make install                        # 直接安装到 $DEFAULT_PREFIX

# 6. 手动创建 staging 目录
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp $DEFAULT_PREFIX/bin/bibtex2html $TEST_PREFIX/$DEFAULT_PREFIX/bin/
cp $DEFAULT_PREFIX/bin/bib2bib $TEST_PREFIX/$DEFAULT_PREFIX/bin/
cp $DEFAULT_PREFIX/bin/aux2bib $TEST_PREFIX/$DEFAULT_PREFIX/bin/
# + man pages
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: Cannot find ocamlc | bibtex2html 是 OCaml 程序，非 C/C++ | 从源码编译安装 OCaml 4.14.2 |
| 2 | OCaml config.guess 不识别平台 | HarmonyOS 不在旧版 config.guess 数据库中 | 替换 automake-1.16 版 config.guess/config.sub |
| 3 | config.status: Permission denied | `umask 077 && mktemp -d` 在 HarmonyOS 上创建的目录无法写入（HMDFS/SELinux 限制） | 将 config.status 中 `umask 077` 改为 `umask 022` |
| 4 | bibtex2html config.guess 不识别平台 | 同问题 2 | 同上，替换 config.guess |
| 5 | Makefile 不支持 DESTDIR | Makefile.in 中无 DESTDIR 变量 | 手动创建 staging 目录并复制安装产物 |
| 6 | make check 无目标 | 该软件 Makefile 不提供 check 目标 | 手动执行功能测试（见 reports/test-report.md） |
| 7 | ocamlopt 不可用 | OCaml 仅编译了字节码版本（native compiler 需额外步骤） | 使用字节码编译，产物为 ocamlrun script |

## 源码修改

无补丁文件（修改的是 configure 生成的临时文件 config.status 和从 automake 复制的 config.guess，不属于源码修改）。

修改内容记录：
- `config.guess`: 从 automake-1.16 复制（版本 2023-07-20，支持 aarch64-unknown-linux-ohos）
- `config.sub`: 从 automake-1.16 复制
- `config.status` (OCaml): sed `umask 077` → `umask 022`
- `config.status` (bibtex2html): sed `umask 077` → `umask 022`

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| OCaml | 4.14.2 | 从源码编译（github.com/ocaml/ocaml） |
| ocamlrun | 4.14.2 | OCaml 运行时（随 OCaml 安装） |
| automake (config.guess) | 1.16 | 系统预装 |
| clang | 15.0.4 | 系统预装 |
| make | 4.4.1 | 系统预装 |

## 验证结果

详见 `reports/test-report.md`。

摘要：
- bibtex2html --version: ✅ 版本 1.99
- bib2bib --version: ✅ 版本 1.99
- bibtex2html --help: ✅ 完整选项列表
- bib2bib 过滤功能: ✅ 正确过滤 Book/Author
- 安装后验证: ✅ $DEFAULT_PREFIX/bin/ 可用
- 预编译包验证: ✅ tar.gz 结构完整
- 功能测试: 9 通过 / 0 失败 / 1 注意(OCaml字节码)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bibtex2html-1.99-ohos-aarch64.tar.gz | 900KB | 预编译包 |
| bibtex2html | 457KB | BibTeX to HTML 转换器 (OCaml 字节码) |
| bib2bib | 450KB | BibTeX 过滤工具 (OCaml 字节码) |
| aux2bib | 2KB | LaTeX .aux to BibTeX 提取 (Perl 脚本) |
| bibtex2html.1 | 1.2KB | man page |
| bib2bib.1 | 1.2KB | man page |
| aux2bib.1 | 483B | man page |

## 注意事项

1. **OCaml 运行时依赖**: 字节码可执行文件需要 `$DEFAULT_PREFIX/bin/ocamlrun` 运行时支持。部署时需确保 OCaml 运行时已安装。
2. **bibtex 命令依赖**: 完整 HTML 转换需要外部 `bibtex` 命令（TeX 工具链）。环境未安装时，bibtex2html 解析阶段正常但转换阶段报错。
3. **字节码非原生 ELF**: 产物为 OCaml 字节码（`ocamlrun script`），非原生 ELF 二进制。如需原生编译，需安装 OCaml native compiler (ocamlopt)。
4. **G0 干净构建验证限制**: clean-verify 无法自动安装 OCaml 依赖（非预编译包），且 config.guess/config.status 修改未固化为补丁。手动验证编译成功。
