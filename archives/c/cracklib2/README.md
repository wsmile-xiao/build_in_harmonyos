# cracklib2

## 简介

CrackLib 密码强度检查库，用于阻止用户选择容易被猜到的弱密码，提供 `FascistCheck()` C 接口供 passwd 类程序调用。

## OHOS 适配

- Autotools 构建，使用 `--without-python` 关闭 Python 绑定
- 依赖制品仓已发布的 `zlib/1.3.1`（字典压缩打包环节链接 `-lz`）
- `config.guess` 不识别 HarmonyOS，固定 `--build=aarch64-unknown-linux-gnu`
- 复用 mktemp 包装器规避 autoconf 临时目录权限问题
- 上游测试在构建目录完整执行：`make check` 编译测试驱动，`util/cracklib-check < test-data`（10 项）+ `util/testlib < test-data`（1 项）共 N=11 项
- 配方内置 `cracklib-format` 等价预处理（Python，与上游产出一致）+ `cracklib-packer` 生成测试字典，`--with-default-dict` 指向构建目录

## 依赖

- zlib/1.3.1

## 功能验证

通过链接 `libcrack` 并调用 `FascistCheckUser()` 验证完整引擎路径（规则拒绝、字典词识别、强密码通过）。HarmonyOS 上 `FascistCheck()`（走 `getpwuid`）受系统无 passwd 条目限制，输出环境提示消息，属环境限制而非库缺陷。

## 参考

- 上游仓库: https://github.com/cracklib/cracklib
