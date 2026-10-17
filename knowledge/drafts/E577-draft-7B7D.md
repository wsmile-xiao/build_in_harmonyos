# E577 — test_package 访问传递依赖产物时 package_folder 为 None（Conan 判 Skipped binaries）

## 错误特征

`conan create` 在被测包构建成功、进入 test_package 阶段后立即失败，日志形如：

```
======== Launching test_package ========
======== Computing dependency graph ========
Requirements
    cdb/20251021#... - Cache
    dbskkd-cdb/3.00#... - Cache
Skipped binaries
    cdb/20251021
======== Testing the package: Executing test ========
dbskkd-cdb/3.00 (test package): Running test()
ERROR: dbskkd-cdb/3.00 (test package): Error in test() method, line 45
	cdb_bin_dir = os.path.join(self.dependencies["cdb"].package_folder, "bin")
	TypeError: expected str, bytes or os.PathLike object, not NoneType
```

关键识别点是 **`Skipped binaries` 与被测包同现**：Conan 明确表示该传递依赖的 binary 本轮未被实例化，
因此配方侧 `Dependency.package_folder` 是 `None`，`os.path.join(..., None, ...)` 抛 `TypeError`。
报错行号指向 test() 里那一行，错误类型是纯 Python 的 `TypeError`，容易误判成配方拼路径写错。

## 触发条件

- 构建系统 / 工具：Conan 2.x（本仓库 2.29.1 实测），与上游构建系统无关
- 阶段：testing（`conan create` 的 test_package 执行阶段）
- 配方形态（三个条件同时满足）：
  1. 被测包是 `package_type = "application"` 或静态链接了某个依赖（二进制里不留下运行时依赖）；
  2. test_package 的 `requirements()` 只声明 `self.requires(self.tested_reference_str)`；
  3. test() 需要该**传递**依赖提供的产物——可执行工具、数据文件、CLI：
     `self.dependencies["<dep>"].package_folder` / `.cpp_info.bindirs`。
- 反例（不触发）：test_package 自行链接该依赖（`CMake`/`Meson` 等 helper 会把它算作被消费的依赖），
  或该依赖是被测包动态链接的运行时依赖。

## 根因分析

Conan 计算 test_package 的依赖图时按「谁被实际消费」裁剪 binary 实例化。被测包把依赖静态链接进
自己的产物、test_package 又只是执行被测包的二进制时，这条传递依赖在测试图里没有被任何构建目标
消费，Conan 于是打印 `Skipped binaries <pkg>/<ver>`、不下载/不实例化该 binary，
`Dependency.package_folder` 保持 `None`。

这与「test_package 需要传递依赖的**头文件**必须显式 `requires`」（CMakeDeps 不为传递依赖填充
`*_INCLUDE_DIRS`）是同一族的两个不同触发面：前者表现为 **`package_folder` 为 None**，
后者表现为 **include 目录为空**。两者都不写进配方就在运行时才暴露。

## 解决方案

### 推荐方案

在 test_package 的 `requirements()` 里显式声明该依赖，版本必须与被测配方声明的完全一致：

```python
def requirements(self):
    self.requires(self.tested_reference_str)
    # test 需要 cdb 包的 cdbmake/cdbtest，必须显式声明，否则 Conan 打印
    # Skipped binaries 且 package_folder 为 None
    self.requires("cdb/20251021")
```

随后用绝对路径定位工具，不从 PATH 取（同时满足 CI L1e 破坏性反向验证：删掉被测包产物后测试必须失败）：

```python
cdb_bin_dir = os.path.join(self.dependencies["cdb"].package_folder, "bin")
```

### 回退方案

若该依赖根本不在被测包的依赖图中（纯测试侧工具），改用 `build_requirements()` +
`self.tool_requires("<tool>/<ver>")`，并在 test() 中使用 `env="conanbuild"` 的 VirtualBuildEnv。
不要手工拼 `os.environ["PATH"]`：与 VirtualRunEnv 生成的环境脚本冲突（仓库内 nng 草稿已记录同一结论）。

### 禁止做法

- ❌ 把 `package_folder` 为 `None` 当成「路径写错」，改成从 PATH 调用工具：依赖其实没被实例化，
  测试会变成对构建机环境的依赖，换 worker/换机器即失败，并且掩盖真实的依赖缺失。
- ❌ 在 test() 里用 `try/except TypeError` 或 `or ""` 吞掉 `None`：空路径会让后续用例静默跳过。

## 验证

```bash
# 复现（requirements() 只写 tested_reference_str 的版本）
conan create archives/d/dbskkd-cdb/3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build='dbskkd-cdb/*'
# → Skipped binaries cdb/20251021 + TypeError: expected str, bytes or os.PathLike object, not NoneType

# 修复后（requirements() 显式 requires("cdb/20251021")）同一条命令：
# → test_package summary: TOTAL=31 PASS=31 FAIL=0
```

实测记录（dbskkd-cdb 3.00，设备 OHOS aarch64，Conan 2.29.1）：
修复前 test() 第 45 行抛 TypeError；
在 test_package 的 requirements() 增加与被测配方同版本的 `self.requires("cdb/20251021")` 后，
同一条 `conan create` 打印 `cdb/20251021: Already installed! (1 of 2)` 并跑完全部 31 个用例
（该包 26 个消费者协议/夹具用例 + 5 个鸿蒙特有平台检查）。

## 与既有条目的差异（反证）

- `python3 scripts/ohc-run.py engine --file <该 create 日志> --trace` 的命中为 E472（SDL test_package
  需 ELF 签名 + dummy 驱动）与 E225/E428/E298/E529，全部 `phaseB=0`，语义与「依赖 binary 未被实例化」
  无关；真正未命中的 token（`Skipped binaries`、`package_folder ... None`）在索引中没有对应条目。
- `grep -rn "Skipped binaries" knowledge/` 仅命中 `DRAFT-nng-1.10.1-*.kv`，
  而该草稿讲的是**被测包自身**的 CLI 定位（`self.dependencies["<pkg>"].package_folder`），
  不涉及传递依赖被 Conan 裁剪这条路径；复现命令：
  `grep -rn "Skipped binaries" knowledge/ && grep -n "package_folder" knowledge/DRAFT-nng-1.10.1-*.kv`。

## 关联条目

- 同族（头文件面）：test_package 需传递依赖头文件时须显式 requires（CMakeDeps 不填充 `*_INCLUDE_DIRS`，见 workflow 第 5.3 节）
- 相似定位手法：`knowledge/drafts/DRAFT-nng-1.10.1-cmake-unknown-platform-conan-cli-test.kv`
