# 草稿 — 源码分析误用 master 分支构建文件：tag 归档内容才是配方唯一依据

> Status: **Draft**（待审核 promote）| severity: `2` | category: `headers, build-system, conan, methodology` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-libuinputplus-0.1.4-tag-archive-vs-master-buildfile.kv`

## 可复现症状与稳定错误签名

- `test_package/.../test_xxx.cpp:13:10: fatal error: 'uInput.hpp' file not found`
- 包管理日志同时显示头文件已打包，只是路径在子目录：`Packaged 3 '.hpp' files` + cmake --install 日志 `Installing: .../include/uInputPlus/uInput.hpp`
- 稳定签名：test_package 头文件 not found，且 **install 日志里该头文件路径与配方 `cpp_info.includedirs` 不一致**。

## 根因与最小复现

- 触发实例：libuinputplus 0.1.4 真机 shadow CI r3（2026-09-27）。
- W1 分析时抓取了 `raw.githubusercontent.com/YukiWorkshop/libuInputPlus/master/CMakeLists.txt`（精简版：单目标、头文件平铺装 `include/`），据此写 `cpp_info.includedirs=["include"]` 并在 notes 里描述布局。
- 而 v0.1.4 **tag 归档**（sha256 a537e156... 已被 conan 校验下载）的 CMakeLists 实际为：显式 `SHARED` + `_Static` 双目标、SOVERSION、头文件装 `include/uInputPlus/` 子目录、安装 `lib/pkgconfig/uInputPlus.pc`。
- 结果：主包构建安装成功，test_package 编译即找不到头。本地交叉编译验证因直接编 .cpp 绕过了 CMakeLists，未能提前暴露。
- 与 E217 的边界：E217 的根因是“没检查 install DESTINATION 子目录”；本条根因是“检查了**错误版本**的构建文件”——tag 与 master 内容不一致时，分析对象选错。

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 按 master 分支 CMakeLists 写 includedirs=["include"] | r3 真机 test_package 编译失败（本条根因） |
| 本地只交叉编译 .cpp 源文件验证 | 编译通过但绕过了 install 布局，未暴露问题（教训：消费者验证要按“安装后布局”组织 include） |
| 读 tag 归档 CMakeLists + `.pc.in` 的 Cflags 行 | 一步得出 `includedirs=["include/uInputPlus"]`，r4 起 test_package 编译链接通过 |

## 最终方案、输入输出与真实验证

- 输入：目标 tag 归档内的 `CMakeLists.txt` 与 `uInputPlus.pc.in`。
- 处理：`.pc.in` 的 `Cflags: -I${includedir}/uInputPlus` 直接给出消费端 include 契约；配方同步修正。
- 输出：`cpp_info.includedirs = ["include/uInputPlus"]`，notes/manifest 布局描述同步更正。
- 真实验证：r5 真机 shadow CI exit 0，L0/L1/L4/L5 全 pass，test_package 40/40 断言通过（iter 记录见 archives/l/libuinputplus/0.1.4/notes.md）。

## 适用范围、反例、解除条件与风险

- 适用：所有 W1 源码分析，尤其上游 master 与最新 tag 之间有过重构/精简/打包化的仓库（本例 master 反而比 tag 简单）。
- 反例：上游 master 与 tag 构建文件一致时按哪种读都行；但“一致”本身也需 diff 确认，不能默认。
- 解除条件：无（方法论条目）。
- 风险：只看 install 布局不看 .pc 时仍可能选错 include 契约；.pc 的 Cflags 是上游自己声明的消费契约，优先级高于自行推断。

## 知识库查重与新增价值

- grep index.tsv：E217（includedirs 未匹配 install 子目录——终态症状同、根因层不同）、E221（cpp_info 公开契约）。无“tag vs master 分析对象选错”条目。
- 新增价值：①把根因前移到 W1 分析对象选择（防患），而非事后改 includedirs；②给出 `.pc.in Cflags` 这一步到位的契约推断手法；③记录“本地交叉编译绕过构建系统导致假验证”的教训。
