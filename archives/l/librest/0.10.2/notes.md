# librest 0.10.2 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-17
- 编译器: clang (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

使用 Meson/Conan 生成 OHOS armv8 目标构建，启用上游 tests，关闭
introspection、Vala、examples、gtk-doc、soup2 和 fallback 下载。目标产物
前一候选曾绑定 W3 `librest-0.10.2-w3-run-022`；本轮 recipe 发生变化，该冻结清单仅作不可复用的前驱记录。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 交叉构建的测试程序不能在 x86_64 主机执行 | 目标 ELF 架构和主机 ABI 不同，Meson 会报告 `Exec format error` 或退出 77 | 使用任务私有的 native host 构建执行完整上游测试；目标运行由独立 W3 consumer 验证 |
| 2 | Flickr 上游测试访问公共 HTTPS 端点超时 | 外部服务不可控，无法形成稳定断言结果 | 仅在 host-test 源码副本中将 URL 指向 loopback fixture，保持测试注册、请求参数和断言不变 |
| 3 | 平台 CI 构建 libsoup3 时找不到 `zlib.pc` | `override=True` 只统一传递版本，不建立 PkgConfigDeps 所需的直接 requirement | 精确引用已发布的 libsoup3/3.6.5-r3；其 zlib requirement 使用 `force=True`，随后重做 Conan 与 W3 successor |
| 4 | 平台 CI `#50040` 在建图阶段报告 `glib/2.84.0.1` 与 `glib/2.84.0.1.1` 冲突 | libsoup3-r3 与 json-glib 分别选择两个精确 glib recipe 版本，根 recipe 只有 `force=True` 时在平台图解析中未形成稳定 override | 以直接 `override=True, force=True` 引用已发布的 `glib/2.84.0.1.1`，分别统一图版本并保留直接生成器依赖；须重新执行图解析、Conan、W3 和平台 CI，不能复用旧闭包 |
| 5 | Windows 本地 `conan install` 在重写 glib `.pc` 时报告 `PatternError: bad escape \\H` | `re.sub` 的 replacement 字符串会把 Windows 路径反斜杠解释成正则转义 | 改用 callable replacement 返回路径文本；重新执行本地 install 和目标验证 |
| 6 | 平台 CI `#50072` 在 `glib2/2.88.0` 的 `meson.test()` 失败；旧候选 W0 仍找不到 shared glib2 binary | 旧 recipe 同时声明 `glib2` direct，而 `libsoup3/3.6.5-r3` 也传递 `glib2`；当时的 W0 二进制闭包未发布，旧 run 不能进入新 W3 | 该失败仅约束旧候选；当前 recipe 保留已发布 `glib2/2.88.0` direct provider，并在新候选重新执行 W0、Conan、W3 和平台 CI，不把本地 graph 当作远端 binary PASS |
| 7 | `r055` package_info 拒绝 override 节点 component，`r056` 链接缺少 GLib/GObject，`r058` 暴露 direct requirement 未被组件使用，`r059` 因并发回写实际运行旧 recipe | `glib/2.84.0.1.1` 只能负责版本统一；librest 的 GLib/GObject 符号必须由独立 direct `glib2/2.88.0` 和 `glib2::glib2` component 提供；并发回写会使日志与工作树脱钩 | 增加 `glib2/2.88.0` direct requirement（保留 headers/libs/run/transitive traits）、`glib2::glib2` component 和 `pcre2/10.45` generator closure；`r060` 首行绑定 recipe SHA-256，已证明 package_info、OHOS 交叉编译、打包、CMake consumer 和 test_package 均 RC0；旧 r055-r059 仅作失败/漂移证据 |

## 源码修改

Conan 配方负责 Meson 工具链、pkg-config 依赖路径和 Windows 主机下共享库别名物化；正式 recipe 未包含 host fixture。

## 依赖版本

- glib/2.84.0.1.1
- glib2/2.88.0
- libsoup3/3.6.5-r3
- json-glib/1.10.6
- libxml2/2.15.3
- pcre2/10.45
- zlib/1.3.1.1

## 验证结果

```text
上游 native host fixture 测试: 10/10 PASS, skipped=0, timeout=0
Conan r060: graph、package_info、OHOS 交叉编译、打包、CMake consumer 和 test_package 均 RC0；日志首行绑定 recipe SHA-256
前一候选 W3 run-022: FULL_CHAIN_VALIDATION=PASS, receipts=10（本轮 recipe 变化后不可复用）
新候选 W3 run-023: 待当前 recipe freeze、fresh transfer、唯一 launch 和 consumer 验证
```

## 交付物

配方、Conan test_package、MANIFEST.yml 和 E605/E6339 知识草稿对。前一候选 W3 目标归档及其哈希证据位于任务根的 `w3/run-022/`，不进入本轮 recipe PR，也不能替代新候选 W3；`r056`/`r057` 日志保留在 evidence 目录。

## 注意事项

host fixture 只证明可重复的上游断言，不替代 OHOS 目标执行；`#50040` 的 glib 精确版本冲突和 Windows `.pc` 路径替换问题均已形成定向 recipe 修复，必须在新当前 HEAD 上重新通过平台 CI 和最新 AI Review 后才能提审。
### 对话 #1（2026-09-17）
- 用户确认继续完成本地收尾，并要求通过平台 CI 后再提审。
- 实际执行：使用已验证的 OHOS Conan package prefix 生成 release/debug tarball，并完成归档校验准备。
---

**编译结束**: 2026-09-18 04:01
**最终状态**: built
