# 纯 Python 包的解释器级依赖（numpy）三段式解析：CI Worker 宿主无 pip 包 + 制品仓交叉 ABI 注入 + E212 软跳过

> Draft: `DRAFT-IGOR2-059-PY-NUMPY-THREE-STAGE`
> Stem: `igor2-0.5.9-py-numpy-three-stage-resolution` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-IGOR2-059-PY-NUMPY-THREE-STAGE
- **严重度**: 2
- **类别**: conan|python|ohos-platform
- **触发工具**: conan|python|pytest
- **阶段**: build|test
- **实证构建**: #66321（失败根因）/ #66374（修复后全绿）

## 错误特征

```
ConanException: host python3 (/data/service/hnp/bin/python3) cannot import
numpy — igor2 requires numpy>=1.19.2 at runtime:
ModuleNotFoundError: No module named 'numpy'
```

- CI 侧 12.9 秒快速失败，`conan-build-test` 步骤，CI 自动归类"未知"
- 本地 devbox/真机同配方全绿（宿主 python3 带 pip numpy）——环境差异伪装成"配方时灵时不灵"

## 根因（平台机制因果）

1. **纯 Python 包的消费形态是解释器 import，不是 ELF 链接**。conan 的
   cpp_info/libs 依赖链对它们完全不起作用，numpy 这类运行时依赖必须由
   配方作者显式安排来源。
2. **宿主 python3 双环境分裂**：devbox/真机（~/usr/local/bin/python3）
   有 pip 装的 numpy；CI Worker（/data/service/hnp/bin/python3）是极简
   环境，一个 pip 包都没有。badread 0.4.2 的"pip 级依赖、非 conan
   requires"先例只在 devbox 成立，在 CI 被证伪。
3. **制品仓 numpy 的 ABI 边界**：numpy/2.5.2 的 .so 是交叉编译签名件
   （NEEDED libc++_shared.so，aarch64-linux-ohos ABI），宿主解释器默认
   路径加载不到——必须 PYTHONPATH 指向其 site-packages 且
   LD_LIBRARY_PATH 含 /system/lib64（系统真 so 提供 __h 命名空间符号；
   SDK 侧 libc++.so 是链接器脚本 INPUT(-lc++_shared)，musl 加载器不认）。
4. **E212 沙箱层**（与 issue #2538 同族）：即使注入正确，CI Worker 的
   loader 策略可能拒绝 dlopen 用户路径 .so（Permission denied）。

## 修复方案（三段式解析）

```python
# 1) requirements 显式 conan require（依赖从制品仓来，audioflux 先例）
def requirements(self):
    self.requires("numpy/2.5.2")

# 2) build()/test() 三段式：
#    (a) 宿主 python3 自带 numpy → 真机/devbox 快路径
#    (b) conan numpy site-packages 注入 PYTHONPATH + /system/lib64 注入
#        LD_LIBRARY_PATH → CI Worker 唯一可行路径
#    (c) 仍失败（E212 沙箱拒 dlopen）→ 软跳过 + warning 说明，
#        全量结果以真机 conan create 实测记录进 MANIFEST.yml
# 3) test_package 同款注入 + E212 静态校验回退
#    （包布局 + wrapper 可执行 + numpy .so 的 ELF/.codesign）
```

**红线**：禁止把"宿主无 numpy"设计成硬失败（ConanException）——CI Worker
环境差异不是配方错误；也禁止静默跳过不留痕——上游测试形同虚设。

## 与既有条目的边界（查重）

- **issue #2538 / E212 家族**：覆盖"test_package 沙箱拒 dlopen 已加载的
  .so"——是"加载被拒"问题；本条解决"依赖从哪来"（来源缺失，
  ModuleNotFoundError）。阶段不同（build 期 vs test 期），触发签名不同。
- **baler vendor stub 方案**：掩盖真实依赖断链，仅适配合成断言场景；
  本条反其道——require 真制品 + 差异化环境三段降级。
- 增量：首个"解释器级依赖来源"维度的完整闭环（require → 注入 → 沙箱
  软跳过 → 真机记录），可推广到一切带 numpy/scipy 依赖的纯 Python 件。

## 适用范围

所有 setuptools 后端、无 C/C++ 扩展、pyproject 声明了解释器级运行时依赖
的纯 Python 包（python-require / application 型配方），以及任何在
build()/test() 里 subprocess 调 python3 跑上游测试或探测导入的配方。

## 红线与教训

- 上游测试探测**不要用 conan 的 self.run**（env wrapper 会重置 PATH），
  用 subprocess + 显式绝对解释器路径
- numpy 注入的 LD_LIBRARY_PATH 顺序：/system/lib64 必须在 SDK lib 之前
  （遮蔽会导致 sign-tool 类工具 127 退出）
- 修复后必须本地 conan create 复验再推（R44：不带着已知错误去撞 CI）
