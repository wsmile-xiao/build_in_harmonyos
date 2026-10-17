# ccurl 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile (直接编译上游 curl.cc)
- 编译日期: {2026-09-03}
- 编译器: clang/clang++
- 状态: built
- 固定源码: https://codeload.github.com/gsauthof/ccurl/tar.gz/6f55068a7038c9ec16e6c904ab6f639163f1bb9f
- 源码 SHA-256: dba5f916b08560b671b8caf70ae6b4a8c7ca42e6da913085cf82c0d76ca03723

## 编译步骤

上游只有 Makefile，配方使用 C++ 编译器编译 curl.cc，并把对象归档为
libccurl.a；curl/8.15.0 通过 Conan 传入头文件和链接依赖。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 自动模板误判为 Autotools | 上游没有 configure 脚本 | 改为 custom/Makefile 直接编译，并在 package_info 中导出 curl::libcurl |
| 2 | `libcurl` 在 OHPCD 不存在 | OHPCD 的包名是 `curl` | 使用 `curl/8.15.0`，并以 OHOS/arm64 `--build=never` 回读通过 |

## 源码修改

新增 `patches/0001-clang-friend-declaration.patch`：上游头文件把全局回调写成
`friend size_t ::ccurl_cb_header(...)`，OHOS clang 15 会将其解析为非法限定名。
补丁把回调声明/定义统一到 `curl` 命名空间，保持回调行为不变；Conan
`apply_conandata_patches()` 已在固定提交源码上应用成功。

## 依赖版本

`curl/8.15.0`（OHPCD），其闭包 `openssl/3.5.6.1`、`zlib/1.3.1.1` 均已解析到 OHOS/arm64 二进制。

## 验证结果

```bash
W0 `conan install --requires=curl/8.15.0 --build=never -r=ohpcd`：成功。
目标 clang 15：curl.cc、消费者 test_ccurl.cpp 编译成功；conan create（OHOS/armv8，
跳过 test_package）成功，生成 libccurl.a。
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `libccurl.a` | 99716 B | OHOS/armv8 静态库（Conan package） |
| `curl.hh` | 3090 B | 导出 C++ API 头文件 |

## 注意事项

Windows MinGW 不能直接链接 OHOS ELF 依赖；主机链接失败不代表目标平台失败。
目标真机测试仍需通过任务自有传输闭包完成。

## 真机与进程生命周期验证

- W3 run-013：诊断插件漏链 `curl.cc`，`ctypes.CDLL` 在构造函数符号解析阶段失败；唯一 launch 已冻结并释放。
- W3 successor-014：补齐 `curl.cc` 后插件可加载、upstream=0，但单进程串行 probe 命中
  `Curl already globally initialized`（consumer=101）；该 run 已冻结并释放，未重放。
- W3 successor-015：runner 为 upstream 与 consumer 分别启动 Python 子进程，真实目标输出
  `upstream_rc=0 consumer_rc=0`，consumer 的 global/callback/handle/tag 阶段均执行，PID
  退出后远端根独立回读为 ABSENT。
- 目标闭包中的三个 task-private ELF 均使用官方 `binary-sign-tool` self-sign，回读确认
  恰好一个 `.codesign`、owner execute 和插件 `$ORIGIN` RUNPATH。

## 本地 Conan 重建

使用 F 盘任务 profile 指向 OpenHarmony SDK 的 clang/llvm-ar，执行
`conan create archives/c/ccurl/1.0.0 -pr:h=<task-profile> -pr:b=default --build=ccurl/* -tf ""`，
返回 `rc=0`，package ID 为 `41f4279b27e40ce968889cf4f01dfa18f520820c`，PREV 为
`fa8eddebdd95ebe3505190dc450c98a7`。`-tf ""` 只跳过 Windows host 无法运行的 AArch64
test_package；真机 W3 已独立验证 upstream/consumer 目标行为。
---

**编译结束**: 2026-09-03 15:09
**最终状态**: built
