# vecmath 1.5.2 适配笔记

## 编译环境
- 构建系统：Custom（BiSheng JDK `javac` + `jar`）
- 目标平台：HarmonyOS PC / arm64（ci/conan/profiles/ohos-aarch64）
- 状态：built（待真机预检通过后由 HMBS 统一提交推送）

## 库说明
vecmath 1.5.2 = Java3D 的 `javax.vecmath`，纯 Java 向量/矩阵数学库（Vector2/3/4、Tuple*、Matrix3f/d、Matrix4f/d、Quat4f/d、GMatrix/GVector、AxisAngle4 等）。版本号 1.5.2 精确对应 Maven Central 的 `javax.vecmath:vecmath:1.5.2`（Java3D vecmath 项目，GPLv2 + Classpath exception）。

## 上游源码定位
1.5.2 这个精确版本在 GitHub 的维护 fork（hharrison/vecmath，标签从 1.6.0-pre 起）没有 1.5.2 标签；官方 java.net SVN 已停服。因此该**精确版本唯一官方源码发行**是 Maven Central 的 `vecmath-1.5.2-sources.jar`（org 内主 jar 的同源源码归档），采用它作为 request 的 source（R39 官方源）。

## 编译步骤
1. `get()` 下载 `vecmath-1.5.2-sources.jar`（sha256 校验，Maven Central 该 artifact 真实哈希 `7bea4e97...`）。
   - jar 无单根目录（文件直接位于 `javax/vecmath/` 下），故 **strip_root=False**；Conan 按 zip 魔数识别并解包。
2. `_ensure_java()`：优先复用 `JAVA_HOME` / `~/bishengjdk17` / PATH 中的 JDK；缺失时从 conandata `build_tools.bisheng_jdk` 下载固定 BiSheng JDK 17.0.13（gitcode cmd-pkgs，与 servlet-api/4.0.1 同款）。
3. `javac -source 8 -target 8 -encoding UTF-8 -d classes @sources.list` 编译全部 51 个 `.java`。
4. 复制 `*.properties`（ExceptionStrings.properties）资源到 classes。
5. `jar cf vecmath-1.5.2.jar -C classes .` 产出 JAR，packaging 到 `libexec/`。

## 上游测试
- 审计结论：vecmath 1.5.2 发行版（Maven Central sources jar）仅含源码与资源，**无任何测试代码**（无 test-classes、无测试源、无打包构建脚本）。已在 `test_package/MANIFEST.yml` 写 `upstream_tests_exist: false` + `upstream_test_audit` 逐项审计。
- HMBS 机器门禁：`HMBS_UPSTREAM_TEST_RESULT(status=no_tests, discovered=0, executed=0)` 在 `test_package/test()` 输出（覆盖 cache-hit）。

## test_package
- `TestVecmath.java`：调用 Vector3f（length/normalize/dot/cross）、Tuple3f（get/setX/get(float[])）、Matrix4f（setIdentity/determinant）、Matrix3f（mul/determinant）、Quat4f（conjugate 共轭/双重共轭）共 **16 个数值断言**（R34 实质性验证）。
  - ⚠️ 踩坑：`Quat4f.norm()` 在 1.5.2 **不存在**（从 1.6 才有），改用 `conjugate()`（真实四元数操作）验证。
  - ⚠️ 踩坑（真机失败修复）：`Quat4f(float x,y,z,w)` 构造函数会**自动归一化**（除以模长，Quat4f 恒为单位四元数）。此前用 `new Quat4f(1,2,3,4)` 期望 x=1，实际被静默重标定为 (1,2,3,4)/√30，导致 conjugate 后 x≈-0.1826 而非 -1.0，共轭断言失败（15/16）。改用已归一化的 `(0.5,0.5,0.5,0.5)`（模长正好 1，归一化幂等），共轭后 x/y/z=-0.5、w=0.5，断言精确可验证。
- `test.sh`：解析 JDK → javac 编译 → java 运行 → 从输出 `RESULT CHECKS: passed=N` 行解析真实通过数 → 据实落 `HMBS_TEST_PACKAGE_RESULT(discovered=16, passedCount=N)`。
- `conanfile.py`（test_package）：要求被测包，定位 `libexec/vecmath-1.5.2.jar`，确保 JDK，跑 test.sh，再冗余复发 `HMBS_UPSTREAM_TEST_RESULT(no_tests)`。

## 依赖版本
- BiSheng JDK 17.0.13（构建与测试工具，conandata 固定下载）
- 无 Conan 运行时依赖

## 源码修改
无补丁（纯 Java，跨平台字节码，无需 OHOS 平台适配）。

## 验证命令（真机，由 HMBS 预检执行）
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
期望输出：
- `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"discovered":16,"passedCount":16}`
- `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...}`

## 交付物
| 文件 | 说明 |
|------|------|
| `libexec/vecmath-1.5.2.jar` | javax.vecmath 1.5.2 编译产物（51 个类） |

---

**适配完成**：2026-09-18
**最终状态**：built（待真机门禁通过）
