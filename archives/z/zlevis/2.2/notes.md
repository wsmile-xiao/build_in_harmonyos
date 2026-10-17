# zlevis 2.2 适配笔记

## 编译环境
- 构建系统: meson（仅 install_data 安装 3 个 POSIX shell 脚本，0 编译目标）
- 编译日期: 2026-09-16
- 编译器: 无需编译（纯 shell 脚本，无二进制产物）
- 状态: built

## 软件简介

zlevis 是 Clevis (https://github.com/latchset/clevis) 的 POSIX shell 精简分支，
用于 ZFS root-pool 的 TPM2 自动解密。上游通过 Meson 将 3 个 shell 脚本
（zlevis / zlevis-encrypt / zlevis-decrypt）安装到 bin/。

## 编译步骤

纯脚本项目，无 configure/make 编译步骤。验证方式：

```bash
# 1. meson 配置
meson setup builddir --prefix=$DEFAULT_PREFIX
# 2. 上游测试（3/3 通过）
meson test -C builddir --print-errorlogs
#   1/3 zlevis:zlevis         OK
#   2/3 zlevis:zlevis-encrypt OK
#   3/3 zlevis:zlevis-decrypt OK
# 3. 安装验证
meson install -C builddir --destdir $TEST_PREFIX
# 安装 3 个脚本到 bin/，逐个执行 --summary 验证输出
```

conanfile.py 采用纯脚本打包模式（参照 acme.sh 先例）：source() 下载解压后，
package() 直接将 src/ 下 3 个脚本 copy 到 bin/ 并 chmod 0755，
无 build() 编译步骤，无运行时依赖（脚本依赖 zfs/jose/tpm2-tools 为运行时外部命令）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败 SSL CERTIFICATE_VERIFY_FAILED | git.ampel.dev 证书不被 Python urllib 信任 | 手动下载源码包放置到 $TMPDIR/builds/，用 --no-download 初始化 |
| 2 | init-build 默认写入 SKILL 安装目录 | find_project_dir() 从脚本位置向上找 SKILL.md | 设置 OHC_PROJECT_DIR=<工作区仓库> 强制项目根；清理 SKILL 目录误写产物 |
| 3 | conan-init 生成 Autotools 模板 | 模板按 URL/注册表猜测构建系统 | 按实际构建系统（meson 纯脚本）重写 conanfile.py/commands.json/MANIFEST.yml |

## 源码修改

无（未打补丁）。

## 依赖版本

无编译依赖。运行时依赖外部命令：zfs、jose、tpm2-tools（上游 Alpine 打包
depends="jose tpm2-tools tpm2-tss-tcti-device"，均为脚本调用的系统命令，
非 conan 依赖）。

## 验证结果

```bash
# 上游测试：meson test 3/3 OK
Ok:                3
Fail:              0

# 安装后脚本 --summary 验证（3/3 OK）：
$ zlevis --summary
A tool that enables automatic decryption of ZFS rpools with TPM2
$ zlevis-encrypt --summary
Encrypts using a TPM2.0 chip binding policy
$ zlevis-decrypt --summary
Decrypts a JWE using a TPM2.0 chip
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 纯脚本 application 配方（copy 3 脚本到 bin/） |
| conandata.yml | 源码 URL + sha256（b73de6ba...f86d22e） |
| test_package/test_zlevis.sh | 3 个断言：逐一执行 --summary 校验输出 |
| commands.json | CLI 工具声明（R38） |

## 注意事项

- 上游 3 个 meson test 用例均为 `--summary` 冒烟（输出描述文本），
  本适配在 test_package 中以 3 断言等价覆盖（逐一核对 --summary 输出）。
- 脚本运行时依赖 zfs/jose/tpm2-tools（TPM2 硬件相关），消费方需自备这些命令，
  纯脚本不参与 conan 依赖链。
---

**编译结束**: 2026-09-16 19:52
**最终状态**: built
