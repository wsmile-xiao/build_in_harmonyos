# flex 2.6.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-26
- 编译器: clang
- 状态: built

## 编译步骤
1. 下载源码 `https://github.com/westes/flex/releases/download/v2.6.4/flex-2.6.4.tar.gz`
2. 应用补丁（如有）
3. `./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-gnu`
4. `make -j$(nproc)`
5. `make install`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conandata.yml 格式错误 | sources 多了一层版本号嵌套 | 移除版本号嵌套，直接使用 url/sha256 |
| 2 | conanbuild.conf 不存在 | 缺少 generate() 方法 | 添加 generate() 方法，调用 AutotoolsToolchain |
| 3 | package() 复制路径错误 | autotools.install() 会因 doc/ 缺少 makeinfo 失败 | 手动复制 flex 二进制、libfl.a、FlexLexer.h |
| 4 | config.guess 无法识别 HarmonyOS | config.guess 脚本太旧（2015年） | 添加 --build=aarch64-unknown-linux-gnu 参数 |
| 5 | config.status 权限错误 | HMDFS 不允许在 $PWD 执行临时 awk 脚本 | 补丁 0006: mktemp 模板改用 `${TMPDIR:-/tmp}` 避免相对路径 |
| 6 | 缺少静态链接 | R26 规则要求终端工具静态链接 | 添加 tc.extra_ldflags.append("-static") |
| 7 | build() 中多余的 install 调用 | autotools.make(target="install") 与 package() 重复 | 移除 build() 中的 install 调用 |
| 8 | configure 检测到 reallocarray 但链接时找不到 | OHOS bionic 有头文件但无实现 | generate() 中添加 `ac_cv_func_reallocarray=no` |

## 依赖版本
无外部依赖

## 验证结果
- flex 二进制正常生成，可执行
- test_package: 验证 flex --version、生成 scanner、编译运行（4 项断言）

---

**编译结束**: 2026-04-29 23:58
**最终状态**: built
