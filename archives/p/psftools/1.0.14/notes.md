# psftools 1.0.14 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-06-26
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: published

## 编译步骤

1. 下载源码: `curl -kL -o psftools-1.0.14.tar.gz https://www.seasip.info/Unix/PSF/psftools-1.0.14.tar.gz`
2. 验证 sha256: `dcf8308fa414b486e6df7c48a2626e8dcb3c8a472c94ff04816ba95c6c51d19e`
3. 解压到 .orig (基线) 和 .work (工作目录)
4. 复制 font-util-1.4.1 的新版 config.guess/config.sub 到 config/ 子目录 (旧版 2002 年不识别 HarmonyOS)
5. 修补 configure 中 `umask 077` → `umask 022` (HMDFS 权限问题)
6. 运行 configure: `./configure --prefix=$DEFAULT_PREFIX --disable-shared`
7. 运行 make: `make -j1` (避免 HMDFS mkfifo 问题)
8. 安装: `make install DESTDIR=$TEST_PREFIX`
9. 测试: `make check` (通过)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败，无法下载源码 | HarmonyOS OpenSSL 未配置 CA 证书 | 使用 `curl -kL` 手动下载；conanfile.py source() 中用 curl + hashlib + tarfile 替代 conan 内置下载器 |
| 2 | configure 报错不识别平台 | config.guess (2002年版本) 不包含 HarmonyOS 检测分支 | 从 font-util-1.4.1 复制新版 config.guess/config.sub，添加 HarmonyOS 支持输出 aarch64-unknown-linux-gnu |
| 3 | make install 后文件权限为 0600 | HMDFS 文件系统默认 umask 077 导致权限问题 | 修补 configure 中 `umask 077` 替换为 `umask 022` |
| 4 | make -j4 失败 | HMDFS 文件系统不支持 mkfifo (configure 并行构建依赖) | 使用 `make -j1` 串行构建 |
| 5 | Conan profile 无效 | os.cpu.arch 和 tools.build:cxx_executable 不是 Conan 2 有效配置 | 修复为 arch=armv8 和 tools.build:compiler_executables (dict 格式) |
| 6 | conan 内置下载器 sha256 不匹配 | conan 下载器受 SSL 问题影响 | 在 conanfile.py source() 中使用 curl -kL + hashlib.sha256 校验 + tarfile 解压 |
| 7 | G4 产物检查失败 | conan cache path 返回 export 文件夹而非包二进制文件夹 | 在 export 文件夹创建符号链接到包二进制文件夹的 bin/lib/include |

## 源码修改

共 3 个补丁文件:

| 补丁文件 | 修改文件 | 说明 |
|----------|----------|------|
| 0001-config-config.guess.patch | config/config.guess | 替换为支持 HarmonyOS 的新版 config.guess (+1257/-841) |
| 0002-config-config.sub.patch | config/config.sub | 替换为支持 HarmonyOS 的新版 config.sub (+1645/-1222) |
| 0003-configure.patch | configure | umask 077 → umask 022 (+2/-2) |

## 依赖版本

psftools 1.0.14 无外部依赖。编译环境:
- clang 15.0.4 (HarmonyOS 自带)
- bash (CONFIG_SHELL)
- Conan 2.12.0

## 验证结果

```bash
# ELF 签名验证
$ xxd -l 4 bin/psf2txt
00000000: 7f45 4c46                            .ELF
# 34/34 个二进制均为有效 ELF

# 静态链接验证 (R26)
$ readelf -d bin/psf2txt | grep NEEDED
  0x0000000000000001 (NEEDED)             Shared library: [libc.so]
# 所有二进制仅依赖 libc.so (系统库)

# 端到端功能测试
$ psf2txt test.psf test.txt  # → 43211 bytes, 内容正确
$ psf2raw test.psf test.raw  # → 2048 bytes
$ raw2psf test.raw test2.psf # → 2080 bytes
$ psf2bdf test.psf test.bdf  # → 26927 bytes, BDF 格式正确
```

## 注意事项

1. **R26 静态链接**: psftools 是终端工具集，configure 默认 --disable-shared 即可满足静态链接要求，所有二进制仅依赖 libc.so
2. **config.guess 路径**: psftools 的 config.guess/config.sub 位于 `config/` 子目录，不在源码根目录
3. **umask 问题**: HMDFS 文件系统上 umask 077 会导致 make install 后文件权限为 0600，需替换为 umask 022
4. **make 并行**: HMDFS 不支持 mkfifo，必须使用 `make -j1` 串行构建
5. **SSL 下载**: HarmonyOS OpenSSL 未配置 CA 证书，所有 HTTPS 下载需用 curl -kL 或在 conanfile.py source() 中处理

---

**编译结束**: 2026-06-26 01:33
**最终状态**: published
