# DRAFT-clipman-1.2.0-git20200218.39fd4fe-complete-conan-settings-pass-l0p-gate
> conan配方settings缺compiler/build_type致L0p失败时补齐四项过门禁
## 问题特征（真实日志片段/标记）
- CI #43288 conan-build-test步骤L0p失败：`[fail] L0p: settings缺少compiler/build_type`，当前settings = os, arch
- 门禁标记为missing_setting_compiler/missing_setting_build_type，真机修复前`v2:unknown:unclassified_failure`存在
- 触发文件为`archives/c/clipman/1.2.0-git20200218.39fd4fe/conanfile.py`的settings声明行
## 根因
- `ci/conan/build_and_test.sh`约917行L0p检查逻辑要求settings行同时包含os/compiler/build_type/arch四项
- clipman配方只声明了os/arch两项，不满足profile兼容要求，故L0p直接失败
- 这是CI L0p门禁策略类问题，与具体Go构建逻辑无关，跨库可复用
## 修复方案（rec）
1. 打开`archives/c/clipman/1.2.0-git20200218.39fd4fe/conanfile.py`，定位`settings`声明行（原为os, arch两项）
2. 将`settings`补齐为四项：`os, compiler, build_type, arch`
3. 确认新增的compiler/build_type未被Go构建逻辑使用，不影响现有编译行为，仅为满足L0p与profile兼容
4. 重新触发CI conan-build-test，确认L0p通过；真机预检验证原问题消失且门禁全部通过
## 禁止策略
- 禁止保留`settings = "os", "arch"`缺项声明放行；L0p要求四项齐全，否则必报missing_setting_compiler/missing_setting_build_type失败并退回修复循环
## 与相近条目的边界（查重）
- 本条针对CI L0p门禁策略缺settings项场景，解法是补齐四项过门禁
- 现有知识库零命中该场景，未覆盖此类门禁策略修复，故新建条目；区别于编译器报错、源码移植、测试套件类条目
## 适用判断
- 适用：CI报L0 gate missing_setting_compiler/missing_setting_build_type且配方settings行缺项时
- 注意：新增settings仅为满足profile兼容，Go构建不消费compiler/build_type，需确认profile可提供这两项后再补齐
- 验证：CI conan-build-test步骤L0p通过且真机预检全部通过，原v2:unknown:unclassified_failure消失
