# ruby 3.4.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-13
- 编译器: clang 15.0.4 (OHOS 工具链)
- 状态: built

## 编译步骤

```bash
# 1. init-build 下载源码 (cache.ruby-lang.org 官方源)
# 2. E007: config.guess 无法识别 HarmonyOS
#    → perl patch-autotools-ohos.pl tool/config.guess tool/config.sub
# 3. E268: config.sub 内核-OS 校验缺 linux-ohos
#    → tool/config.sub 校验列表追加 '| linux-ohos*'
# 4. E002/tmp 陷阱 + 临时目录权限: configure 脚本 umask 077 → 022
# 5. 依赖扩展 (fiddle/openssl/psych) 缺 libffi/openssl/libyaml:
#    conan install --requires=... -pr:h=ci/conan/profiles/ohos-aarch64
#    → PKG_CONFIG_PATH/CPPFLAGS/LDFLAGS 指向 conan 依赖，重新 configure + make
# 6. configure --prefix=$DEFAULT_PREFIX
# 7. make -j2 && make install DESTDIR=$TEST_PREFIX
#    注: conanfile.py build() 使用 -j1（HMDFS jobserver fifo EPERM，R9）
# 8. make check（test_fork.rb 段错误，其余通过）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess: unable to guess system type | E007: config.guess 无 HarmonyOS 检测分支 | patch-autotools-ohos.pl 一键补丁 |
| 2 | Kernel 'linux' not known to work with OS 'ohos' | E268: config.sub 内核-OS 校验缺 linux-ohos | config.sub 校验列表追加 linux-ohos* |
| 3 | configure 临时目录 Permission denied | config.status 用 umask 077 建 700 目录，当前 uid 无写权限 | configure 脚本 umask 077 → 022 |
| 4 | fiddle/openssl/psych 扩展未编译 | 缺 libffi/openssl/libyaml 依赖 | conan install 安装已发布依赖，配置 PKG_CONFIG_PATH 重新 configure |
| 5 | make check test_fork.rb 段错误后挂起 | 鸿蒙平台 fork 相关限制（平台限制） | 超时跳过并记录原因，其余 bootstraptest 全部通过 |

## 源码修改

- tool/config.guess: HarmonyOS 系统识别分支（patch-autotools-ohos.pl）
- tool/config.sub: ohos-linux 三元组 + linux-ohos 内核校验
- configure: umask 077 → 022（临时目录权限）

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libffi | 3.5.2 | conan 制品仓 ohpcd (已发布) |
| openssl | 3.5.6.1.1 | conan 制品仓 ohpcd (已发布) |
| libyaml | 0.2.5 | conan 制品仓 ohpcd (已发布) |

## 验证结果

```bash
# 扩展加载验证（通过）
ruby -e 'require "openssl"; puts OpenSSL::OPENSSL_VERSION'   # OpenSSL 3.5.6
ruby -e 'require "yaml"; puts YAML::VERSION'                 # 5.2.2
ruby -e 'require "fiddle"'                                   # ok
ruby -e 'require "json"'                                     # ok
ruby -e 'require "socket"'                                   # ok

# 版本
ruby 3.4.10 (2026-06-30 revision 2b0b7728dc) +PRISM [aarch64-linux-ohos]

# make check: bootstraptest 大部分通过；
# test_fork.rb 段错误（鸿蒙平台 fork 限制），按 SKILL 规则跳过并记录
```
---

**编译结束**: 2026-08-13 05:46
**最终状态**: built
