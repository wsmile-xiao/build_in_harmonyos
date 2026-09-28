# DRAFT-socat-1.8.1.3-ohos-openssl-asn1-string

OpenSSL 3/4 将 ASN1_STRING 结构不透明化，直访成员的上游代码编译失败，需访问器

## 基本信息

- **草稿 ID**: DRAFT-socat-1.8.1.3-ohos-openssl-asn1-string
- **关联库**: socat 1.8.1.3（r03，OHOS aarch64 + openssl/4.0.1 实测）
- **严重度**: 2
- **类别**: openssl, compat, asn1, opaque-struct
- **触发**: 启用 OPENSSL 特性（配方 openssl/4.0.1）后编译 xio-openssl.c，GEN_IPADD peername 代码直访 `pName->d.iPAddress`（ASN1_OCTET_STRING）成员；OpenSSL ≥ 3.0 仅前向声明 `struct asn1_string_st`，成员不可见 → incomplete type 编译错误

## 错误特征

```
ASN1_STRING.*incomplete type
struct asn1_string_st
dereference of incomplete type
ASN1_OCTET_STRING
GEN_IPADD
openssl/asn1.h
```

## 根因分析

OpenSSL >= 3.0 将 `struct asn1_string_st` 设为不透明（仅在 `<openssl/types.h>`
前向声明，完整定义移入 `<openssl/asn1.h>` 且默认不展开）。依赖直访
`pName->d.iPAddress->data` / `pName->d.iPAddress->length` 等成员的上游代码
（如 socat `xio-openssl.c` 的 GEN_IPADD 分支）在编译期得到 incomplete type；
未显式包含 `<openssl/asn1.h>` 时连前向声明都不可见。

## 推荐方案

**方法**: use-asn1-string-accessors

1. **显式包含头文件**：在引用 ASN1_STRING 的源文件顶部 `#include <openssl/asn1.h>`
   （OpenSSL 3/4 下完整结构定义所在；`conf.h`/`types.h` 均不保证展开）。
2. **改用访问器**（OpenSSL 1.1+ 均存在，向后兼容）：

```c
/* 旧写法（OpenSSL 1.x 可用，3/4 编译失败） */
const unsigned char *data = pName->d.iPAddress->data;
size_t len = pName->d.iPAddress->length;

/* 新写法（OpenSSL 1.1+ / 3.x / 4.x 均可用） */
const unsigned char *data = ASN1_STRING_get0_data(pName->d.iPAddress);
size_t len = (size_t)ASN1_STRING_length(pName->d.iPAddress);
```

socat 实测补丁：`patches/0006-xio-openssl.c.patch`（r03 随 PR #12410 提交）。

## 验证/命令

```
clang -I<openssl-include> -c xio-openssl.c   # 修复前 incomplete type 报错；修复后编译通过
openssl version                              # 确认 3/4.x
# r03 conan-verify G2 干净构建 + test_package 消费者通过（WITH_OPENSSL=1）
# r03 鸿蒙专项测试 OPENSSL TLS 双向握手+数据中继 PASS（rc=0 MATCH）
```

## 适用范围

任何直接访问 ASN1_STRING / ASN1_OCTET_STRING 成员（`.data` / `.length` /
`.type` / `.flags`）的上游 C 代码，在 OpenSSL 3.x/4.x 下编译均需改为
`ASN1_STRING_get0_data()` / `ASN1_STRING_length()` 等访问器。**与平台无关**
（非 OHOS 特有），x86/ARM Linux 同源问题，可跨库复用。

## 反例 / 边界

- 仅接触 `ASN1_STRING` 指针并整体传递（不直访成员）的代码不受影响，无需修改。
- OpenSSL 1.1.x 下旧写法仍可编译，但为兼容 3/4 建议统一改用访问器。
- 若上游代码同时使用 `ASN1_STRING_to_UTF8` 等既有 API 处理内容，仅成员访问
  需替换，其余 API 调用不变。

## 回退方案

无法改源码时可用 `--disable-openssl` 回退（socat configure 选项），但会丢失
SSL/TLS 功能域与全部 openssl 用例；仅应急，非推荐。

## 关键词

ASN1_STRING, asn1_string_st, ASN1_STRING_get0_data, ASN1_STRING_length,
ASN1_OCTET_STRING, GEN_IPADD, openssl 3, openssl 4, opaque struct,
xio-openssl, incomplete type
