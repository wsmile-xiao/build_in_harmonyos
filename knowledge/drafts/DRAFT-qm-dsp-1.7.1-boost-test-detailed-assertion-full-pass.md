# DRAFT-qm-dsp-1.7.1-boost-test-detailed-assertion-full-pass
> Boost.Test以--report_level=detailed运行时以断言行满通过替代短尾标判定

## 问题特征（真实日志片段/标记）
- rpath修复生效后6个上游测试二进制全部exit=0、Running计数与审计一致，但harness仍报0/64失败：
- `qm-dsp/1.7.1: ERROR: [upstream-test] test-mathutilities: FAIL (missing-No-errors-detected)`
- `qm-dsp/1.7.1: ERROR: [upstream-test] test-window: FAIL (missing-No-errors-detected)`
- `qm-dsp/1.7.1: ERROR: [upstream-test] test-fft: FAIL (missing-No-errors-detected)`
- `qm-dsp/1.7.1: ERROR: [upstream-test] test-pvoc: FAIL (missing-No-errors-detected)`
- `qm-dsp/1.7.1: ERROR: [upstream-test] test-resampler: FAIL (missing-No-errors-detected)`
- `qm-dsp/1.7.1: ERROR: [upstream-test] test-medianfilter: FAIL (missing-No-errors-detected)`
- 真机证据定性为`exit=0 reported==expected但ERROR missing-No-errors-detected`，框架实际输出形态为`8 assertions out of 8 passed`类逐用例行。
- 结构化方法记录：`HMBS_REPAIR_METHOD={"title":"Boost.Test detailed报告断言行判定替代短尾标检查"}`。

## 根因
- `--report_level=detailed`下Boost.Test只输出逐用例`N assertions out of M passed`行，从不打印短报告尾标`No errors detected`，旧`ok_text`条件系统性为假。
- 此时运行时定位问题已排除：上一轮rpath修复后6二进制已exit=0、无`Error relocating`和`symbol not found`，失败纯属判定口径错误。
- 与`/tmp`只读诊断无关，配方与测试均未写`/tmp`，`HMBS_PLATFORM_CAPABILITIES/tmpdir`子串为误命中。

## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 在`archives/q/qm-dsp/1.7.1/conanfile.py`测试判定逻辑中删除`No-errors-detected`字符串检查。
2. 新增正则解析全部`assertions out of passed`行，要求至少一行且全部满通过（N==M），无算术回补分支。
3. 成功条件改为`exit==0且Running N==审计期望且断言行满通过`，恒等式结构不变。
4. info日志增加`full-pass-assert-lines`计数行，便于下次核对逐用例行数。
5. 保持未提交等待HMBS复跑真机预检；本任务下一轮日志验证`64/64 passed`，确认判定修复生效后失败才转移到test_package工具链阶段。

## 禁止策略
- 禁止在`--report_level=detailed`下继续以短尾标为通过条件；该模式必然缺失该尾标，会把全部exit=0判为`missing-No-errors-detected`的0/64失败。
- 不断言短报告模式行为；若上游更改report级别，必须重审正则。

## 与相近条目的边界（查重）
- 与每轮日志必带的`HMBS_PLATFORM_CAPABILITIES/tmpdir`子串误命中不重叠：后者为环境能力探针，与SSE直写、CFLAGS覆盖、rpath与detailed判定、工具链文件后补丁的根因签名均无关。
- 与`ctest/automake/munit`等不同框架汇总解析不重叠：本条目仅处理Boost.Test `--report_level=detailed`的`N assertions out of M passed`形态。
- 与本任务内其他根因不重叠：构建时直写剥离SSE标记解决`source file is different`补丁失败，命令行CFLAGS补齐`-I.`解决`maths/MathUtilities.h file not found`覆盖问题，LDFLAGS追加无引号rpath解决`Error relocating`的rc=127，test_package工具链文件后补丁解决`conan_toolchain.cmake`死路径烘焙；本条目仅覆盖判定口径。

## 适用判断
- 适用：Boost.Test以`--report_level=detailed`运行并需机器判定的小；关键词`boost_test, report_level_detailed, hmbs_repair_method`；适用于所有同模式上游测试判定。
- 不适用：短报告模式、ctest/automake/munit汇总、非Boost.Test二进制。
- 注意：若上游更改report级别需重审正则；本轮不扩展到短尾标兼容分支。
