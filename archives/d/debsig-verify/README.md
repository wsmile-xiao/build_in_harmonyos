# debsig-verify

> Debian 二进制包（.deb）签名校验工具：依据预置策略与密钥环验证包内嵌的 OpenPGP 签名。

## 简介

debsig-verify 由 Dpkg 团队维护，用于在脱离仓库的场景下验证 .deb
包的真实性：读取包内 `_gpgorigin` 签名成员，用策略目录
（policies）与密钥环目录（keyrings）中的配置逐条校验，包无签名、
签名损坏、无匹配策略时以不同退出码失败。构建系统为 Autotools，
发布包自带生成的 `configure` 脚本。

上游发布页：<https://deb.debian.org/debian/pool/main/d/debsig-verify/>
源码仓库：<https://git.dpkg.org/cgit/dpkg/debsig-verify.git>

## OHOS 适配要点

- 依赖 `libdpkg >= 1.22.0`（`PKG_CHECK_MODULES_STATIC` 强依赖）：由站内
  `dpkg/1.23.7` 整包提供其头文件与库，配方优先用 `libdpkg.pc` 做
  pkg-config 解析，缺失时回退到预置 `LIBDPKG_CFLAGS`/`LIBDPKG_LIBS`。
- `make check` 需要 `dpkg-deb`（同样取自 `dpkg` 包，已加入构建 PATH）
  与 OpenPGP 签名后端（`sq`/`gpg`，OHOS 工具链缺失，见 0.34/notes.md）。
- 工具包：产物为 `bin/debsig-verify`，包类型 `application`，
  软件级 `commands.json` 已声明。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| dpkg | 1.23.7 | 提供 libdpkg 与 dpkg-deb |
| expat | 2.8.2 | 策略 XML 解析（`AC_CHECK_LIB` 强依赖） |
| zlib | 1.3.1 | libdpkg 静态链接的传递依赖 |

## 功能验证

```bash
debsig-verify --version
debsig-verify --help
debsig-verify --policies-dir policies --keyrings-dir keyrings package.deb; echo $?
```

## 参考

- [上游源码（cgit）](https://git.dpkg.org/cgit/dpkg/debsig-verify.git)
- [上游源码镜像（GitHub）](https://github.com/guillemj/debsig-verify)
- [Debian 源码包页](https://tracker.debian.org/pkg/debsig-verify)
