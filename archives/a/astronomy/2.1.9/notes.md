# astronomy 2.1.9 适配笔记

## 编译环境
- 构建系统: custom（单文件 C 库，直接编译）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，OHOS aarch64）
- 状态: built

## 编译步骤

astronomy（Astronomy Engine, cosinekitty/astronomy）为单文件 C 库，上游无 C 库构建系统：

```bash
conan create . -pr:h ohos-aarch64 -pr:b ohos-aarch64
```

conanfile.py build() 执行：
```bash
clang -O2 -fPIC -c astronomy.c -o astronomy.o   # cwd = source/c
llvm-ar rcs libastronomy.a astronomy.o
```

package() 安装 astronomy.h → include/，libastronomy.a → lib/，LICENSE → licenses/。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | package_type=library 无 shared 选项报错 | Conan 2 要求 library 类型声明 shared 选项 | 改为 package_type=static-library（本库仅产静态库） |
| 2 | conandata.yml 版本键结构导致 get() 崩溃 | 仓库约定 sources 直接含 url/sha256（AA3D/a52dec 同款） | 改为扁平结构 url+sha256 |
| 3 | ctest.c clang15 -Werror 编译失败 | -Wfortify-source 对 sscanf 缓冲区告警升级为错误 | 构建测试时追加 -Wno-error=fortify-source（不改源码） |
| 4 | generate/novas.c -Werror 失败 | -Wmisleading-indentation 告警 | 追加 -Wno-error=misleading-indentation |
| 5 | 上游 bash 脚本无法执行 | 鸿蒙环境无 /bin/bash，shebang 解析失败 | 用 /data/service/hnp/bin/bash 显式调用 |
| 6 | constellation 测试数据缺失 | 上游 run 脚本硬编码下载 hygdata_v3.csv，HYG-Database 已重构该路径 404 | gh-proxy git 稀疏克隆取 hyg/v3/hyg_v33.csv，转无引号 CSV 后按上游脚本生成 |
| 7 | /tmp 只读（E002） | 鸿蒙 /tmp 只读 | 全部使用 $HOME/tmp |

## 源码修改

无（零补丁）。上游测试构建参数调整见 reports/test-report.md 工具链差异说明。

## 依赖版本

无第三方依赖（仅系统 libc/libm）。

## 验证结果

- conan create 通过（含 test_package 实际运行：Earth heliocentric distance = 1.004708 AU）
- 上游测试：54/55（98.2%），当前配置可执行集合 54/54（100%），详见 reports/test-report.md
- 鸿蒙专项测试 test_ohos：5 项全过（aarch64 ELF / musl / .codesign / 无宿主路径 / 真实天文计算）
- 消费者用例 ohos-astronomy-consumer：全部通过（2024 四季日期 + 日地距离 0.983646 AU）

## 注意事项

- 库 API 中太阳能日心矢量恒为 (0,0,0)、地球地心矢量恒为 (0,0,0)，均为坐标系定义使然，验证脚本应选用地球日心距离/太阳地心距离作断言。
- 2024-04-08 为日全食（新月），月照度接近 0 属正确行为。
---

**编译结束**: 2026-09-19 02:47
**最终状态**: built
