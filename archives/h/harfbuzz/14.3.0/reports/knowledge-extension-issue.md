**【申请人账号】**2301_80739235

**【队伍名称】**天天开心

**【申请日期】**2026/08/19

**【库名称】**harfbuzz

**【版本】**14.3.0

**【contrib 任务】**3712，状态为已领取，活动为开源鸿蒙PC专项积分赛-依赖，任务分支为 feat/harfbuzz-14.3.0。

**【关联跟踪】**Issue #1866 仅作关联与追踪，不是所有权权威，也不否决 contrib 精确任务行确认的当前账号所有权。

## 申请原因

HarfBuzz 14.3.0 是官方当前稳定修订，也是 Pango 1.58.2 所需的直接共享库依赖。本任务将完成真实 OHOS/arm64 shared 包、完整上游 Meson 测试、消费者 API 验证及合并后发布回读。适配中发现 Conan graph info 能解析完整 RREV/PID/PREV 但 package_folder 仍可为空，必须与同一隔离 home 的 install 结果按完整包身份连接后再做产物验证，因此按路径 A+B 申请。

## 知识库查重情况

已按最新 main 对 knowledge/graph、knowledge/drafts、knowledge/doc、knowledge/operations 四个范围执行关键词与语义等价查重。已有条目覆盖一般 package_folder 使用、共享库物化和 Conan 身份读取，但未覆盖 graph info 与 install 对 package_folder 物化时点不同、且必须按 RREV/PID/PREV 精确连接的验证边界。候选知识草稿为 E2153-draft-2301-conan-package-folder-materialization。

## 可复用说明

该规则可复用于所有以 fresh isolated Conan home 和 --build=never 验证远端二进制的配方：graph info 负责依赖图、无效节点和远端身份，install 负责二进制检索与 package_folder 物化；二者必须保持 profile、home、RREV、PID、PREV 完全一致，不能用空 graph package_folder 误判包未发布。

## 所有权与安全边界

contrib 精确任务行是领取与所有权权威；Issue 仅用于分类和追踪。该所有权不替代当前 main、全状态 PR 和语义等价查重，也不代表 W0-W5、Review、CI、合并或制品仓发布已经通过。合并前禁止执行 /release，发布完成必须由全新隔离 Conan home 的 download、graph info 和 install --build=never 回读证明。
