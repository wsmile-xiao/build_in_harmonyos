# E2176 — 上游构建系统的 FIND_PACKAGE 探测可能是残余死逻辑，声明 Conan 依赖前先 grep 实际 include

## 错误特征
```
CMake 输出 "Boost not found, using local: <源码>/src/ext"（或任一
FIND_PACKAGE 未命中回退信息），但构建/测试全部通过、产物无该依赖符号；
或反向：配置阶段强制要求某依赖，源码却 grep 不到一行 include。
```

## 触发条件
- 构建系统: cmake（含历史遗留探测宏的老工程，如 CLucene 2.3.3.4 的
  CLuceneBoost.cmake）；autotools 的 AC_CHECK_* 同理
- 阶段: configuration / 依赖声明（conanfile requirements()）编写期

## 根因分析
上游构建系统对依赖的探测逻辑可能滞后于源码演进：探测命中失败时
回退到源码内捆绑副本（如 clucene 的 src/ext/boost），而随着版本迭代
源码已不再 include 该依赖——探测成了死逻辑。若照搬构建系统探测
直接写 `self.requires("boost/1.84")`，会拖入巨型依赖链、放大版本
冲突面并拉长 CI 构建，且无任何功能收益。判定依据必须来自源码的
真实调用面，而非构建脚本的存在性。

## 解决方案

### 推荐方案
在声明依赖前对源码做 include 审计：
```bash
# 例：核实 boost 是否为真实依赖（排除捆绑副本目录）
grep -rn '#include.*<boost/' src/ --include='*.cpp' --include='*.h' | grep -v '/ext/'
```
- 零命中 → 不声明依赖；构建系统探测命中失败仅是回退提示，不是错误
- 有命中且为公共 API 依赖 → 声明精确 `name/version` 并走 W0 实证
- 若探测逻辑本身有 bug（如 CLucene 的 `ELSEIF(ZLIB_FOUND)` 笔误
  导致捆绑回退死代码），以「注入正确路径变量」代替改上游构建脚本

### 禁止做法
- ❌ 看到 FIND_PACKAGE/AC_CHECK 就写 requires()，未做 include 审计
- ❌ 用捆绑副本路径（src/ext 等）充当依赖 include 目录（污染包接口）

## 验证
```bash
# 产物应无被排除依赖的符号（例：boost）
nm -D --defined-only libclucene-*.so | grep -c boost   # 预期 0
grep -rn 'include.*<boost/' src/ --include='*.cpp' | grep -v /ext/ | wc -l  # 预期 0
```

## 关联条目
- 相关: E187（CMake 4 政策参数；同一适配中"构建系统遗留逻辑"的
  另一类处理）
