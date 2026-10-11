# libcharon 5.0.0 适配笔记

## 基本信息

- 上游：https://github.com/Ultimaker/libCharon（tag 5.0.0，LGPL-3.0）
- 说明：3D 打印文件元数据/流库（UFP/G-code），Cura 生态组件。注意：与 strongSwan 的
  charon 同名但无关；Debian 源包 libcharon 5.0.0-5 与 FreeBSD net/libcharon 均指向本上游。
- 构建系统：custom（纯 Python 包；上游 CMakeLists 仅做 `install(DIRECTORY Charon ...)` 与注册 ctest）
- 源码包：`https://github.com/Ultimaker/libCharon/archive/refs/tags/5.0.0.tar.gz`
- sha256：`7b58b921c6fd78329badc83de4b9987c058d048b6a450313be23756415372fbf`（下载实测，151686 字节，顶层目录 `libCharon-5.0.0/`）
- 适配路径：路径 A（基础适配）——零源码修改，配方仅打包 + 真实运行测试
- 状态：built（待真机预检返回 evidence 后更新通过率数字）

## 编译步骤

配方 `conanfile.py`（`package_type = "python-require"`，仿 gym 0.26.2 / cloudpickle 3.1.2）：

1. `source()`：`get()` 官方 tag 包，`strip_root=True`。
2. `build()`：确认 `Charon/` 存在； fixtures 非空检查（`um3.gcode`、`um3.gcode.gz`、
   `hello.opc`、`empty.opc`）；`pip install --target <build>/pydeps pytest`
   （先 pin `pytest==8.3.4`，失败回退 unpinned；内部镜像源；`PYTHONNOUSERSITE=1`）；
   `pytest --collect-only` 交叉核对总数 == 37（审计值，不一致直接抛异常）；
   真实运行 `python -m pytest tests/ -q --no-header -p no:cacheprovider --tb=short`；
   解析 `-q` 汇总单行（唯一计数源）得 discovered/executed/passed/failed/skipped，
   输出 `HMBS_UPSTREAM_TEST_RESULT` 并落盘 `hmbs_upstream.json`。
3. `package()`：`Charon/` 整体复制到 `lib/python3.12/site-packages/Charon/`；LICENSE 进 `licenses/`。
4. `test_package`：`test_charon.py` 对包内 `Charon` 做 6 项真实 API 调用，
   逐项打印 `CHECK-OK:`；`test()` 用 `self.run()` 真实执行（L0d/R34，
   输出重定向到日志文件）并计数该行（唯一计数源）输出
   `HMBS_TEST_PACKAGE_RESULT`（discovered=6）。

## 上游测试审计（pytest 口径，python_def）

| 文件 | 测试函数数 | 说明 |
|------|-----------|------|
| tests/filetypes/TestGCodeFile.py | 12 | G-code 头解析异常分支（unittest 方法） |
| tests/filetypes/TestGCodeFormat.py | 2 | VirtualFile 读 .gcode/.gcode.gz（fixtures） |
| tests/filetypes/TestOpenPackagingConvention.py | 23（12 个 def 经 parametrize 展开） | OPC 读写/别名/元数据/rels：listPathsEmpty 1 + getWriteStream 5 + forbidOnRels 1 + cycleSetDataGetData 3 + aliases_replacement 2 + cycleStreamWriteRead 3 + cycleSetMetadataGetMetadata 3 + toByteArray 1 + toByteArrayStream 1 + addContentType 1 + addRelation 1 + getMetadataSize 1 |
| **合计** | **37** | `pytest.ini`: testpaths=tests, python_files=Test*.py；计数单位为 pytest 收集项（collect-only），每个 parametrize 实例单独计数 |

- `Charon/Client/test_glib.py`、`test_qt.py` 为小写手工脚本，不被 pytest 收集（0 用例）。
- 上游 ctest 仅 1 个包装项 `pytest-main`（调同一 pytest），故 PR 口径以 pytest 展开后 37 为准。
- 未修改任何上游测试；无新增鸿蒙特有测试之外的上游改动（新增仅 test_package 消费者用例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 初判可能为 strongSwan 子库 | libcharon 与 strongSwan charon 同名 | 核查 Debian/FreeBSD 源包指向，确认为 Ultimaker/libCharon 独立 Python 库 |
| 2 | Windows 检出上游 main 失败：`archives/g/gama/...patch??` 非法路径 | 该文件名尾含回车符，Windows 非法 | 稀疏检出排除该目录（仅本地措施，不进版本） |
| 3 | Windows 下 `archives/l/libXext` 与 `libxext` 大小写碰撞致 status 常显修改 | 上游同时存在新旧大小写目录 | 本地现象，不改动这两处；Linux 真机不受影响 |
| 4 | 本机无可用 Python（WindowsApps 存根） | 精简镜像 | 食谱与测试脚本的语法按上游同版本文件逐行核对；真实执行交由真机预检 |

## 依赖版本

- 运行时：无（Charon 仅用 stdlib：zipfile/json/xml/typing；PyQt5 仅 PNG 缩放分支，测试不覆盖）。
- 测试执行器：pytest（pip 私有安装，先 `pytest==8.3.4`，回退 unpinned）。

## 验证结果

- 本地：配方文件静态核对完成（API 签名逐一对照上游 5.0.0 源码）。
- 真机预检（待 HMBS 回传后填写）：上游 37 用例执行数/通过数、新增 6 用例通过数、
  两行 HMBS JSON 标记原文。
- 证伪安排：fixtures 非空检查 + collect-only 交叉核对已在配方内；test_package 数据
  全部 in-code 构造且断言非空（如 `len(raw) > 0`、`len(paths) > 0`）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | python-require 配方，上游 pytest 真跑 + 标记 |
| conandata.yml | 官方 tag URL + sha256 |
| manifest.yaml | 版本级 manifest（custom 构建） |
| test_package/test_charon.py | 6 项真实 API 消费者测试（14 断言） |
| test_package/conanfile.py | 运行测试并输出 test_package 标记 |
| test_package/MANIFEST.yml | 上下游测试声明（total 37，python_def） |

## 注意事项

- 本包为纯 Python 库，无 `commands.json`（无可执行产物，R38 不适用）。
- `Charon/Service`（DBus 服务）与 `service/*.service` 均不安装（PC 制品仅需文件库）。
- 如真机出现上游失败项，按类别（environment/ohos_feature/test_failure）逐项记 gaps，
  缺依赖必须补齐重测，不得记 missing_dependency 豁免。
