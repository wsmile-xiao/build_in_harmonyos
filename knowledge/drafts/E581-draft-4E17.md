# E581 — Python 包配方需对齐平台既有科学计算栈的依赖版本上限（numpy<2.3 约束）

## 错误特征

封装 Python 科学计算类库时，依赖安装阶段解析失败或运行时 ABI/API 报错：

```
ERROR: Cannot install yt==4.4.2 and scipy==1.14.1 because these package versions have conflicting dependencies.
The conflict is caused by:
    The user requested numpy (>=2.3)
    scipy 1.14.1 depends on numpy<2.3 and >=1.23.5
```

或运行时：

```
AttributeError: module 'numpy' has no attribute 'float_'   # numpy 2.x API 变更
ValueError: numpy.dtype size changed, may indicate binary incompatibility
```

## 触发条件

- 构建系统: Python / pip
- 阶段: installation（依赖解析/安装）或 runtime（二进制不兼容）

## 根因分析

平台既有的 Python 科学计算栈（如 scipy 1.14.x）对 numpy 有**上界约束**（`numpy<2.3`）。
配方若让 pip 自由解析顶层依赖，会拉入 numpy ≥2.3：

1. 与平台预装/预编译 wheel 的约束**直接冲突** → `ResolutionImpossible`；
2. 即便安装成功，numpy 2.x 与按 numpy 1.x/2.2 ABI 编译的扩展也会出现
   `numpy.dtype size changed` 之类二进制不兼容错误。

pip 在缺少统一约束文件时不会自动回退到兼容版本——**必须显式钉住上限**。

## 解决方案

### 推荐方案

1. 配方内显式传递版本约束，**先装被约束的下游包**（如 numpy），再装上层依赖：

```bash
pip install --no-cache-dir 'numpy<2.3'
pip install --no-cache-dir -r requirements.txt
```

2. 把**实测通过**的版本组合写入 `conandata.yml` / `notes.md` 作为事实源
   （例：numpy 2.2.6 + scipy 1.14.1 + matplotlib 3.x）。
3. `test_package` 中导入关键依赖并断言版本满足约束，把"能装"升级为"能跑"：

```python
import numpy
from packaging.version import Version
assert Version(numpy.__version__) < Version("2.3"), numpy.__version__
```

### 禁止做法

- ❌ **依赖 `--no-deps` 跳过解析**：装得上但运行时缺模块，问题后移更难查。
- ❌ **盲目升级平台既有包**（如把 scipy 换新版以适配 numpy 2.3）：污染平台运行时，
  可能影响其它已发布包。
- ❌ **不记录实测版本组合**：下次封装同栈软件时重新踩一遍同样的坑。

## 验证

```bash
python3 -c "import numpy,scipy; from packaging.version import Version; assert Version(numpy.__version__)<Version('2.3'), numpy.__version__; print(numpy.__version__, scipy.__version__)"
# 2.2.6 1.14.1
```

## 关联条目

- 相关: E580（扩展后缀归一化）、E512（Python 依赖与 CI 环境）、E319（Python 网络与打包）
