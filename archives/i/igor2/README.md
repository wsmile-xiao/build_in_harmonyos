# igor2

AFM-analysis 出品的 IGOR 二进制文件读取接口（Igor Pro 的 .ibw 波形文件与
.pxp 打包实验文件 → numpy 数组），AFM 显微镜数据分析生态常用库。
igor 系列的社区维护续作（上游 W. Trevor King igor 的 fork）。

- 上游：https://github.com/AFM-analysis/igor2
- 形态：纯 Python 包（setuptools 后端，`packages=["igor2"]`，无 C/C++ 扩展）
- 依赖：numpy >=1.19.2（宿主 python3 运行时提供）
- 命令：`igorbinarywave`（.ibw → ASCII/TSV 转换）、`igorpackedexperiment`
  （.pxp 记录转储）— PyPI console scripts，OHOS 下用 sh wrapper 实现

## OHOS 适配

- **Python 件路线**：无编译步骤。包体直接安装到
  `<prefix>/lib/python3.12/site-packages/igor2/`，CLI 用
  `python3 -m igor2.cli.igorbinarywave` wrapper 提供（badread 0.4.2 先例）。
- **numpy 非 conan 依赖**：消费形态是 python3 解释器 import，制品仓
  numpy conan 包为交叉编译 .so（libc++_shared aarch64-linux-ohos ABI），
  与宿主 python3.12 不兼容；宿主 pip 的 numpy（2.5.3）才是正确 ABI。
- **版本号**：上游用 setuptools_scm（需 git 元数据），tarball 无 .git —
  配方内生成 `igor2/_version.py`。
- **CLI 可选 matplotlib**（补丁 0001）：上游 script.py 未装 matplotlib 时
  任何普通转换 exit 1（先查 pyplot 再查 -p 参数，顺序颠倒）；补丁交换
  检查顺序后，普通转换无 matplotlib 可用，`-p` 绘图行为不变。matplotlib
  本就是 pyproject 的可选 extra（`CLI = ["matplotlib"]`）。
- **测试**：上游 pytest 套件 15 用例（test_ibw 11 + test_pxp 2 +
  test_cli 2）在 build() 内真跑；test_package 消费者测试用真实 .ibw/
  .pxp 二进制数据（上游测试数据内嵌）断言解析结果 + CLI 端到端转换。

## References

- https://github.com/AFM-analysis/igor2
- https://pypi.org/project/igor2/
