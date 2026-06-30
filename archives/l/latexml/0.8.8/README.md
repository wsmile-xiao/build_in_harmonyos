# LaTeXML 0.8.8 — HarmonyOS (aarch64) 编译包

## 简介
LaTeXML 是一个将 LaTeX 文档转换为 XML/HTML/MathML 格式的工具，
由美国国家标准与技术研究院（NIST）开发维护。

## 版本信息
- **版本**: 0.8.8
- **许可证**: 公共领域（Public Domain）
- **源码**: https://dlmf.nist.gov/LaTeXML/releases/LaTeXML-0.8.8.tar.gz
- **构建系统**: Perl Makefile.PL (ExtUtils::MakeMaker)
- **目标平台**: HarmonyOS (aarch64)

## 安装说明

### 前置依赖
- Perl 5.42+ (已安装于 `/data/service/hnp/perl.org/perl_5.42.0/`)
- XML::LibXML 2.0210+ (XS模块，需签名后安装)
- 其他Perl模块（见test-report.md）

### 安装步骤
```bash
# 1. 解压打包文件到目标目录
tar xzf latexml-0.8.8-ohos-aarch64.tar.gz -C $DEFAULT_PREFIX

# 2. 设置Perl模块路径
export PERL5LIB="$DEFAULT_PREFIX/lib/perl5:$DEFAULT_PREFIX/lib/perl5/site_perl/5.42.2:$DEFAULT_PREFIX/lib/perl5/-harmonyos-thread-multi"

# 3. 签名XS模块的.so文件（HarmonyOS必需）
binary-sign-tool sign -keyAlias default -inFile $DEFAULT_PREFIX/lib/perl5/-harmonyos-thread-multi/auto/XML/LibXML/LibXML.so \
  -signAlg SHA256withECDSA -selfSign 1 -outFile $DEFAULT_PREFIX/lib/perl5/-harmonyos-thread-multi/auto/XML/LibXML/LibXML.so
binary-sign-tool sign -keyAlias default -inFile $DEFAULT_PREFIX/lib/perl5/-harmonyos-thread-multi/auto/Clone/Clone.so \
  -signAlg SHA256withECDSA -selfSign 1 -outFile $DEFAULT_PREFIX/lib/perl5/-harmonyos-thread-multi/auto/Clone/Clone.so

# 4. 验证安装
$DEFAULT_PREFIX/bin/latexml --version
```

## 包含文件
- `bin/` — 5个可执行脚本（latexml, latexmlc, latexmlfind, latexmlmath, latexmlpost）
- `lib/perl5/LaTeXML/` — 106个Perl模块文件
- `lib/perl5/LaTeXML/Package/` — 455个.ltxml绑定文件
- `lib/perl5/LaTeXML/resources/` — RelaxNG schema等资源文件

## 已知限制
1. HarmonyOS要求所有.so文件通过binary-sign-tool签名
2. DB_File使用内存hash替代（持久化功能受限）
3. XML::LibXSLT使用stub替代（XSLT功能不可用）
4. 部分Perl XS模块需与目标Perl架构匹配编译

## 构建配置
```yaml
build_system: perl
configure_command: perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX NOMKTEXLSR=1
dependencies: perl/5.42.0
cc: clang
cxx: clang++
```