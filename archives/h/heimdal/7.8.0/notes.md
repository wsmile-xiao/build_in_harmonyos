# heimdal 7.8.0 适配笔记

## 项目简介
Heimdal —— Kerberos 5 认证协议实现（KTH 开发，C 语言，BSD-3-Clause），
含 KDC/kinit/klist/kpasswd 等完整客户端+服务端。上游 GitHub heimdal/heimdal，
官方发布包 heimdal-7.8.0.tar.gz（sha256 fd87a207...）。

## 架构
- autotools 构建（官方 tar.gz 含 configure 构建产物，无需 autogen 自举）；
- 自带子库自包含：hcrypto（加密）、roken（可移植运行时）、com_err、
  wind（Unicode）——外部依赖少；
- 依赖：sqlite3（--with-db-type-preference=sqlite 数据库后端）、libedit
  （命令行编辑）、gettext/libintl、libxcrypt（密码哈希）、flex（构建工具）。

## OHOS 适配要点（同 krb5/1.22.1 先例 + E114/E216 知识）
1. **config.guess/config.sub 鸿蒙识别**（0001/0002 patch）：补
   aarch64:HarmonyOS/OHOS 分支与 ohos* os 列表（同 krb5 先例，鸿蒙 uname
   报 Linux 但识别为 ohos-linux 更准确）；
2. **E114 ac_tmp/TMPDIR patch**（0003）：configure 的
   `tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\`` 在 HMDFS 沙箱写临时
   文件被拦（"C compiler cannot create executables"）→ ac_tmp 重定向到
   `.conan2/p/b/heimdal-ac-tmp` 可写目录；
3. **依赖声明**：requirements 显式声明 sqlite3/3.53.3、libedit/20240808、
   gettext/0.22.5、libxcrypt/4.5.2（均制品仓已发布）；flex/2.6.4 作
   tool_requires（configure 生成语法分析器需要）；
4. **configure 参数**（参考 Chimera cports）：
   `--enable-kcm --without-openssl --with-hcrypto-default-backend=hcrypto
   --with-db-type-preference=sqlite --with-sqlite3 --with-libedit
   --with-libintl`（openldap/otp 可选关闭）。

## 参考先例
- **krb5/1.22.1**：另一 Kerberos 5 实现，同 autotools 构建——本配方复用其
  config.guess/sub 鸿蒙 patch 模式与 configure.wrapper 思路。

## 验证
- 模拟 CI 干净 PATH conan create 通过；
- 上游 make check（上游自带测试套件）；
- test_package：链接 heimdal 库并调用 API。
