# dbab

> dnsmasq-based ad-blocking using pixelserv（基于 dnsmasq 与像素服务器的广告拦截工具集）。

## 简介

dbab 为 SOHO 服务环境提供一体化的 DHCP、DNS、本地缓存与广告拦截方案。
广告拦截在 DNS 层面完成：广告域名的请求由 `dnsmasq` 直接指向本地的
`dbab-svr` 像素服务器，由其返回一张 `1x1` 透明 GIF，无需在用户态做
URL 模式匹配，因此轻量快速，且对手机等客户端零侵入。

上游以纯 shell/Perl 脚本形式发布（`bin/` 下 5 个工具脚本），外加
`assets/` 配置样例与 man 手册页，通过一个仅做安装的 Makefile 分发，
无编译产物、无测试套件。

## OHOS 适配要点

- 上游 `make install` 依赖 `ronn` 生成的 `assets/dbab-svr.8`（缺失）且硬编码
  `INSTALL = /usr/bin/install -c`；配方改为用 Conan `copy()` 按上游
  Makefile 的安装清单逐项复制，效果等价且不依赖外部工具。
- 上游把可执行脚本装到 `sbin/`；按 Conan 惯例重定位到包内 `bin/`，
  通过 `cpp_info.bindirs = ["bin"]` 暴露。
- 配置文件装到包内 `etc/dbab/`，文档到 `share/doc/dbab/`，手册页到
  `share/man/man8/`，与上游安装路径语义一致。
- 无编译步骤；`build()` 中对 4 个 shell 脚本做 `bash -n` 语法校验，
  对 Perl 主服务脚本做载荷完整性检查。

## 排除与替代

- `dbab-get-list` 需联网从 `pgl.yoyo.org` 下载拦截列表，离线环境不可用；
  可改用 `dbab-add-list` 维护本地拦截列表（见 `assets/dbab.list+` 样例）。
- 运行时依赖系统 `perl`（`dbab-svr` 需 `IO::Socket::IP` 模块）与
  `dnsmasq`，由使用环境提供，不在 Conan 依赖中声明。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
|（无）| — | 纯脚本包，无 Conan 编译依赖 |

## 功能验证

```bash
command -v dbab-svr dbab-get-list dbab-add-list dbab-chk-list dhcp-add-wpad
bash test_package/test.sh
```

## 参考

- [上游仓库](https://github.com/suntong/dbab)
- [详细介绍（dbab.md）](https://github.com/suntong/dbab/blob/master/dbab.md)
- [Debian 软件包页](https://packages.debian.org/sid/dbab)
