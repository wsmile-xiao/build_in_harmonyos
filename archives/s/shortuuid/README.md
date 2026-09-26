# shortuuid

shortuuid 将 UUID 编码为较短且适合 URL 的字符串，也支持解码、自定义字母表和 `shortuuid` 命令行调用。
本归档对应上游 1.0.13，源码来自 PyPI 发布的固定 sdist。
该软件是纯 Python 包，Conan 配方复制源码文件并安装调用上游 CLI 的 `bin/shortuuid` 脚本，运行环境提供 `PYTHONPATH`。
OpenHarmony PC aarch64 真机固定 sdist 的上游 unittest 19/19、Conan 真包消费者 6/6、W3 setup/build 子步骤及工具 CI 结果已从原始证据核验。004 续测产生并独核真实 OHOS release tar，SHA-256 `edece2a79dbca6d24b003b4fc9439d6b28a1b54763fd9f443ed383a1c76717f5`，脚本 tar mode 0755。原 conan-verify G1 rc1、整体 finish rc1、原 finalize rc2，正式状态保持 pending；独立 W4 为 FAIL，官方 CI 尚未通过。
上游项目：https://github.com/skorokithakis/shortuuid
许可证：BSD-3-Clause，打包时保留 `COPYING`。
