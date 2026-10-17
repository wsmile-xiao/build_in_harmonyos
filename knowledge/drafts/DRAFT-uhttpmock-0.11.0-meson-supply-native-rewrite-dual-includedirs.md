# DRAFT-uhttpmock-0.11.0-meson-supply-native-rewrite-dual-includedirs
> Meson配方OHOS真机缺meson/pkg-config且profile编译器路径缺失时的供给与native file重写及版本化头双根
## 问题特征（真实日志片段/标记）
- HMBS_BUILD_TOOLS仅含cmake/make/ninja/python3，真机PATH无meson与pkg-config
- ../meson.build:1:0: ERROR: Unknown compiler(s) clang路径在worker上ENOENT
- ../meson.build:50:11: ERROR: Dependency lookup for glib-2.0 with method pkg-config failed: Pkg-config for machine host machine not found
- test_package阶段CMAKE_C_COMPILER钉死路径加System is unknown to cmake
- 消费者侧fatal error libuhttpmock-1.0/uhttpmock/uhm.h file not found，后变为uhm.h内部uhttpmock/uhm-message.h file not found
- 上游meson test 2项中server FAIL，not ok tls-certificate，TLS support is not available，GLib-GIO-DEBUG显示GDummyTlsBackend，标记为2/2/1/1加gaps
## 根因
- HMBS仅注入cmake/make/ninja/python3，空build_requirements沿用CI全局meson假设，真机缺meson与pkgconf本体
- ohos-aarch64 profile把tools.build compiler_executables钉死在/data/service/hnp/bin/clang，该文件在预检worker缺失，MesonToolchain与CMakeToolchain原样烘焙致探测失败，需conf存在性校验后重写
- MesonToolchain默认不在conan_meson_native.ini写pkgconfig行，事后裸行正则永不命中，需generate内预先pin绝对路径加PKG_CONFIG导出加无行插入兜底
- 上游头布局为include/libuhttpmock-1.0/uhttpmock下多头，消费者带版本前缀包含而头内部以短前缀互含，单根只能满足一侧，需双根
- OHOS glib栈无GIO TLS模块仅GDummyTlsBackend，同栈libsoup3同源缺口不可补依赖，TLS子项失败属ohos_feature缺口
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. archives/u/uhttpmock/0.11.0/conanfile.py的build_requirements新增tool_requires meson 1.11.0与tool_requires pkgconf 3.0.5，不引入registry ninja
2. 新增resolve逻辑按conf存在性检查到CC与CXX环境到PATH到已知LLVM目录到shadow布局顺序探测真clang，as改为可选仅pin真实存在文件，ar保留必需支持llvm-ar回退
3. generate内解析到pkgconf绝对路径则预先设置binaries中pkgconfig并导出PKG_CONFIG到环境与buildenv，兼容pkgconf与pkg-config双名，找不到时不猜测
4. tc.generate后重写conan_meson_native.ini中c与cpp行为真实编译器绝对路径，重写或无行插入binaries中pkgconfig行，build开头防御性重导出PKG_CONFIG
5. test_package改显式generate，用CMakeToolchain加CMakeDeps加VirtualRunEnv与BuildEnv，cache_variables预pin加生成后重写conan_toolchain.cmake中钉死编译器字符串加CC与CXX导出
6. 主包package_info includedirs改为include与include/libuhttpmock-1.0双根，保留glib与libsoup透传includes，满足消费者前缀与内部短前缀两侧
7. 上游解析器按归一化名去重last verdict wins，TLS失败按真实字符串发射gaps类别ohos_feature并透传，build失败分支有gaps时转警告继续打包以放行test_package，无gaps仍硬失败
## 禁止策略
- 禁止保留/data/service/hnp/bin/clang等不存在路径或把clang驱动冒充为as传入meson，否则报Unknown compiler并ENOENT中断
- 禁止仅做事后裸行替换而不做预pin与无行插入，MesonToolchain默认无此行会导致永不命中
- 禁止单根或删除TLS断言消错，须保留双根与gaps真实日志证据
## 与相近条目的边界（查重）
- upstream/main在32018bae查重命中无meson native file、无pkgconfig预pin、无行插入、双根或GDummyTlsBackend条目，本条目为新增
- 现有compile_error与hmbs_platform_capabilities命中仅为日志同词，fcft同错仅tool_requires即成功而本配方需预pin加插入，bzrtp存在性探测 doctrine仅转用于meson与cmake工具链重写，autotools与Go与Rust为相邻场景不适用
- 关键词meson_native_file加pkgconfig_pre_pin加compiler_path_missing加dual_includedirs加ohos_feature_tls_gap标识本类Meson加版本化头库
## 适用判断
- 适用：Meson配方在HMBS真机报meson缺失、Unknown compiler、Pkg-config not found三段递进，且头安装在include下版本子目录消费者与内部前缀不一致时
- 适用：test_package用CMakeToolchain且同样被profile钉死编译器路径时，同理重写conan_toolchain.cmake
- 不适用：autotools半残包direct-cc、无pkg-config二进制调用的纯CMake静态库、非GDummy证据的未知TLS失败
- 注意：ar保持必需不可全可选，只pin真实存在可执行绝对路径，无gaps失败不得转警告
