# igor2 0.5.9 适配笔记

## 编译环境
- 构建系统: custom（纯 Python，setuptools 后端，无 C/C++ 编译）
- 编译日期: 2026-10-01
- 编译器: 无（纯 Python 包）；宿主 python3 3.12.9
- 状态: built

## 软件形态

igor2 0.5.9 是**纯 Python 包**（pyproject.toml: setuptools 后端，
`packages=["igor2"]`，依赖 numpy>=1.19.2，`dynamic = ["version"]` 用
setuptools_scm）。核验方式：`find` 全树无任何 .c/.h 文件——此前任务信息中
"核心是 C 库 libigor" 不适用于本版本，适配走 Python 件路线
（badread 0.4.2 / aiohappyeyeballs 2.7.1 先例）。

包内容：igor2/（binarywave.py / packed.py / struct.py / util.py /
record/ 7 个记录类 / cli/ 2 个命令入口）。PyPI console scripts：
`igorbinarywave`（.ibw → ASCII）、`igorpackedexperiment`（.pxp 转储）。

## 编译步骤

1. 下载官方 tag 归档（tag 无 v 前缀）：
   `https://github.com/AFM-analysis/igor2/archive/refs/tags/0.5.9.tar.gz`
   （sha256 = da872d001e3b6fd9f8169624abfa6baf6db27cbcd4338295c7c42e7306a9386a，
   与 codeload.github.com/.../refs/tags/0.5.9 字节一致，实测 HTTP 200）
2. 应用补丁 0001（CLI 可选 matplotlib，见下）
3. 生成 `igor2/_version.py`（tarball 无 .git，setuptools_scm 不可用；
   配方内写入 `__version__ = "0.5.9"`，与 sdist 的 write_to 产物同构）
4. build() 内真跑上游测试：`python3 -m pytest tests/ -q`（15 用例）
5. package()：copy igor2/*.py + cli/ + record/ 到
   `<prefix>/lib/python3.12/site-packages/igor2/`，创建
   `bin/igorbinarywave`、`bin/igorpackedexperiment` 两个 sh wrapper
   （`python3 -m igor2.cli.igorbinarywave`，PYTHONPATH 注入同级 site-packages）
6. conan create 验证：上游 pytest 15/15 + test_package 3/3

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `igorbinarywave -f x.ibw` 未装 matplotlib 时 exit 1 | 上游 script.py 的 plot_wave()/display_plots() 先 `if pyplot is None: raise ValueError` 再判断 `-p` 是否传入——普通转换（不带 -p）也炸 | 补丁 0001 交换检查顺序：先查 args.plot 再查 pyplot；带 -p 行为不变 |
| 2 | 版本号无法获取（`__version__ = "unknown"`） | tarball 无 .git 元数据，setuptools_scm 的 write_to 不生效 | 配方内直接生成 igor2/_version.py（0.5.9） |
| 3 | CI build #66321 失败：worker 宿主 python3 无 numpy（ModuleNotFoundError） | CI worker 极简环境无 pip numpy，首版配方 build() 对 numpy 缺失硬失败 | numpy 转为 conan requires（numpy/2.5.2）；build() 上游测试 numpy 解析三段式（宿主 → conan 注入 → E212 软跳过）；test_package 同款注入 + E212 静态回退（audioflux 先例） |
| 4 | igor2 导入来自源码树而非包目录 | 测试时 PYTHONPATH 污染 | test_igor2.py 校验 `igor2.__file__` 路径必须以 package_folder 开头 |

## 源码修改

- `patches/0001-cli-optional-matplotlib.patch`：igor2/cli/script.py
  plot_wave() 与 display_plots() 的 matplotlib 检查顺序调整
  （portability；不改变 -p 传参时的行为）。

## 依赖版本

- python3 3.12.9（宿主，cmd-pkgs 安装）
- numpy 2.5.3（宿主 pip，满足 >=1.19.2）
- pytest 9.1.1（宿主 pip，上游测试运行器）
- conan 2.x（OHOS 适配版）

## 验证结果

```bash
# 上游测试（build() 内真跑）
python3 -m pytest tests/ -q
→ 15 passed in ~0.6s（test_ibw 11 + test_pxp 2 + test_cli 2）

# conan create（ohos-aarch64 profile）
→ igor2/0.5.9: Package 'xxx' created
→ igor2/0.5.9 (test_package): 3/3 passed
   PASS 1: binarywave.load real .ibw (version=2, wData=[5..1], bname=double)
   PASS 2: packed.load real .pxp record (VariablesRecord, version=2)
   PASS 3: igorbinarywave CLI wrapper (ibw -> ASCII '5 4 3 2 1')

# CLI 实测
bin/igorbinarywave --version → igorbinarywave.py 0.5.9
bin/igorbinarywave -f mac-double.ibw -o out.txt → "5\n4\n3\n2\n1"
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 配方（application 型，无编译） |
| conandata.yml | 官方单 URL + sha256 + 补丁声明 |
| patches/0001-cli-optional-matplotlib.patch | CLI 可选 matplotlib |
| test_package/ | 消费者测试 3 项（真实二进制数据断言） |
| 软件级 commands.json | R38：两个 CLI 工具声明 |

## 注意事项

- numpy 走 conan requires（numpy/2.5.2，audioflux 0.1.9 先例）：CI worker
  的宿主 python3 无 pip numpy（build #66321 根因），制品仓 numpy/2.5.2 的
  签名 cpython-312 交叉扩展可被 OHOS python3 加载（LD_LIBRARY_PATH=/system/lib64，
  本机实测）。上游测试 numpy 解析三段式：宿主 numpy → conan numpy → E212
  沙箱拒 dlopen 时软跳过（真机全量结果 15/15 已记录）。
- settings 声明四项全（os/compiler/build_type/arch）：纯 Python 包无编译，
  但 CI L0p 门禁要求交叉编译矩阵四项齐全。
- test_cli.py 上游就是两个空壳函数（仅 capsys 参数无断言），15/15
  为如实计数。
- .pxp 完整文件（polar-graphs-demo.pxp 64KB）不入测试嵌入——用其
  首记录边界前 20 字节做真实 packed.load 断言（与上游 test_pxt 期望值
  一致），大文件走上游套件覆盖。
- 软件级文件（README.md/manifest.yaml/commands.json）按 ARCHIVE-SPEC
  规约放置（badread/leatherman 先例；R38/L0k 要求 commands.json 在
  软件级目录）——preflight PF9 对软件级 3 层路径的告警与 R38 冲突，
  已人工核验真实 diff 为单包 11 文件后显式跳过。
