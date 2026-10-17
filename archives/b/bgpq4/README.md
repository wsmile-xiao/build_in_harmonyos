# bgpq4

bgpq4 is a BGP filtering automation tool. It generates router configuration snippets such as prefix-lists, extended access-lists, policy-statement terms, and AS-path filters from IRR data.

## OHOS 适配要点

- 上游 `1.16` release tarball 只有 `configure.ac` 和 `Makefile.am`，没有预生成 `configure`。当前 recipe 绕过 Autotools，在 `build()` 中直接编译 C 源码。
- 构建系统为 custom direct compile，产物是命令行工具 `bgpq4` 和 man page。
- 上游 `make check` 包含 `bgpq4 -v` 以及在线 IRR 查询；在线测试依赖 DNS 和外部网络。

## 依赖

无外部 Conan 依赖。

## 功能验证

- 上游测试：`make check`
- Conan 消费者测试：运行 `bgpq4 -v` 并验证版本输出包含 `bgpq4`。

## 参考

- https://github.com/bgp/bgpq4
- https://github.com/bgp/bgpq4/releases/tag/1.16
