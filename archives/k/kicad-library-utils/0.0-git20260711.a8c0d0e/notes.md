# notes.md — kicad-library-utils 0.0-git20260711.a8c0d0e 适配笔记

## 1. 上游形态与版本语义

上游 <https://gitlab.com/kicad/libraries/kicad-library-utils> 是 KiCad 官方库的
维护工具仓库，**没有发布 tag**（滚动 master 开发模式），因此版本号取
`0.0-git<date>.<short-sha>` 语义，源码身份由冻结 commit
`a8c0d0ec8faad0e55e8be55bcb43df89da515d26` 唯一确定（该 commit 恰为最新一个
"补 exec bit" 提交，脚本可执行位齐全；打包后统一 `python3` 调用，不依赖可执行位）。

归档获取的坑（已写入 conandata.yml 注释）：

| 事实 | 说明 |
|---|---|
| 必须用 GitLab API 端点 | `https://gitlab.com/api/v4/projects/kicad%2Flibraries%2Fkicad-library-utils/repository/archive.tar.gz?sha=<full-sha>`；web 端 `/-/archive/` 形态会被 Cloudflare 拦截命令行下载（403） |
| 归档确定性 | 服务端按 commit 生成，同一 commit 多次下载 sha256 一致（两次独立下载复核均为 2966b04d…45e） |
| 根目录名 | `kicad-library-utils-<sha>-<sha>/`，conan `get()` 必须 `strip_root=True` |
| 内容形态 | 562 个条目纯 Python + 测试数据；无 `.c/.cpp/.h`、无 CMakeLists、非 pip 包（pyproject.toml 仅样式工具配置） |

## 2. 适配口径：无构建 + 整体保留源码树

上游没有 install 语义，入口脚本以相对路径引用公共模块
（`klc-check/check_symbol.py` 第 16–21 行）：

```python
common = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "common")
)
```

因此任何"把可执行脚本抽到 bin/"的做法都会破坏 import。配方语义：

- `build()` 显式 no-op（无编译器调用，交叉编译风险为零）；
- `package()` 把整棵源码树（含上游测试数据 `klc-check/test_symbol/`、
  `klc-check/test_footprint.pretty/`）原样复制到 `share/kicad-library-utils/`；
- `package_info()` 用 `resdirs=["share"]` + 各工具子目录 bindirs 表达
  "工具在包内、按树组织"的事实，消费者可通过 conanrun 环境拿到 PATH 注入。

## 3. 类型裁定：application + commands.json（R38）

本包是真实的命令行工具集合（KiCad 官方库仓库 CI 的门禁程序），不是数据包，
按 R38 诚实声明 `package_type = "application"` 并提供软件级 `commands.json`
（type=tool、binary=false）。CI 门禁 L0k 的三个判据（bindirs 非空 / bin 安装 /
application 类型）本配方命中"bindirs 非空"与"application"两条，commands.json
必须存在且通过校验（name 含包名、versions 含本版本）——与数据/资源型包用
`unknown` 规避门禁的 kicad-symbols 先例（E255/E305 模式）相反，这里门禁要求
是本包类型的正确表达。

## 4. 依赖闭包：只声明 stdlib 级核心路径

核心检查路径 `common/` + `klc-check/` 仅依赖 Python 标准库（argparse/multiprocessing/
dataclasses/glob 等），`colorama` 为可选（`common/print_color.py` 缺失时自动降级，
设备已装 0.4.6）。可选重依赖 bs4/click/requests/Pillow 等只被 `tools/`、
`symbol-generators/`、`html-diff/`、`scripts/` 子目录按需引用，不属于本包
Conan 依赖闭包（配方 requires 为空，R36 无涉）。上游测试体系为标准库
`unittest`（设备无 pytest，也不需要）。

## 5. 上游测试的真实运行

上游 Makefile 提供三个真实测试目标，test_package 按原样逐条执行
（`python3 -B` 关闭字节码写入，属包目录卫生口径：不在已安装包内遗留
`__pycache__`、保持包目录与构建修订一致；HMDFS 路径下字节码写入本身可行，
并非规避写入失败；multiprocessing 在真机可用）：

| 上游目标 | 命令 | 真机实测 |
|---|---|---|
| `test-klc-symbols` | `python3 klc-check/check_symbol.py --unittest klc-check/test_symbol/*.kicad_symdir` | exit 0，133 用例全 passed |
| `test-klc-footprints` | `python3 klc-check/check_footprint.py --unittest klc-check/test_footprint.pretty/*__*.kicad_mod` | exit 0，53 用例全 passed |
| `test-klc-footprints`（第二条） | `python3 klc-check/check_footprint.py -vv klc-check/test_footprint.pretty/SO-8_3.9x4.9mm_P1.27mm.kicad_mod` | exit 0，No errors |
| `test-symgen` | `python3 symbol-generators/from_csv_generator.py symbol-generators/BQ24004-example.csv` | exit 0，生成 BQ24004-example.kicad_sym（校验非空后移除恢复包目录原状） |

未纳入的 Makefile 目标及理由：

- `lint` / `style` / `spelling`：依赖 black/isort/flake8/codespell，属代码风格
  工具而非测试断言，设备未安装且与本包运行无关；
- `test-comparelibs-symbols`：comparelibs 自测试设计上接受退出码 2/3（"不在意
  是否 KLC 合规"），且 `--junit` 落盘写文件；为保证 test_package 全部零退出断言
  的严格性未纳入，其被测核心模块（rulebase/junit）已被符号/封装两套 unittest 覆盖。

勘误（Web Reviewer KLU-REV-001）：初版把 `test-symgen` 以"依赖 click"为由排除，
该理由失实——`from_csv_generator.py` 零 click 引用（click 只在被该目标不调用的
`symbol-generators/stm32/*.py` 里），上游 requirements.txt 也不含 click。
`test-symgen` 属上游 `make check` 组成目标，在本依赖闭包内零成本可运行，
已按上表纳入真实执行。

## 6. 遗留风险

- 上游滚动开发：同一 commit 冻结确定性无虞，但未来升级新 commit 时需重新复核
  测试用例数（133/53 会随上游变化）；
- OHOS 真机文件系统大小写不敏感：本包内部引用均大小写一致（实测通过），但
  消费者若在大小写不敏感卷上把本包与其他工具混用需注意；
- `bin` 名义上在 bindirs 中的脚本需 python3 解释器在 PATH（OHOS PC 标准环境
  已满足）。
