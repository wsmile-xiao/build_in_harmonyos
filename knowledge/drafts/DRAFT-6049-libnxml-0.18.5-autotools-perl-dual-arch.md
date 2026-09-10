# DRAFT-6049-libnxml-0.18.5-autotools-perl-dual-arch — conan autotools 闭包内两套 perl 5.42.2 的 arch 目录冲突导致 aclocal Cwd.c handshake mismatch

- 触发事件：libnxml 0.18.5 适配，conan create 首跑 autoreconf 即败
- 路径：Path B（知识库扩展）
- 编号：DRAFT-6049

## 现象

conan create 走到 autoreconf -fi 时，conan automake/1.18 包的 aclocal
（sh 包装器 exec `.aclocal-real`）立即报：

```
Cwd.c: loadable library and perl binaries are mismatched
(got handshake key 0xf880080, needed 0xf180080)
```

或（取决于 PERL5LIB 内容）`Can't locate Cwd.pm in @INC`。

## 根因

本机（OHOS PC）同时存在两套 perl 5.42.2：

- 系统 perl `/storage/Users/currentUser/usr/local/bin/perl`
  （arch 目录名带 harmonyos）；
- conan perl/5.42.2 包（arch 目录 aarch64-linux-thread-multi）。

三层因素叠加：

1. conan 的 automake/autoconf 包各自包装脚本时记录的 shebang 不同源——
   automake 包的 `.aclocal-real` shebang 构包时的系统 perl（绝对路径），
   autoconf 包的包装器支持 `$PERL` 覆盖且 `*-real` 直接 shebang conan perl，
   同一 conanbuild env 内无法用单一 PERL5LIB 同时满足两套二进制；
2. conan perl 包被重定位（安装前缀 ≠ 编译前缀）后 @INC 编译期常量为
   空路径，必须依赖 PERL5LIB，于是 PERL5LIB 一定会出现 conan arch 目录，
   污染系统 perl 进程；
3. 系统 perl 进程加载 PERL5LIB 里另一套 perl 的 Cwd.so（XS 模块）即报
   handshake mismatch——XS 模块与 perl 二进制必须同源编译。
   automake/autoconf 的业务模块（Automake/*.pm、Autom4te/*.pm）都是纯
   Perl，不依赖任何 XS；XS 冲突只发生在核心模块（Cwd 等）。

## 可复用处置（对任何 autoreconf 自举的 conan 配方）

build() 的自举命令显式统一解释器：

```python
am = self.dependencies.build["automake/1.18"].package_folder
ac = self.dependencies.build["autoconf/2.72"].package_folder
self.run('PATH="<autoconf/bin>:<m4/bin>:$PATH" '
         'PERL=perl PERL5LIB="%s/share/automake-1.18:%s/share/autoconf" '
         'autoreconf -fi' % (am, ac), env="conanbuild")
```

1. `PERL=perl`：autoconf 包包装器以 `$PERL` 调 `.autoreconf-real` /
   `.autom4te-real`，全链改走 PATH 上的系统 perl；
2. PERL5LIB 收敛为仅两个包的纯 Perl 模块目录
   （`share/automake-1.18`、`share/autoconf`），核心 XS 模块回落系统
   perl 自带 @INC——Cwd.so 与 perl 二进制必然同源，handshake 不再失配；
3. 不改缓存包、不打补丁、不 shim，配方自包含。

## 判定要点

- 与 E116（预编译 automake 的 @INC 缺 Automake/Config.pm）区分：E116 是
  **纯 Perl 模块路径缺失**（编译/换 automake 包可解），本条是**两套 perl
  二进制的 XS 模块失配**（必须统一解释器，加 PERL5LIB 只会加重）；
- 与 DRAFT-6051（远端 automake 包丢点文件）区分：6051 是 `.aclocal-real`
  **文件不存在**（No such file or directory），本条是文件存在但**执行时
  XS 失配**；前者修包，后者修解释器环境；
- 快速定性：`PERL5LIB=<conan perl libs> 系统 perl -MCwd` 复现同错即命中。

## 实证

- 直接复现：PERL5LIB 指向 conan perl 库目录时系统 `perl -MCwd` 报同错；
  PERL5LIB 只含 automake share 目录时 `aclocal --version` 正常（1.18）；
- libnxml 0.18.5 修复后 autoreconf 一次通过，configure 17606 行正常生成，
  conan create --build=libnxml/* 全链 CREATE=0；
- 日志：/storage/Users/currentUser/tmp/libnxml-adapt/conan-create.log；
- 配方：archives/l/libnxml/0.18.5/conanfile.py build()。

## 边界与适用范围

只影响自举阶段（autoreconf -fi 一次调用）；configure/make 阶段不涉及
perl。依赖本机系统 perl 完整（OHOS PC 自带 5.42.2 harmonyos 版满足）。
若构建机系统 perl 缺 Automake 依赖的核心模块（极少），则需退回给 conan
perl 一套完整 PERL5LIB 并统一用 conan perl 跑 autoconf 侧脚本，同时把
automake `*-real` 的 shebang 统一到 conan perl（需重建 automake 包）。

任何在 OHOS PC 上以 tool_requires automake/libtool/autoconf + autoreconf
自举的 conan 配方，出现 Cwd.c handshake / Can't locate Cwd.pm 时套用同一
`PERL=perl` + 双 share 目录 PERL5LIB 组合；automake 大版本不同时把
`share/automake-1.18` 换成对应版本目录。
