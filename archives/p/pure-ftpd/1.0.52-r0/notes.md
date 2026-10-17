# pure-ftpd 1.0.52-r0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤
1. 下载源码并解压
2. 应用 config.guess/config.sub 平台补丁
3. 在 build() 中修复 HMDFS mktemp 权限问题
4. configure --with-tls (启用 TLS，依赖 openssl/3.5.6.1.1)
5. make -j1 && make install

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 上游无 OHOS 检测 | 0001 补丁添加 aarch64:HarmonyOS |
| 2 | config.sub 不识别 ohos | 上游无 OHOS 支持 | 0002 补丁添加 ohos-linux |
| 3 | config.status 创建临时文件失败 | HMDFS: mktemp -d 创建 0700 目录，chmod 无效 | conanfile.py build() 中用 sed 替换 mktemp 为 mkdir+umask 027 |

## 依赖版本
- openssl/3.5.6.1.1 (TLS 支持)

## 验证结果
pure-ftpd --help 输出正常, make check 通过

---

**编译结束**: 2026-08-26
**最终状态**: built
