# svgwrite

`svgwrite` 是生成 SVG 文档的纯 Python 库。上游源码与许可证来自固定的 PyPI 1.4.3 源码归档，项目地址为 <https://github.com/mozman/svgwrite>。

## OpenHarmony PC 包装

Conan 配方保存 `svgwrite`、`svgwrite.data`、`svgwrite.extensions` 的 Python 文件和 MIT `LICENSE.TXT`，通过运行环境中的 `PYTHONPATH` 提供导入路径。没有本机扩展或平台二进制。

## 测试

Conan `build()` 用 Python 标准库 `compileall -q -f svgwrite tests` 检查库与测试源码语法，不依赖 Worker 未预装的 pytest。完整上游 `python3 -m pytest tests -q` 仍保留在测试声明中；H1/W3 在提供 pytest 的环境各运行 478 项。官方 clean Worker CI #61615 的上一版输入因缺少 pytest 失败，修正后的配方尚待同一 MR 官方 CI 验证。外网字体用例用固定 CSS 和字体字节执行，仍检查实际 SVG 嵌入数据。路径解析器将不需要的正则捕获组改为非捕获组，以减少长 SVG 路径验证开销。`test_package` 用打出的包生成形状、文字和 SVG 文件并解析输出。

H1 v11 Conan G1/G2 通过，pytest 478/478、包消费者 4/4；W3 本地 CI setup/build 均 rc0，pytest 478/478、消费者 4/4。完整 `finish` 实际 rc1（step5b、step8），不能据阶段测试称收尾通过；官方 Worker CI #61615 在缺 pytest 的旧配方输入上失败；修正输入尚待官方复验。Conan Verify 的 G4 未定位 package ID，L2/L4/L5 因无 cache 路径跳过。

路径性能补丁减少捕获组开销，但不证明已解决所有回溯问题：当前长路径回归覆盖长有效路径和短非法尾部，没有覆盖“长有效前缀后接非法尾部”的高回溯情形；该边界仍可能有严重性能退化。
