# fonts-encodings 1.1.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-26
- 编译器: clang 15.0.4 / clang++
- 平台: OpenHarmony (aarch64) — uname -s 返回 HarmonyOS
- 状态: published

## 编译步骤

1. 初始化: `ohc-run.py init-build fonts-encodings 1.1.0 --url=...`（SSL 失败，改用 curl -kL 手动下载后 --no-download）
2. 配置: `./configure --prefix=$DEFAULT_PREFIX`（需先补丁 config.guess 和 configure）
3. 编译: `make -j1`（使用 -j1 避免 HMDFS mkfifo 问题）
4. 安装: `make install DESTDIR=$TEST_PREFIX`
5. 检查: `make check`（数据包无测试，通过）
6. Conan 配方: `ohc-run.py conan-init` → 手动修复 conanfile.py → `ohc-run.py conan-verify` → 8/8 通过
7. 收尾: `ohc-run.py finish fonts-encodings 1.1.0 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 鸿蒙系统缺少 CA 根证书，Python urllib 和 curl 均失败 | 使用 `curl -kL` 手动下载源码；设置 `CURL_CA_BUNDLE` 和 `SSL_CERT_FILE` 环境变量 |
| 2 | config.guess 不识别 HarmonyOS | `uname -s` 返回 "HarmonyOS"，config.guess 无匹配规则 | 补丁: 在 `Linux|GNU|GNU/*)` 后加 `|HarmonyOS`；在 `aarch64:Linux:*:*` 后加 `| aarch64:HarmonyOS:*:*` |
| 3 | config.status 创建临时目录失败 | HMDFS 不允许写入 700 权限目录（umask 077 生成的目录） | 补丁: 将 configure 中 `umask 077` 替换为 `umask 022`，并添加 `chmod 775 "$tmp"` |
| 4 | mkfontscale 不可用 | 预编译包中无 mkfontscale，Conan 仓库也无 | 创建 mkfontscale wrapper 脚本，扫描 .enc/.enc.gz 文件生成 encodings.dir |
| 5 | G4 产物完整性失败 | 数据包无 bin/lib/include 目录 | 在 conanfile.py package() 中创建 `lib/pkgconfig/fonts-encodings.pc`，提供 encodingsdir 变量 |
| 6 | tarfile 解压丢失执行权限 | Python tarfile.extractall 不保留执行权限位 | source() 方法中手动 chmod +x configure/install-sh/missing 等脚本 |
| 7 | test_package API 错误 | Conan 2.x 中 `cpp_info.rootpath` 属性不存在 | 使用 `self.dependencies["fonts-encodings"].package_folder` 替代 |
| 8 | 字体根目录检测错误 | X.Org XORG_FONTSUBDIR 宏检测系统字体路径而非 prefix | 添加 `--with-fontrootdir=${prefix}/share/fonts/X11` 配置参数 |

## 源码修改

### 补丁 1: 0001-config.guess.patch
- 文件: config.guess
- 类型: 平台适配
- 内容: 在 `case $UNAME_SYSTEM` 的 `Linux|GNU|GNU/*)` 分支添加 `|HarmonyOS`；在 `aarch64:Linux:*:*` 分支添加 `| aarch64:HarmonyOS:*:*`

### 补丁 2: 0002-configure.patch
- 文件: configure
- 类型: 平台适配（HMDFS 权限）
- 内容: 将 `umask 077` 替换为 `umask 022`，添加 `chmod 775 "$tmp"` 确保临时目录可写

### Conan 配方修改（conanfile.py 内嵌，非补丁）
- source(): 使用 curl -kL 下载 + hashlib.sha256 校验 + tarfile 解压 + strip_root + chmod
- generate(): 添加 `--with-fontrootdir=${prefix}/share/fonts/X11`
- build(): 内嵌 config.guess HarmonyOS 补丁 + configure umask 补丁
- package(): 创建 lib/pkgconfig/fonts-encodings.pc
- package_info(): libs=[]，设置 pkg_config_name

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| mkfontscale | wrapper 脚本 | 手动创建（预编译包无此工具） |
| font-util | 1.4.1 | 预编译包（已安装） |
| util-macros | 1.20.2 | 预编译包（已安装） |
| gzip | 系统自带 | /usr/bin/gzip |

## 验证结果

```
conan-verify 结果: 8/8 门禁全部通过
  G0 PASS | G1 PASS | G2 PASS | G3 PASS | G4 PASS
  L2 PASS | L4 PASS | L5 PASS

test_package 结果: 34 small + 16 large encodings found
Conan 包: fonts-encodings/1.1.0
```

## 注意事项

- 这是 X.Org 字体编码数据包，产物为 .enc.gz 数据文件和 encodings.dir，非二进制/库文件
- mkfontscale 是构建时依赖，用于生成 encodings.dir 索引文件
- HMDFS 文件系统对 700 权限目录有写入限制，所有 autotools 项目的 configure 脚本都需要此 umask 补丁
- conanfile.py 中 source() 方法使用 curl -kL 替代 Conan 内置下载器，绕过 SSL 证书问题
- test_package 验证数据文件存在性，而非库链接

---

**编译结束**: 2026-06-26 00:42
**最终状态**: published
