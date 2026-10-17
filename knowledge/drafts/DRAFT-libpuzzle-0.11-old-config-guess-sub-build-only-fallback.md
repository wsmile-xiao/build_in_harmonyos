# DRAFT-libpuzzle-0.11-old-config-guess-sub-build-only-fallback
> 老autotools捆绑陈旧config.guess/sub不识别HarmonyOS与aarch64时仅保留--build的原生构建回退
## 问题特征（真实日志片段/标记）
- 真机conan create在configure的build检查处失败：`configure:4992: error: cannot guess build type; you must specify one`，起因是2008版config.guess不认识HarmonyOS（attempt18513）。
- 按常规交叉思路补`--build`后build检查通过（`checking build system type... x86_64-pc-linux-gnu`），但host检查随即失败：`configure:5032: error: /bin/sh .../config.sub aarch64-linux-ohos failed`，即`--host=aarch64-linux-ohos`被2008版config.sub拒绝（attempt18513 excerpts与attempt18578证伪链）。
- 该配方此前只传`--host`未传`--build`，且configure无AC_CANONICAL_HOST相关校验旁路，命中上述两连败。
## 根因
- libpuzzle 0.11的configure.ac含AM_INIT_AUTOMAKE，会触发build-system-type检查并调用捆绑的2008版config.guess/config.sub。
- 该版本既不识别HarmonyOS（UNAME层面猜测失败），也不认识aarch64。attempt18513先加`--build=x86_64-pc-linux-gnu`跳过config.guess使build检查通过，选x86_64是因为2008版config.sub尚不认识aarch64，该值只影响cross判定、真实目标码仍由CC/CXX决定。
- attempt18578形成证伪链：保留`--host=aarch64-linux-ohos`的策略被真机证伪，此前“--host被接受但不使用”的假设错误，老config.sub同样会校验并拒绝该--host，故必须删除--host，仅保留--build，缺省host等于build即原生构建，conftest在真机实跑。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 在`archives/l/libpuzzle/0.11/conanfile.py` OHOS手动configure调用中新增`--build=x86_64-pc-linux-gnu`，跳过config.guess识别失败；不要选用aarch64作为--build值（老config.sub会拒）。
2. 在同一configure调用中删除`--host=aarch64-linux-ohos`，仅保留--build；缺省host即等于build，build==host为原生构建，该三元组仅是给老脚本的占位，真实目标码仍由已探测的CC/CXX决定。
3. 保留手动configure路径的`--enable-shared/--disable-static`或`--disable-shared/--enable-static`开关，与generate()按`options.shared`映射保持一致。
4. 在注释/docstring及`archives/l/libpuzzle/0.11/manifest.yaml`与`notes.md`中修正错误的“--host无用论”，明确注明未补丁config.sub时禁止加回该--host；同步更新configure_options说明。
5. 验证：真机`conan create`日志确认build检查通过且不再出现上述两条error_signature，configure进入后续编译检查。
## 禁止策略
- 禁止在未替换/补丁捆绑老config.sub的情况下加回`--host=aarch64-linux-ohos`（对应`config\.sub aarch64-linux-ohos failed`）：老脚本必然报Invalid configuration并使configure exit 1，任务退回修复循环。
- 禁止把--build改为aarch64等老config.sub不认识的值来“凑交叉语义”，同样会被拒绝；禁止臆测host被忽略而不做真机验证。
## 与相近条目的边界（查重）
- 现有readonly_tmp条目只解决可写TMPDIR隔离（C++ compiler cannot create executables伴随/tmp只读），ncrack条目只解决umask/子目录configure failed for，E165条目只解决shebang，均不覆盖本场景的老脚本三元组识别失败。
- 本条目仅适用于捆绑陈旧config.guess/sub且未打补丁的autotools库的三元组校验失败，不替代TMP隔离、编译器发现、install垫片等其他libpuzzle修复。
- fallback若需恢复交叉语义，必须先更新config.guess/config.sub到可识别HarmonyOS与aarch64的新版，属另一改动，不在本rec内默许加回--host。
## 适用判断
- 适用：autotools配方捆绑2008左右config.guess/sub，真机报cannot guess build type或config.sub对aarch64-linux-ohos校验失败，且真实编译由CC/CXX决定、可接受build==host原生构建占位时复用。
- 不适用：已更新config脚本可识别新系统/架构时；configure要求严格交叉（host!=build且需真实交叉测试）时；失败实为TMP只读、编译器缺失、依赖头缺失等其他原因时。
