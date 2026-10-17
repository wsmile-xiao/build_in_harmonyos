# libobjfwrt1 1.5.7 适配笔记

## 定位
- ObjFW runtime（上游 ObjFW/ObjFW tag `1.5.7-release`，src/runtime/）
- 产物: libobjfwrt（-lobjfwrt），头文件 ObjFWRT.h（objc_* API）
- 与 libobjfw1 同源 tarball，本包只产出 runtime 库

## 构建要点（复用 libobjfw1 适配）
- tool_requires automake/1.18 + libtool/2.5.4（OHOS 缺 autotools 工具链）
- `./autogen.sh` 生成 configure
- config.sub 注入 ohos 支持（基本 OS 列表 + linux-ohos*- 组合；
  autogen 后重新注入，因 automake --add-missing 会覆盖）
- 显式 `--build/--host=aarch64-unknown-linux-ohos`
- `--without-tls`（OHOS 无 TLS 实现）
- in-source layout（顶层 Makefile 源码自带）
- 递归替换 configure/config.status 的 `umask 077→022`

## 测试
- test_package 消费者用例（4 断言）：runtime objc_* API roundtrip

## 遇到的问题与解决方案
| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | tarball 无预生成 configure | build() 先跑 ./autogen.sh |
| 2 | config.sub 不识别 ohos | autogen 后注入 ohos（两处） |
| 3 | out-of-source 找不到 Makefile | in-source layout |
| 4 | config.status umask 077 | 递归替换 077→022 |

## 验证
- 本地 `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`：消费者用例通过
