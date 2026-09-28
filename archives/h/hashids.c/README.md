# hashids.c

[hashids.c](https://github.com/tzvetkoff/hashids.c) 是 [Hashids](https://hashids.org/) 的 C 语言移植库：从一个或多个数字生成 Youtube 风格的短字符串 ID（用于隐藏数据库自增 ID），支持编码/解码、hex 编解码、salt 与自定义 alphabet。

## 版本

- 1.2.2（当前适配）

## 构建

- 构建系统：autotools（`./bootstrap && ./configure && make`）
- 上游 tag 归档不携带生成的 `configure`，配方在 `build()` 中 `autoreconf -fi` 生成（tool_requires: automake/1.18 + libtool/2.5.4）
- 产物：`libhashids`（静态库默认）+ `bin/hashids` 命令行工具 + 上游 `test` 测试程序

## OHOS 适配

- autotools 在 HarmonyOS 正常可跑（注入 libtoolize 后 bootstrap 成功）
- E114：生成 configure 的 `umask 077 && mktemp -d` 在 HMDFS 下产生不可写临时目录，配方在 build() 中去除该 umask
- 上游测试 `make check`（63 个 testcases）已集成进配方 build() 并实际运行通过
- `test_package` 消费者测试调用公开 API（`hashids_encode/decode/encode_one/encode_hex`）

## CLI 用法

```bash
hashids 1            # => jR
hashids -d jR        # => 1
```

commands.json 声明见本目录 `commands.json`。