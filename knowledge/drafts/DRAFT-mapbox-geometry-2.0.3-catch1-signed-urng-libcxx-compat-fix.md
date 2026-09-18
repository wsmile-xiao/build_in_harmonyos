# DRAFT-mapbox-geometry-2.0.3-catch1-signed-urng-libcxx-compat-fix
> vendored Catch 1.x有符号URNG与新版libc++ uniform_int_distribution静态断言冲突的幂等兼容修复
## 问题特征（真实日志片段/标记）
- 真机build()编译上游测试失败：uniform_int_distribution.h:235 static_assert __libcpp_random_is_valid_urng<Catch::RandomNumberGenerator>失败，经shuffle.h:154、catch.hpp:7184/7202实例化
- 门禁标记为v2:compile:test_assertion_failed，真机门禁拦截，attemptId 15042记录原问题已消失且真机门禁全部通过后才判定resolved
- 仅影响上游测试编译阶段，配方产物形态为header-library，无shared硬错；日志中/tmp只读行为环境噪音，配方已有_writable_tmpdir处理，与本故障无关
## 根因
- Catch 1.9.6的RandomNumberGenerator声明typedef std::ptrdiff_t result_type为有符号类型
- 新版OHOS LLVM libc++强制要求URNG的result_type为无符号整数类型，std::shuffle内部的uniform_int_distribution<long>对其做__libcpp_random_is_valid_urng有效性静态断言
- 有符号URNG传入即触发编译期static_assert，属于工具链兼容模式问题，非测试逻辑错误、非autoconf只读tmp问题、非package_type形态问题
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 在archives/m/mapbox-geometry/2.0.3/conanfile.py导入replace_in_file工具
2. 在_run_upstream_tests中上游测试编译前，对vendored Catch 1.9.6头catch.hpp做幂等测试框架兼容修复：把RandomNumberGenerator::result_type由typedef std::ptrdiff_t result_type改为typedef unsigned int result_type
3. 保持幂等写法，已修复时不再重复改写；其余测试逻辑、断言与执行口径均不动，仅动测试框架头
4. 本地执行py_compile验证配方语法，保持工作树修改未提交，等待HMBS真机预检复跑验证；真机preflight应显示build()上游测试编译通过，原v2:compile:test_assertion_failed消失且门禁passed
## 禁止策略
- 禁止保留typedef std::ptrdiff_t result_type有符号URNG定义放行：新libc++ uniform_int_distribution静态断言必定拦截编译，导致真机build()失败退回修复循环
- 禁止为绕过断言而改动测试逻辑、删除shuffle相关测试或关闭上游测试执行口径
- 禁止将/tmp只读噪音误判为根因去改autoconf/configure逻辑，禁止将header-library误判为shared形态问题
## 与相近条目的边界（查重）
- 查重零命中，现有技能库无法解决该类编译期static_assert拦截问题，故具增量性
- 通用性边界：本条目针对Catch1.x有符号URNG与新libc++ URNG有效性检查冲突的工具链兼容模式，可跨库复用；不覆盖Catch2及以上、非URNG原因的uniform_int_distribution失败、非libc++断言的普通测试断言失败
- 与demo提升回归套件、autoconf tmp处理、package_type形态类条目无重叠，experienceDecisions已明确reject后两者
## 适用判断
- 适用：vendored Catch 1.x、错误签名命中__libcpp_random_is_valid_urng或uniform_int_distribution.h static_assert经shuffle.h与catch.hpp实例化、新版libc++工具链下编译上游测试的库
- 不适用：已使用无符号URNG或Catch2的库、无shuffle或uniform_int_distribution调用栈的测试编译失败、纯运行时测试断言失败
