## PR 信息
- **三方库名称**：boost1.84-locale（Boost.Locale 组件包，从 Boost 1.84.0 完整源码独立裁剪）
- **上游版本**：1.84.0（boost_1_84_0.tar.gz，SHA256 a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724）
- **上游仓库地址**：https://github.com/boostorg/locale （locale 子模块；完整源码出自 Boost 官方发布仓库 https://github.com/boostorg/boost tag boost-1.84.0）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E068（Boost.Build SHELL 执行机制在鸿蒙不兼容——b2 不可用，手动编译绕过）；底稿 archives/b/boost/1.84.0 已验证方案；E999 先例（平台限制豁免口径）

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 15 | 来源：libs/locale/test/（上游 Jamfile.v2 的 run 目标：14 个通用测试 + test_message；非 std 后端专属测试 test_collate/test_convert/test_boundary/test_formatting/test_icu_vs_os_timezone/test_winapi_*/test_posix_* 自带后端守卫，本包 std-only 配置下编译后自动 Skipping 返回 0，不计入运行矩阵） |
| 集成测试 | 0 | - |
| 其他测试 | 0 | - |
| **合计** | **15** | test_message 需 cwd=libs/locale/test 读取 .mo 文件 |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 15 | 不变 | 全部 15 项上游测试绕过 b2 手动编译运行：10 项完整通过（100%）；5 项因 OHOS musl C 库数据差异部分断言失败（合计 23 个失败断言，详见下方平台限制说明） |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 9 | 新增 | test_package 九组校验（generator+info facet/musl iconv 编码往返/invalid charset 异常/to_upper/collate/as::number 格式化/format 插值/date_time 年算术/message 回退），CMake find_package(Boost COMPONENTS locale) 消费链路 + ELF 签名后真机运行，全过 |
| **合计** | **24** | **+9** | |

---

## 上游测试用例修改说明
### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例
  （上游测试源文件零修改。b2 在 OHOS 不可用，改为 clang++ 直接编译 libs/locale/test/ 原始测试源文件链接 libboost_locale.a 运行，测试内容与断言与上游完全一致；test_message 按上游 Jamfile 语义在 libs/locale/test 目录下运行）

---

## 补全测试用例说明
### 上游是否存在无测试用例，适配后补全的情况？
- [x] **否**，上游已有测试用例覆盖
  （上游 locale 库自带 15 项可运行测试，全部真实运行；另新增 test_package 九组 API 冒烟校验作为鸿蒙特有测试，非补全性质）

---

## 验证结果
- 编译状态：通过（conan create PASS；产物 libboost_locale.a（21 源文件）+ 完整 boost 头文件树）
- 上游测试用例通过率：10/15（66.7%；5 项部分断言失败合计 23 个，全部为 musl C 库数据差异的平台限制，非适配缺陷——test_message 2118 断言中仅 1 个失败（99.95% 断言级通过率），test_std_formatting 42/50，test_std_collate 32/40，test_codepage_converter 2 个，test_encoding 4 个）
- 新增测试用例通过率：9/9（100%，test_package ctest boost_locale_test 通过）

验证命令：
```bash
conan create archives/b/boost1.84-locale/1.84.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
关键输出：`TOTAL 15: 10 passed / 5 failed`（5 项失败均为 musl 平台限制，断言明细见 reports/test-report.md）、`boost1.84-locale smoke test PASSED`

---

## 补充说明
- **打包方式**：b2 构建系统在 OHOS 不兼容（E068，SHELL 执行机制失败），采用底稿 archives/b/boost/1.84.0 的手动编译方案——libs/locale/src/boost/locale 下 21 源文件（核心 15 + std 后端 5 + gregorian 1）逐文件 clang++ 编译 + llvm-ar 归档为 libboost_locale.a，全量 boost 头文件树随包分发
- **后端配置（本包关键决策）**：std 后端启用（POSIX/WinAPI/ICU 禁用）+ musl libc 内置 iconv。实测发现上游 Jamfile.v2 明确要求非 Windows 平台必须有 iconv 或 ICU（std-only 是上游不支持配置，编码转换 API 会全部抛 invalid_charset_error）；OHOS musl libc 自带 iconv（iconv.h 属 sysroot 标准头，符号在 libc 内，与 glibc 平台布局一致），支持 ISO8859-x/cp125x/cp932/iso-2022-jp/koi8-r 等，**零新增 conan 依赖**
- **补丁**：0001-ohos-pthread-cancel-fix.patch——OHOS musl 无 pthread_setcancelstate，通过 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性宏跳过（R8 合规，无平台宏硬编码；与底稿 boost/1.84.0 同一补丁，locale 的 localization_backend.cpp 引 boost/thread 头链必需）
- **依赖**：无 conan requirements（iconv 来自 musl libc；boost::system 自 1.69 起 header-only）
- **CMake 组件**：Boost::locale / Boost::headers / Boost::system（header-only 声明），cmake_file_name=Boost 与其他 boost1.84-* 组件包一致
- **运行环境**：测试二进制运行需 SDK libc++_shared.so（clang++ -print-file-name 动态定位注入 LD_LIBRARY_PATH）+ ELF 自签名（llvm-objcopy --remove-section .codesign + binary-sign-tool，继承 boost1.84-chrono 先例），配方内全自动处理
- **平台限制豁免（E999 先例口径）**：5 项测试的 23 个失败断言全部根因于 musl 与 glibc 的 C 库数据/行为差异（换 glibc 环境即消失），非适配缺陷：
  1. gbk 字符集 musl iconv 不支持（test_encoding 一处无守卫调用异常终止）
  2. iso-2022-jp 编码方向 musl 逐字符独立 ESC 转义序列 vs glibc 合并连续同字符集字符（字节级差异，两方向往返解码语义等价——均解出"冬季"）
  3. musl 无 //TRANSLIT（glibc 专有扩展）：test_message 的 ISO-8859-8 转换 1/2118 断言，musl 以 * 替换不可转换字符 vs glibc 删除；test_codepage_converter 的 cp932 映射差异 2 断言
  4. musl locale 数据限制：en_US.UTF-8 的 collate 为字节序（test_std_collate 期望 a<ç<d 的 locale 感知排序，8 断言）、money_put 无 mon_grouping 千分位数据（test_std_formatting 8 断言）；sv_SE.UTF-8/en_US.ISO8859-1 等 locale 不存在（上游测试内建 get_std_name 判空走"not supported, skipping"分支，上游设计已兼容）
  - 佐证：同一批断言在 std-only（无 iconv）配置下失败范围更大（14 项测试 10 项失败），启用 musl iconv 后断言级通过率从 ~64% 提升至 99%+；ISO-8859-1↔UTF-8 往返转换字节精确（test_utf/test_codecvt/test_catalog 等 10 项 100% 通过）
