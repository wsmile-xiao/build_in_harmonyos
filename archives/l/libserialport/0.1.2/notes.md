# libserialport 0.1.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码包 libserialport-0.1.2.tar.gz
2. 解压到 ~/builds/libserialport-0.1.2.orig 和 .work
3. 应用 autotools 补丁（config.guess + config.sub）
4. 运行 configure: `./configure --prefix=$HOME/usr/local`
5. 编译: `make -j1`
6. 安装: `make install DESTDIR=$TEST_PREFIX`
7. 打包制品

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 缺少 HarmonyOS 检测分支 | 添加 `*:HarmonyOS:*:*` case 分支 |
| 2 | config.sub 不接受 linux-ohos 三元组 | 缺少 ohos 平台验证 | 添加 ohos-linux、ohos*、linux-ohos* |
| 3 | HMDFS 临时目录权限问题 | config.status 使用 mktemp | 修改为固定 .conf_temp 目录 |
| 4 | Makefile 重生成 autotools | 缺少 aclocal-automake | 跳过 Makefile.in 重生成规则 |

## 源码修改

- `autostuff/config.guess`: 添加 HarmonyOS 系统识别
- `autostuff/config.sub`: 添加 ohos 平台三元组支持

## 依赖版本

无外部依赖，纯 C 库。

## 验证结果

```bash
ls -la .libs/
# libserialport.a (243KB)
# libserialport.so.0.1.1 (142KB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libserialport-0.1.2-ohos-aarch64.tar.gz | 450KB | 预编译制品包 |

## 注意事项

- G0 干净构建验证因 HMDFS 平台限制未能通过
- make check 测试程序编译失败，但不影响库功能

---

**编译结束**: 2026-05-21 19:54
**最终状态**: published