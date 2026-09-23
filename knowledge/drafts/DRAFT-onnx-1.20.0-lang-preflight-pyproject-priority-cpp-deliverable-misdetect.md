# DRAFT-onnx-1.20.0-lang-preflight-pyproject-priority-cpp-deliverable-misdetect

> Contributor: staralsnow | Status: Draft | Updated: 2026-09-16
> Source: onnx 1.20.0 适配（ohpcd task 9169，lang=cpp，lang-preflight 阶段）
> 领域：语言预检（R47 / scripts/ohc/lang_detect.py）/ 绑定型双语言仓库判定 / 构建系统识别

## 一、使用说明（什么时候用这条）

任务标记为 cpp（或 c），但 lang-preflight 返回 detected_language=python、把任务写成
env_unsupported；而**上游同时提供完整的 Python 包和可独立安装的 CMake C++ 库**时，用本条目复核
适配交付物到底是什么语言，并把证据交平台。**最终语言以平台检查结论为准（官方口径：以检查为主），
不得自行覆盖。**

**禁止**：不按 R47（冻结协议）自行覆盖检测结果硬做 cpp 适配；也不要把真正以 Python 为主体的库
（没有 C/C++ 安装目标）强行算成 cpp。

## 二、适用范围

**适用**（命中以下全部或多数）：
- 顶层同时存在 pyproject.toml/setup.py 与 CMakeLists.txt；
- CMakeLists.txt 有 project(... LANGUAGES CXX)，且 install(TARGETS <lib>) 导出可被
  find_package(<Lib> CONFIG) 消费的 C++ 目标；
- Python 绑定是 opt-in 开关且**默认关**（如 ONNX_BUILD_PYTHON=OFF）；
- 源码统计里 .py 占比高（含大量 Python 测试用例生成器/绑定胶水），.cc 数量少但构成对外 API。

**不适用**：
- 纯 Python 包（无 C/C++ 安装目标）→ python 判定正确，应迁移；
- 真正的混合库（C/C++ 与 Python 均为交付主体、无明确主交付物）→ 应如实上报 mixed。

## 三、输入 / 输出定义

**输入**
- ohc-run.py lang-preflight <软件> <版本> --src <源码目录> 的输出（JSON：expected /
  detected_language / language_evidence）；
- 上游 CMakeLists.txt（顶层 project() / option(...BUILD_PYTHON...) / install(TARGETS ...)）；
- 源码统计（.py / .cc / .h 数量，可按目录排除 test 后复算）。

**输出（判定结论三选一）**
1. 交付物为 C++ 库 → 报平台并附证据，由平台按检查结论定语言（维持 python 则迁移）；
2. python 成立（纯 Python 交付物）→ 接受 env_unsupported，交平台迁移；
3. mixed（双主体）→ 如实上报 mixed + 证据。

## 四、示例（onnx 1.20.0 实证）

**实测输入/输出**

```text
$ python3 scripts/ohc-run.py lang-preflight onnx 1.20.0 --src <src>
{"expected": "cpp", "detected_language": "python",
 "language_evidence": {
   "build_system": "setuptools",
   "manifest": "pyproject.toml 存在（python 打包 manifest）",
   "source_stats": "源文件 595 个（python:525, cpp:69, bash:3, nodejs:1），主体占比 88%"}}
→ EXIT=2，已自动写 env_unsupported
```

**交付物证据（说明这是绑定型双语言库、交付物是 C++ 库）**

| 证据 | 位置 | 原文 |
|---|---|---|
| C++ 项目声明 | CMakeLists.txt:4 | project(onnx LANGUAGES CXX) |
| 安装 C++ 目标 | CMakeLists.txt:584 | install(TARGETS onnx onnx_proto EXPORT ONNXTargets ...) |
| Python 绑定可选且默认关 | CMakeLists.txt:43 | option(ONNX_BUILD_PYTHON "Build Python binaries" OFF) |
| 消费者示例 | onnx/test/cmake/CMakeLists.txt | find_package(ONNX REQUIRED CONFIG) + protobuf::libprotobuf |

**检测器为什么会判 python（根因行号）**

| 位置 | 逻辑 | 后果 |
|---|---|---|
| lang_detect.py:107-110 | pyproject.toml/setup.py/setup.cfg → python/setuptools，用**全文件集合** names | 根级 pyproject.toml 压过 CMake |
| lang_detect.py:124-128 | CMakeLists 只取**顶层** tops，且排在 python 检查**之后** | c/cpp 判定优先级更低 |
| lang_detect.py:245-255 | 绑定标记 = pybind11/boost_python/Python_Additions/find_package(Python | **不含 nanobind**（onnx 1.20 用 nanobind） |
| lang_detect.py:190-194 | 绑定覆盖要求 dominant==cpp and share>=0.70 | onnx 主体 python 88% → 覆盖永不触发 |

**补充统计（排除 test 目录仍然 python 占多数）**：.py 约为 .cc 的 5 倍（onnx/backend/test/case/node
另有 190 个测试用例生成器 .py）。因此本条目**不主张** onnx 是纯 C++ 库；它主张的是：
**判定口径应以 Conan 适配交付物（安装目标）语言为准**，而当前工具只看打包 manifest + 全量文件占比。

**建议命令（复核用）**

```bash
grep -n "project(.*LANGUAGES CXX" CMakeLists.txt
grep -nE "option(BUILD_PYTHON.*OFF" CMakeLists.txt
grep -n "install(TARGETS" CMakeLists.txt
# 排除 test 后的语言占比
python3 - <<'PY'
import os, collections
c = collections.Counter()
for r, _, fs in os.walk('.'):
    for f in fs:
        e = os.path.splitext(f)[1].lower()
        if e in ('.py', '.cc', '.cpp') and 'test' not in r.lower():
            c[e] += 1
print(dict(c))
PY
```

## 五、查重差异

| 已有草稿 | 其根因 | 与本条的差异 |
|---|---|---|
| DRAFT-debugbreak-1.0-langpreflight-gnumakefile-misdetect | GNUmakefile 未识别 + 辅助 gdb .py 计入主体 → mixed | 辅助脚本把占比拉到阈值下；本条是 **C++ 库 + 完整 Python 包/绑定**，主体确实是 python |
| DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect | 测试目录辅助 Cargo.toml 抢在顶层 CMake 前 → mixed | 非顶层 manifest 抢占；本条是**根级** pyproject.toml 优先于 CMake，且绑定标记缺 nanobind |
| DRAFT-glad-2.0.8-generator-tool-c-deliverable | 官方仓库是 Python 生成器，产物是 C loader | 交付物由生成器产出；本条交付物是**上游 CMake 直接安装的 C++ 库**，Python 绑定是可选开关 |

结论：属于绑定型双语言仓库的交付物语言判定新子类，未与上述三条重复。

## 六、验证证据

- logs/011-lang-preflight.log（lang-preflight 原始 stdout，EXIT=2）
- $HOME/ohpcd-ai-worker-result.json：status=env_unsupported、detected_language=python（R47 协议终态）
- onnx 源码：CMakeLists.txt:4,43,584；onnx/test/cmake/CMakeLists.txt
- 平台任务：ohpcd task **9169** onnx 1.20.0 lang=cpp（另有 task 7291 onnx 1.22.0 lang=cpp，同一坑）
- **官方裁定（2026-09-16）：「onnx 算 C 库」** → 本条的 detected=python 为官方确认的误判，本库按 C/C++ 适配；条目价值在于记录该类判定缺口与证据模板

## 七、备注

本条目记录的是**协议边界与检测器规则缺口**（R47 冻结，agent 无权覆盖），不是绕过预检的方法。
若平台确认 onnx 属 cpp 任务，建议同步修 lang_detect.py：① _detect_binding 增加 nanobind；
② 绑定类包按 install(TARGETS) 的安装目标语言判定，而非全量文件占比；③ python manifest 检查
改用顶层 tops，与 CMake/meson 检查对称。
