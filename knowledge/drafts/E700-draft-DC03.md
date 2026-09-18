# E700 — 固定端口测试套件在 ctest 并行执行下互相冲突 → CTEST_PARALLEL_LEVEL=1 串行化

## 错误特征

```
warn/network TCP 8 | Error binding the socket to the address localhost (Address in use)
error/network TCP | Unable to establish connection: no available sockets
error/client | The connection has timed out before it could be fully opened
```

ctest 并行（CTEST_PARALLEL_LEVEL=16）时同一仓库 146 项测试中 30 项失败，
失败项全部为 server/client 网络套件；部分表现为虚假 SEGFAULT、Broken pipe、
No suitable endpoint found；改为串行（=1）后 0 失败。

## 触发条件

- 构建系统: CMake（conan create 内嵌 ctest）
- 阶段: testing（build() 内 cmake.test()）
- 前提: 多个测试套件各自用默认配置绑定同一固定端口（如 open62541 每个
  server 套件经 UA_ServerConfig_setDefault 绑定 4840）

## 根因分析

open62541 的 server 测试套件全部经 `UA_ServerConfig_setDefault` 绑定固定默认
端口 4840；配方作者为加速曾设 `CTEST_PARALLEL_LEVEL=16`，16 个套件同时抢
同一端口，产生 Address in use / Broken pipe / 假 SEGFAULT / No suitable
endpoint 等互斥表象，无法区分真实失败与并行干扰。上游 CI 默认即串行执行。

## 解决方案

### 推荐方案
- 方案: conanfile.py `generate()` 中设 `env.define("CTEST_PARALLEL_LEVEL", "1")`
- 验证: 串行 ctest 146/146 通过（`conan create` exit_code=0；
  `reports/conan-create-r11.log`、`.ci-result.json`）

### 禁止策略
- 禁止把并行下的表象失败当作库质量问题上报或据此打补丁
- 禁止为绕过冲突而删测试或用 `--rerun-failed` 掩盖未运行项

## 适用范围与边界

- 适用: 任何 check 框架/固定端口 server 测试套件在 ctest 并行下的冲突
- 边界: 若测试套件本身支持随机/独立端口，可保留并行；串行只是保守且与
  上游默认一致的修复
