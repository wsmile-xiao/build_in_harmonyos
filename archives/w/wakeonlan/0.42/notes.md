# wakeonlan 0.42 编译笔记

## 编译信息
- 软件名: wakeonlan
- 版本: 0.42
- 来源: Homebrew (GitHub jpoliv/wakeonlan)
- 构建系统: Perl (ExtUtils::MakeMaker)
- 下载量: 3220

## 编译过程

### 下载
- GitHub无法直接访问, 通过gh-proxy.com镜像下载源码
- URL: https://gh-proxy.com/https://github.com/jpoliv/wakeonlan/archive/refs/tags/v0.42.tar.gz
- 源码大小: ~9KB (简单Perl脚本工具)

### 构建
- `perl Makefile.PL INSTALLDIRS=site PREFIX=$DEFAULT_PREFIX` → 成功
- `make` → 成功 (纯Perl脚本, 无需编译)
- `make install DESTDIR=$TEST_PREFIX` → 成功, 装到 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/wakeonlan`

### 测试
- `make test` → 部分失败 (缺少Test::Perl::Critic和Test::Spelling模块)
  - 这些是开发者/作者测试, 不影响功能
  - t/91_pod.t, t/92_pod_coverage.t: 跳过(缺少Test::Pod)
- 手动验证: `wakeonlan --version` → "wakeonlan 0.42" ✅

### 安装
- `make install` → 安装到 `$DEFAULT_PREFIX/bin/wakeonlan`
- shebang: `/data/service/hnp/perl.org/perl_5.42.0/bin/perl -w`
  - 此路径为鸿蒙平台Perl实际安装路径, 无需修改

### 打包
- 纯Perl脚本, 无ELF二进制文件, 无需ELF签名
- 打包产物: wakeonlan-0.42-ohos-aarch64.tar.gz (16KB)

## 关键知识
1. Perl脚本工具使用ExtUtils::MakeMaker构建系统
2. perl Makefile.PL PREFIX=$DEFAULT_PREFIX INSTALLDIRS=site
3. 纯脚本项目无需ELF签名(无二进制文件)
4. make install后Perl自动修正shebang为平台实际Perl路径
5. 作者测试(Test::Pod, Test::Perl::Critic等)缺失不影响功能验证

## 依赖
- perl >= 5.42.0 (已安装)

---

**编译开始**: 2026-06-03

**编译结束**: 2026-06-03
**最终状态**: published
---

**编译结束**: 2026-06-03 13:22
**最终状态**: published
