# swbis

GNU swbis — POSIX 软件管理工具集，实现 Open Group CAE C701（XDSA）软件管理规范，提供软件包创建、安装、查询、校验与目录完整性检查能力。

## 描述

swbis 提供 swpackage（打包）、swverify（校验）、swcopy（复制）、swinstall（安装）、swlist（列出已装软件）、swremove（卸载）、swconfig（配置）、swign（目录签名打包）等工具。所有工具（除 swpackage 外）经 SSH 网络透明，无需远端新服务。

## 已编译版本

| Version | Status | Date |
|---------|--------|------|
| 1.13.3 | built（待真机预检） | 2026-09-16 |

## 构建说明

- 构建系统：autotools (configure + make)
- 构建命令：`./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --with-no-flex --with-no-bison && make -j1 && make check -j1 && make install`
- 补丁数：0
- 依赖：无（零外部依赖）
- Conan profile：ohos-aarch64

## 关键适配问题

1. **config.guess 不识别 OHOS**：以 `--build/--host=aarch64-unknown-linux-gnu` 固定三元组跳过探测，编译器仍经工具链定位 OHOS 目标。
2. **configure umask 077 不兼容 HMDFS**：放宽为 `umask 022`。
3. **flex/bison 非必需**：源码包自带生成的 parser/lexer，以 `--with-no-flex/--with-no-bison` 直接使用，避免新增工具依赖。
4. **tartest1 条件跳过**：无 GNU tar 时上游静默 exit 0，配方探测 `tar --version` 是否含 GNU，如实计 skipped，不虚报 5/5。

## 依赖

无外部依赖。

## 构建产物

- `bin/swpackage` — 软件包打包器
- `bin/swverify` — 软件包校验器
- `bin/swcopy`、`bin/swinstall`、`bin/swlist`、`bin/swremove`、`bin/swconfig`、`bin/swign` — 分发管理工具

## 使用方法

```bash
# 查看版本
swpackage --version
swlist --version

# 预览打包
swpackage -s hellopkg.psf -p -v

# 打包到 tar
swpackage -s hellopkg.psf @ hellopkg.tar
tar -tf hellopkg.tar | grep catalog
```

## 测试结果

| 测试项 | 结果 | 说明 |
|--------|------|------|
| configure | 待真机预检 | |
| make -j1 | 待真机预检 | |
| make check（testsuite1，共 5 项） | 待真机预检 | shorttest/shorttest2/parsertest/parsertest2/tartest1 |
| swpackage --version | 待真机预检 | 断言 1.13.3 |
| swlist --version | 待真机预检 | 断言 1.13.3 |
| swpackage 真实打包 | 待真机预检 | tar 非空且含 catalog |

## 验证安装

```bash
conan install --requires=swbis/1.13.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 参考资料

- [GNU swbis 官方网站](https://www.gnu.org/software/swbis/)
- [swbis 1.13.3 源码下载](https://ftp.gnu.org/gnu/swbis/swbis-1.13.3.tar.gz)
- [swbis 在线手册](https://www.gnu.org/software/swbis/manual.html)
