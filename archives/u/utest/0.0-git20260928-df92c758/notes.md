# utest 0.0-git20260928-df92c758：当前适配记录

官方源码固定 df92c7589f7f1d1bd22489cc029e8a61ef538588，SHA-256 00e8918b42a8e10efaeb38ca7d6a9c32cea14b956e8d511a8379cd26288718b5。滚动归档与不可变归档的30个普通源码文件逐字节一致；不能以默认分支名代替版本身份。

包安装单头文件，不代表没有上游构建或测试。build() 执行原上游 CMake/CTest 完整清单，test_package 单独执行安装头消费者和鸿蒙专项。许可证是实际 LICENSE，不是不存在的 LICENSE.md。

## 失败与修复

- r001：裸 CMake 名称经 OHOS Python posix_spawn 返回 ENOENT，解析绝对工具路径。
- r002：SDK clang 编译步骤注入链接 --code-sign 参数，严格告警失败；只忽略 driver 该项无效参数告警。make4.4 FIFO 在 HMDFS 失败，使用真实 pipe jobserver。
- r003：OHOS 缺 addchdir_np，选择 vendored subprocess.h 既有 fork/chdir/exec 后端。
- r004/r005：完整原生套件中 type_printers 两项创建 tmpfile 流失败；设置 TMPDIR 后仍返回 NULL，但本次未记录 libc 实际访问路径或 errno，不推断具体路径。r005 完整日志保存，不以 r004 的截断尾部代替。
- r006：测试私有临时流后端中的 C malloc 转换和 NULL=0L 不符合原上游 C++ 严格告警，修正为语言标准相容的转换/null。
- r007：原 CMake、测试 TU 和安装头不修改，保留全部断言、sanitizer、随机顺序及固定种子场景。13/13 CTest、消费者2/2、鸿蒙专项1/1；一次launch、AFTER和清理链均通过。

## 真实分母与状态

CTest场景13个；每个套件内部2178例，2168 PASS与10个故意Todo skip控制。不要将重复场景内部测试累加，也不要声称无内部skip。正式原生Conan create与本地CI模拟已PASS，运行输入哈希不变；finish整体PARTIAL_POST_W3（RC1）的step5b/7/8旧主线知识、范围比较和打包标记要求如实保留。当前HEAD平台CI/AI Review仍为独立门禁，未宣称已提审。

新知识 E2026100405 草稿对补充至 PR #2991：混合语言严格告警中的测试专用临时流后端与分母边界。旧 DRAFT-header-only-package-spec 误称无上游测试/build pass，只从当前候选移除；历史Git版本保留。
