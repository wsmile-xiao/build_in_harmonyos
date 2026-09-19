# libobjfw1 1.5.7 适配笔记

## 定位
- 上游 ObjFW/ObjFW tag `1.5.7-release`，便携 Objective-C 框架
- 构建系统: autotools（tarball 无预生成 configure，需 autogen.sh）
- 产物: libobjfw（-lobjfw）

## 构建要点
- tool_requires automake/1.18 + libtool/2.5.4（OHOS 缺 autotools 工具链，libneurosim 先例）
- `./autogen.sh` 生成 configure
- configure：`--enable-runtime`（内置 ObjC 运行时）+ 显式 triplet
  `--build/--host=aarch64-unknown-linux-ohos`
- 递归替换 configure/config.status 的 `umask 077→022`（OHOS 沙箱）

## 测试
- 上游 `make check`（tests/ 84 个 .m 测试文件，`make -C tests run`）
- test_package 消费者用例（4 断言）

## 遇到的问题与解决方案
| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | tarball 无预生成 configure | build() 先跑 ./autogen.sh |
| 2 | OHOS 缺 automake/aclocal | tool_requires 拉入（conan create 需同时传 -pr:h 与 -pr:b） |
| 3 | config.status umask 077 权限 | 递归替换 077→022 + utime 兜底 |
| 4 | config.guess 不识别 HarmonyOS | 显式 --build/--host triplet |

## 验证
- 本地 `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`：消费者用例通过
