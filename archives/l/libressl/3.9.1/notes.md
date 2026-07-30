# LibreSSL 3.9.1 HarmonyOS PC 适配记录

## 适配结论

LibreSSL 3.9.1 已通过 Conan Release/Debug 构建、完整上游 CTest、OHOS
aarch64 交叉编译和 HarmonyOS PC 模拟器消费者测试。该版本使用路径 B：
保留并执行全部 128 项已注册上游测试，同时对三个依赖宿主环境的额外测试
进行可复现性修复。

## 补丁

### 0001-CMakeLists.txt.patch

上游 CMake 只在 `Linux` 分支定义 POSIX 特性和平台库。补丁让相同逻辑也
识别 `OHOS` 与 `HarmonyOS`，不改变其他平台行为。

### 0002-crypto-bio-b_sock.c.patch ～ 0005-tests-pidwraptest.c.patch

- 对数字 IPv4 使用 `inet_pton()` 严格解析；对数字端口检查空值、完整消费
  和 `USHRT_MAX` 上限，使 OpenBSD 预期的输入规则在 glibc/OHOS 上一致。
- 将 `ocsptest` 的失效 OCSP 目标替换为实际返回 OCSP 响应的目标，保留两个
  公网 TLS/OCSP 交互并增加 30 秒超时。
- 通过链接器 `--wrap=getpid` 确定性模拟 PID 复用，保留“复用 PID 后父子
  PRNG 流不能相同”的安全断言，去掉等待系统 PID 自然回绕的无界循环。

完整的原始结果、128 项名称、根因和未弱化证明见
`reports/upstream-test-inventory.md`。

## 验证结果

### Conan 与上游测试

| 构建类型 | 上游执行 | 通过 | 失败 | 跳过 | test_package |
|---|---:|---:|---:|---:|---|
| Release | 128 | 128 | 0 | 0 | 通过 |
| Debug | 128 | 128 | 0 | 0 | 通过 |

`test_package` 覆盖：

1. SHA-256 公共 API 返回成功。
2. `"abc"` 摘要与标准结果逐字节一致。
3. TLS 方法可创建 SSL 上下文。
4. `libtls` 初始化成功。
5. `tls_config` 创建成功。
6. 不存在的 CA 文件必须返回失败。
7. 失败后必须提供非空错误信息。

### OHOS aarch64

- 官方 DevEco OHOS CMake 工具链，`OHOS_ARCH=arm64-v8a`。
- 860/860 构建目标成功。
- `ctest -N`：128 项。
- `bio_host` 测试程序：ELF64，Machine 为 AArch64。
- 产物：`libcrypto.a`、`libssl.a`、`libtls.a`。

### HarmonyOS PC 模拟器

- 连接目标：`127.0.0.1:5555`。
- 模拟器架构：`x86_64`。
- 使用相同补丁和 OHOS 工具链完成 883/883 构建目标。
- 将静态链接消费者程序推送到 `/data/local/tmp/libressl-3.9.1-test/`。
- 实际输出：

```text
LibreSSL crypto, SSL, TLS, and negative-path checks passed
```

- 远端退出码：0。
- 本任务未执行或声称真机验证。

## 复现命令

```bash
conan create . -s build_type=Release -c tools.build:jobs=12 --build=missing
conan create . -s build_type=Debug -c tools.build:jobs=12 --build=missing
```

OHOS 交叉编译的关键配置：

```text
-DCMAKE_TOOLCHAIN_FILE=<DevEco SDK>/native/build/cmake/ohos.toolchain.cmake
-DOHOS_ARCH=arm64-v8a
-DLIBRESSL_APPS=ON
-DLIBRESSL_TESTS=ON
-DENABLE_EXTRATESTS=ON
-DENABLE_NC=OFF
-DENABLE_ASM=ON
```

已知限制：`ocsptest` 是上游网络测试，执行时需要公网连接；测试已设置 30
秒超时，网络不可用会明确失败，不会被计为通过或跳过。
