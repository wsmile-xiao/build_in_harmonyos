# libosip

## 软件描述

GNU oSIP（libosip2）是一个 LGPL 授权的 SIP（Session Initiation
Protocol）信令协议 C 语言实现，是 GNU 生态中历史最悠久的 SIP 协议栈之一，
也是 eXosip、linphone 早期版本的协议解析基础。

### 主要功能
- `libosipparser2`：SIP 消息解析/生成层 —— URI、header、SDP body 的
  解析与序列化
- `libosip2`：SIP 事务/呼叫状态机层（ICT/IST/NICT/NIST、定时器、
  有限状态机驱动）
- 纯 C、可重入、无第三方依赖（pthread 可选）

### 官方网站
https://www.gnu.org/software/osip/

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 | 产物 |
|------|------|----------|--------|------|
| 5.3.2 | built | 2026-09-10 | 0 | ✅ |

## 编译要点（5.3.2）

### 1. 包名与库名
包名 `libosip`，上游 tarball 名 `libosip2`；一个包产出两个库
`libosip2`（事务层）与 `libosipparser2`（解析层），SONAME 均为
`*.so.15`（`-version-info 15:1:0`）。

### 2. E007：config.guess/config.sub 替换
tarball 内置 2016 版不识别 `aarch64-unknown-linux-ohos`，替换为主机
automake-1.16 版本（见 conanfile.py `_patch_source_tree`）。

### 3. E011：umask 077
HMDFS 下 config.status 临时目录不可写，`umask 077 → umask 022`。

### 4. 无 RPATH
configure 后将生成的 `libtool` 脚本中 `hardcode_libdir_flag_spec`
置空，安装的 .so 不携带 DT_RUNPATH（无 patchelf 环境的标准做法）。

### 5. .codesign 重签
链接期自动签名在打包后失效，`objcopy --remove-section .codesign` 后
`binary-sign-tool -selfSign 1` 重签。

### 6. 上游测试
`--enable-test`（默认关）+ `make check`（122 torture 用例）+ 10 个
noinst 单项程序手动运行，共 132 项全部通过（详见 notes.md）。

## 补丁说明

无源码补丁；全部适配在 conanfile.py 内完成。

## 测试

- 上游：122/122 torture（99 sip + 23 malformed，含 `-c` clone 模式）
  + 10 单项程序全过
- 消费者：test_package/test_consumer.c 覆盖解析/生成/URI/header/
  body/SDP/畸形输入/事务层；OHOS 平台校验 AArch64、musl、SONAME、
  .codesign、无 RPATH
