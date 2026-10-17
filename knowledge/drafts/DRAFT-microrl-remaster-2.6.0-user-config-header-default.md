# DRAFT-microrl-remaster-2.6.0-user-config-header-default

> Path B 知识库扩展草稿（由 microrl-remaster 2.6.0 R01 test_package 消费者编译失败产生，
> 与同名 `.kv` 配对，逐字段一致）。
> 仅为本地知识草稿，不代表任何 PR/commit/push 已成功。

## topic

嵌入式风格 C 库的公共头默认无条件 `#include "microrl_user_config.h"`（用户可配置头，
生成式配置模式）时，Conan 配方打包必须把上游模板头复制为默认空配置头
（`include/<lib>/<user_config>.h`），否则下游消费者（test_package/业务组件）任何
`#include <microrl/microrl.h>` 都会在预处理期 fatal error，导致 conan create 失败。

## error_signature

```
In file included from .../test.c:13:
In file included from .../p/include/microrl/microrl.h:34:
.../p/include/microrl/microrl_config.h:37:10: fatal error: 'microrl_user_config.h' file not found
#include "microrl_user_config.h"
1 error generated.
```

## root_cause

microrl_config.h（公共头链 microrl.h → microrl_config.h）在未定义
`MICRORL_IGNORE_USER_CONFIGS` 时默认 `#include "microrl_user_config.h"` —— 该头是
应用方提供的配置（类 lwIP `lwipopts.h` 模式）。配方 package() 若只打包
microrl.h/microrl_config.h 而不提供 microrl_user_config.h，下游消费者在预处理期即失败；
错误出现在 test_package 构建阶段（库本体编译已成功），表现为 conan create 整体失败。
上游源码树自带 `microrl_user_config_template.h`（空配置模板），rename 即得全默认配置头。

## durable_solution

1. 定位：`grep '#include .*user_config' 公共头`，确认无条件包含（非 `#ifdef` 守卫）。
2. 打包：package() 将上游 `microrl_user_config_template.h` 复制为
   `include/microrl/microrl_user_config.h`（空配置=全默认），保留模板头供下游定制。
3. 复验：conan create 全量重跑，test_package 消费者编译+运行通过。
4. 边界：编译期 -DMICRORL_IGNORE_USER_CONFIGS 只解决库本体编译，不代替对外默认配置头。

## impact

- 修复前：microrl-remaster 2.6.0 test_package 消费者编译失败（2/2 无法构建）。
- 修复后：conan create 内 test_package 2/2（test_microrl_remaster + test_microrl_remaster_ohos）PASS，
  `.ci-result.json` exit_code=0。
- 跨库复用：所有「公共头默认包含用户配置头」的嵌入式/配置化 C 库 Conan 打包。

## boundaries / counterexamples

- 反例：头文件用 `#ifndef FOO_USER_CONFIG` + 内置默认值而非无条件包含时，无需此处理。
- E309（generated config header install）是本模式的邻近条目但场景不同：E309 处理构建期
  configure_file 生成头，本条目处理源码树既有模板复制为默认配置头（无条件包含）。

## verification

```
conan create archives/m/microrl-remaster/2.6.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# -> G2 PASS；test_package: 100% tests passed, 0 tests failed out of 2
```

## relation

- similar_to: E309（config header 打包，场景不同：生成头 vs 模板默认头）
- caused_by: 无（独立模式）
- prerequisite_of: 无
- conflicts_with: 无