# E429 — OHOS HMDFS Autotools 临时文件与 socket 头冲突

## 错误特征
- `config.status: subs1.awk: Permission denied`
- `sockaddr_storage` 在 `linux/socket.h` 与 `sys/socket.h` 中重复定义

## 触发条件
- 构建系统：Autotools
- 平台：HarmonyOS PC arm64 / HMDFS
- 阶段：configure 或编译

## 根因分析
Autotools 默认使用 `umask 077` 创建 `config.status` 临时目录，在 HMDFS 权限模型下会导致后续临时文件不可执行或不可写。OHOS SDK 同时提供 POSIX 和 Linux UAPI socket 定义，部分包含路径会触发重复定义。

## 解决方案

### 推荐方案
1. 在探索源码中将 `configure` 的临时目录 umask 调整为 `022`，再用 `refresh-patch --auto` 生成补丁。
2. 在 Conan `AutotoolsToolchain` 中追加 `-D_UAPI_LINUX_SOCKET_H` 和 `-D__kernel_sa_family_t=sa_family_t`，不要把这些宏写入补丁。
3. 用 `make check`、Conan `conan create` 和 CI `build_and_test.sh` 验证。

### 禁止做法
- 不提交 `file://` 本地源码 URL。
- 不在补丁中直接加入无必要的平台宏。
- 不用普通 bash 执行仓库声明为 zsh 的 CI 脚本。

## 验证
```bash
OHC_W3_TIMEOUT=3600 zsh ci/conan/build_and_test.sh archives/l/libnftnl/1.3.1
```

结果：W3 通过，Conan 消费者测试 1/1 通过，上游 `make check` 32/32 通过。

## 关联条目
- E011 — Autotools 临时目录权限
- E119 — Linux/POSIX socket 头冲突
