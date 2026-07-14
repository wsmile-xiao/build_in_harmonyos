# libkeccak

Keccak 家族哈希库（bit-oriented lanewise 实现），支持 SHA-3、SHAKE、RawSHAKE、cSHAKE、可变长输出、状态序列化、敏感数据擦除与 HMAC。

## 基本信息

| 属性 | 值 |
|------|-----|
| License | ISC |
| 语言 | C（C99，POSIX Makefile） |
| 构建系统 | makefile |
| 当前版本 | 1.4.3 |
| 类型 | 库（默认静态） |
| 依赖 | 仅 libc |

## 安装产物

- **静态库**：`lib/libkeccak.a`（`shared=True` 时为 `libkeccak.so.1.4` + soname 软链接）
- **头文件**：`include/libkeccak.h`、`include/libkeccak/{keccak,sha3,shake,rawshake,cshake,hmac,extra,util,legacy}.h`
- **许可证**：`licenses/LICENSE`

## 核心 API

- `libkeccak_spec_sha3()` / `libkeccak_spec_shake()` — 填充算法参数
- `libkeccak_spec_check()` — 参数合法性校验
- `libkeccak_state_initialise()` / `libkeccak_state_destroy()` — 海绵状态生命周期
- `libkeccak_update()` / `libkeccak_digest()` — 吸收消息与挤出摘要
- `libkeccak_hmac_initialise()` / `libkeccak_hmac_digest()` — HMAC
- `libkeccak_behex_lower()` — 摘要转十六进制

## HarmonyOS 平台注意事项

1. 上游 `config.mk` 默认 `CC = c99`，鸿蒙无 `c99` 驱动，配方从 Conan toolchain 传入 `CC`/`AR`。
2. 打包不走 `make install`：其安装规则含 man 手册与 `ln -sf`，HMDFS 下软链接不可覆盖。
3. 纯 C99 + libc，无 glibc 专有接口，musl 下无需补丁。
