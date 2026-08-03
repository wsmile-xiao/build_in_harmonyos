# hickle 5.0.3 适配笔记

## 基本信息
- **软件**：hickle — HDF5 based version of pickle
- **版本**：5.0.3
- **上游**：https://github.com/telegraphic/hickle
- **许可证**：MIT
- **构建系统**：python（setuptools，纯 Python 包 py3-none-any）
- **适配日期**：2026-07-31

## 源码信息
- **来源**：PyPI sdist
- **URL**：https://files.pythonhosted.org/packages/b1/42/09a543153c1609b656f5c8e33210d6bdd1b7045c0d6e33bc96bb9afbb704/hickle-5.0.3.tar.gz
- **sha256**：`027e51ccad279d168123a244525e6c84bac0db64605b311b0bd349891be0c53e`
- **size**：117601 bytes

## 依赖分析

### 运行期依赖（PyPI requires_dist）
| 依赖 | 版本约束 | OHOS 可用性 | 处理方式 |
|------|---------|------------|---------|
| h5py | >=2.10.0 | 待部署（需 HDF5，已发布 archives/h/hdf5） | 非 Conan requires，由目标 Python 环境提供 |
| numpy | >=1.8,!=1.20 | 已可用（openblas notes 验证 numpy 2.5.1） | 非 Conan requires，由目标 Python 环境提供 |

### 依赖处理决策
h5py/numpy **未作为 Conan requires 声明**，原因：
1. 制品仓未发布 h5py/numpy 的 Conan 配方（archives 无对应 conanfile.py）
2. 声明 Conan requires 会导致 `conan create` 因找不到配方而失败（L0i/L0i-1 fallback 也无法 export 本地配方）
3. 这两个是 Python 运行期依赖，由目标 Python 环境 site-packages 提供，与 C/C++ 库的链接依赖模型不同

参考先例：docutils/python-gssapi 等 Python 包的运行期依赖同样由设备 Python 环境提供，不进 Conan 依赖图。

## 构建方式
**直接拷贝**：hickle 是纯 Python 包（无 C 扩展），`package()` 直接把源码包内的 `hickle/` 目录拷到 `lib/python3.12/site-packages/`。

不走 `pip install` 的原因：
- 避免 pip 对 setuptools / build isolation 的运行期依赖
- 避免 `--no-deps` 仍需解析 setup.py 的 install_requires（会尝试解析 h5py/numpy）
- 纯 .py 拷贝即等价于安装结果

## 测试策略

### test_package 两级验证
1. **包完整性（硬断言）**：
   - `hickle/__version__.py` 存在且 `__version__ == "5.0.3"`
   - `hickle/hickle.py`、`hickle/__init__.py` 存在
   - 移走产物即失败 → 过 L1e 破坏性反向验证（R34）
2. **功能往返（可选 best-effort）**：
   - h5py+numpy 可用时：`hickle.dump`/`load` 一个 dict 校验一致
   - 缺失可选依赖时：SKIP，不阻断 CI

### 上游测试
hickle 上游用 pytest（`hickle/tests/`），需 h5py/numpy/pandas/scipy/astropy 等科学计算栈，OHOS CI 无法完整运行。`upstream_test_in_build: false`，仅做 test_package 冒烟测试。

## CI 门禁符合性（build_and_test.sh L0-L5）
| 门禁 | 检查项 | 状态 |
|------|--------|------|
| L0a | test_package/ 目录存在 | ✅ |
| L0b | test_package/conanfile.py 存在 | ✅ |
| L0c | test_package/ 有测试源文件 (.py) | ✅ test.py |
| L0d | test_package/conanfile.py 有 test() + self.run() | ✅ |
| L0e | test_package/MANIFEST.yml 存在 | ✅ |
| L0f | conandata.yml patches 格式 | ✅ 无 patches |
| L0g | 禁止硬编码 remote | ✅ 无 conan -r= |
| L0h | self.run 无 ${CC}/${CFLAGS} | ✅ |
| L0i | 依赖发布检查 | ✅ 无 Conan requires |
| L0k | commands.json | ✅ 库类型，无需 |
| L0m | 目录结构 archives/h/hickle/5.0.3 | ✅ |
| L0n | 分支名含 hickle-5.0.3 | ✅ feat/hickle-5.0.3 |
| L1a | test_package 被 conan create 执行 | ✅ test_type=explicit |
| L1d | test() 非假运行 | ✅ python3 test.py |
| L1e | 破坏性反向验证 | ✅ 移走产物 test 失败 |
| L4 | 补丁安全扫描 | ✅ 无补丁 |
| L5 | 产物检查 | ✅ site-packages/hickle/ |

## 验证命令
```bash
conan create archives/h/hickle/5.0.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 已知限制
1. **运行期依赖未 Conan 化**：h5py/numpy 不在 Conan 依赖图，消费者须确保目标 Python 环境 site-packages 已安装。完整功能（import hickle）需 h5py 可用。
2. **python3.12 路径硬编码**：site-packages 路径含 `python3.12`，与 OHOS 标准 Python 3.12 一致（SKILL.md §0.0）。
3. **上游测试需科学计算栈**：上游 pytest 需 h5py/numpy/scipy/astropy/pandas/dill 完整栈。OHOS 目标环境实测（2026-08-01）：初始 95/102，应用 5 个 portability 补丁后 102/102 全部通过（详见 manifest.yaml upstream_test_run）。

## 交付物
- `lib/python3.12/site-packages/hickle/` — 纯 Python 包目录
- usr_local deployer 铺到 `~/usr/local/lib/python3.12/site-packages/hickle/` 后系统 python3 可 import
