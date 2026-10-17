# DRAFT-E5xx-ohos-buildhost-pygobject-gi-shim-pythonpath-bridge

## 现象

构建主机（OHOS 设备侧 conan 构建）上 meson configure 阶段失败于 python 模块
探测；直接探针：

```
$ /storage/Users/currentUser/usr/local/bin/python3 -c 'import gi'
Traceback (most recent call last):
  ...
ModuleNotFoundError: No module named 'gi'    # Python 3.12.9, EXIT=1
```

（探针必须用绝对路径：裸 shell 无 `python3`，裸名直接 exit 127。）

即使绕过 configure 探测，构建期生成器子进程运行时同样崩：

```
from gi.repository import GLib
ModuleNotFoundError: No module named 'gi'
```

## 根因

两层缺口、同一根因：

1. 上游 `meson.build` 用 `import('python').find_installation('python3',
   modules: ['gi'])` 在 configure 阶段硬探测 PyGObject——缺失即构建失败。
2. 探测通过后，构建期生成器（`build-aux/gen_locations_variant.py`）由 ninja
   拉起，运行时 `import gi.repository.GLib` 构造 `GLib.Variant`。

PyGObject 是 C 扩展 + 完整 GLib 绑定栈，OHOS 构建主机上不可补装。但生成器对
gi 的真实用量只有 **GVariant 值构造 + `get_data_as_bytes`**（byteswap 分支在
小端主机是死代码，上游注释自证），因此一个实现该子集的纯 python `gi` shim 即
语义等价。

## 修复

recipe 自含 shim，PYTHONPATH 一次注入同时覆盖两类子进程（关键：meson 探测
子进程与 ninja 生成器子进程都直接继承父进程环境）：

```python
exports_sources = "shim/gi/*.py"     # shim/gi/{__init__.py, repository.py}

def build(self):
    shim = os.path.join(self.source_folder, "shim")
    if not os.path.isdir(os.path.join(shim, "gi")):
        raise ConanException("bundled gi shim missing from source folder")
    env = os.environ
    env["PYTHONPATH"] = shim + os.pathsep + env.get("PYTHONPATH", "")
    ...
    meson = Meson(self)
    meson.configure()   # find_installation('python3', modules:['gi']) 经 shim 通过
    meson.build()       # ninja 拉起的生成器子进程同吃 PYTHONPATH
```

要点：

- 注入用 `os.environ` 直改，**不用 `buildenv_info`**（后者只向直接消费者传一跳，
  且写入时机在 generate() 之后）。
- shim 实现范围以**生成器源码审读圈定的 API 面为准**（本例：`GLib.Variant` 的
  构造/类型校验/序列化 + `Bytes`/`VariantType` 壳），不追求完整 PyGObject。
- build() 前置 shim 存在性守卫，缺失即 `ConanException`，不让缺口静默滑过。

## 验证

- 修复前：探针 `ModuleNotFoundError: No module named 'gi'`（Curator 现场实测 +
  Auditor 独立复现）。
- 修复后：`gwl-create2.log:87` `Program python3 (gi) found: YES ... modules: gi`；
  权威 CI run1 EXITCODE=0 全绿（meson test 1/1 + test_package 消费者级解析
  17/17 ALL PASS）。

## 适用范围与诚实边界

- **命中面**：凡构建主机无 PyGObject 且上游构建期需要 import gi 的包
  （GNOME/meson 数据模块、构建期代码生成器）。
- **方案条件（逐库核验，不得默认推广）**：仅当生成器只使用 GVariant 构造 +
  `get_data_as_bytes` 时 shim 可行；涉主循环（MainLoop/idle）、类型仓库
  （GType/信号注册）或其他 GLib 运行时服务时**不可行**。
- **fallback**（不可用时）：宿主侧预装 PyGObject（交叉构建机不可控，仅受控
  集群可考虑）；pre-generate 产物随源码携带（违背不污染上游原则，仅最后退路
  且须 PR 如实申报）。
- **forbid**：recipe 内 `pip install pygobject`（目标机/构建机双不可达）；
  改写上游 meson.build 去掉 `modules:['gi']` 或跳过生成器（放弃上游 oracle）。
- 环境注入的另一个独立坑（ninja 绝对路径钉扎）不在本条目展开，见
  DRAFT-E5xx-ohos-meson-detect-ninja-env-pin。
- 近邻条目：E243（生成器**测试**策略，非 gi 桥接）、E307（test_package 缺
  CMake 的编译器直编，仍属编译面）——均非同题，见 .kv similar_to。
