# DRAFT-ohos-configure-optional-python-hardfail — autotools configure 对可选 python 模块 AC_MSG_FAILURE 硬失败与软放行

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-06
> **Severity**: 🟡 medium | **Category**: autotools / configure / python / portability

## 相关既有条目（同族差异化定位）

本条目与既有 autotools 配置层条目共享 configure 阶段背景，但本条目是 **configure 对可选 python 模块硬失败（AC_MSG_FAILURE）**——非重复条目；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E007**（config.guess 无法识别 OHOS） | 正式收录 | configure 早期报 `unable to guess system type`，是平台三元组探测问题 | 非本题——那是 **build type 探测**，本条目是 **python 模块存在性检查**（AC_MSG_FAILURE）；触发点、修法（config.guess/sub patch vs configure 检查软放行）均不同 |
| **DRAFT-ohos-autotools-rpl-malloc**（speech-dispatcher） | 草稿 | 交叉编译下 AC_FUNC_MALLOC 缓存变量误判 | 非本题——那是 **编译探测值误判**（缓存变量覆盖），本条目是 **可选依赖硬失败**（软放行补丁）；问题层完全不同 |
| **E011**（config.status HMDFS 权限） | 正式收录 | config.status 生成 subs1.awk 权限问题 | 非本题——那是 **生成脚本执行位**，本条目是 **configure 检查逻辑** |

> 全库查证（2026-09-06）：`python3-rdflib` / `AC_MSG_FAILURE.*python` / `rdflib` 命中 0 条——无正面撞车；本条目为真增量。

## Scope（何时用）

用 autotools 构建、且 `configure.ac` 把**可选** python 模块依赖写成 `AC_MSG_FAILURE` 的库，在缺该模块的环境（CI 沙箱、干净镜像、无 pip 网络）构建时：

- configure 报 `failed. Please install the <module> package.` 直接终止；
- 但本体（C 库/引擎/daemon）编译**根本不需要**该模块（仅辅助脚本/文档/解析工具用）。

典型实例：zeitgeist/1.0.4（`python3-rdflib` 仅 ontologies 解析工具需要，本体 libzeitgeist + src 引擎不需要）。

## Symptom

```text
checking for python3-rdflib... configure: error: in `/build/zeitgeist-src':
configure: error: failed.  Please install the python3-rdflib package.
See `config.log' for more details
```

## Root Cause

1. 上游 `configure.ac` 把"可选"工具依赖写成硬检查（`AC_MSG_CHECKING` + `AC_MSG_FAILURE`），
   而不是条件编译/警告跳过——这是上游对可选依赖的过度约束；
2. 在缺该 python 模块的环境（CI 沙箱无 pip 安装、或镜像不含）configure 直接报错退出；
3. 本体（C 库）编译不依赖该模块——硬失败纯属构建环境约束，非代码缺陷。

## Recommended Solution

**主方案：patch configure（及 configure.ac 同步），把该检查改为非致命。**

保留检查输出（`no (optional; ...)` 警告）但不终止 configure。补丁单一职责、可复现，
本体构建无损。

```patch
# patches/0001-relax-rdflib-check.patch（节选）
 echo "import rdflib" | $PYTHON - 2>/dev/null
 if test $? -ne 0 ; then
-  as_fn_error $? "failed.  Please install the python3-rdflib package."
+  printf "%s\n" "no (optional; ontology parsing disabled)"
 else
   ... result: yes ...
 fi
```

**回退方案**：若 configure 的检查逻辑确实强依赖该模块，用 tool_requires/python 预装
模块——改动面大且 CI 沙箱装模块不可控，不推荐。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **zeitgeist/1.0.4** | 主验证（本 PR） | ✅ 未打补丁 configure 报 `failed. Please install the python3-rdflib package`；打 `0001-relax-rdflib-check.patch` 后 configure 通过，make 全量编译成功（libzeitgeist + src 引擎 + examples + doc） |

## 测试覆盖边界

- 软放行只影响 **configure 阶段**；rdflib 相关脚本（ontologies 解析）不参与本体构建，
  无行为差异；
- 声明通过率时：以 configure 通过 + make 全量成功 + make check 10/11（log-test 因
  设备缺 D-Bus machine-id 环境限制失败，非本条目问题面）为实证。
