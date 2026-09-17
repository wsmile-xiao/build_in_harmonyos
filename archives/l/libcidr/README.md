# libcidr

## 简介

libcidr 是 Matthew D. Fuller 编写的 C 语言库，用于解析、比较、输出与切分
IPv4/IPv6 的 CIDR 地址与网段：支持压缩 IPv4、PTR 反查名（in-addr/ip6.arpa）、
掩码/前缀/通配符等多种输出形式，以及网段包含、子网切分、超网合并等操作。

## OHOS 适配（1.2.3）

- 上游为纯 Makefile 工程（BSD Makefile + 预生成 GNUmakefile，无 configure），
  配方直接调用 `make -j1 CC=<clang>`；GNU make 自动选用 `GNUmakefile`。
- 顶层 `all` 仅构建 `src` + `docs/libcidr.3`（sed 生成，无需 SGML 工具）+
  `cidrcalc` 示例；`src/test` 的 7 个验证程序需单独 `make`。
- 上游唯一自动化套件是 `src/test/regression`（perl `test.pl` + `arr.pl`，
  114 个 `cidr_mkstr -_` 向量），配方以 python 复刻执行，无需 perl。
- 产物 SONAME 为 `libcidr.so.0`，别名 `libcidr.so` 以文件拷贝交付，不依赖软链接；
  static 变体归档 PIC 对象为 `libcidr.a`。
- `cidrcalc` 示例二进制随库安装至 `bin` 并签名。

## 依赖

无运行时依赖。

## 功能验证

```bash
# 消费者冒烟测试（test_package 自动执行）
./test_libcidr   # 14/14 PASS（TAP 输出，失败即非零退出）
```

## 参考

- 官网: https://www.over-yonder.net/~fullermd/projects/libcidr
- 源码: https://www.over-yonder.net/~fullermd/projects/libcidr/libcidr-1.2.3.tar.xz
