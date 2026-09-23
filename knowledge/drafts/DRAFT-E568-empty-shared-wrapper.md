# E568（草稿）：上游 SHARED 包装库空壳 → 改交付静态库

**状态**: pending-editor-review（随 mmkv PR #9693 提交，最终编号由主编确认）

## 一、错误特征（可机器匹配）

上游"SHARED 包装库"构建成功，但：

```console
$ llvm-nm -D --defined-only libmmkv.so
000000000000173c T _fini
0000000000001728 T _init
```

消费者链接时报：

```console
ld.lld: error: undefined symbol: <static-lib-symbol>
>>> referenced by wrapper.cpp.obj in archive libcore.a
```

CMake link.txt 特征：`clang++ -shared -o libX.so wrapper.cpp.obj libcore.a`，
且 wrapper.cpp 是空 TU（只有 `#include <X.h>`，无任何符号引用）。

## 二、根因

多平台库（Android 出身 SDK 常见）真实实现在 `Core/` 静态库 target，
`wrapper/` 只提供 SHARED 打包 TU。链接器对静态库归档按需拉取成员：
空 TU 不引用任何符号 → 全部成员被丢弃 → `.so` 只剩 `_init/_fini`。

**编译期完全通过**——这是隐蔽陷阱，`conan create` 不跑消费者链接就发现不了。

## 三、解决方案（代码级）

首选：交付静态库（上游官方 Android/iOS SDK 同形态）：

```python
def package(self):
    # Core 产 libcore.a，复制为规范包名 lib<name>.a
    shutil.copy(os.path.join(self.build_folder, "libcore.a"),
                os.path.join(self.package_folder, "lib", "libmmkv.a"))

def package_info(self):
    self.cpp_info.libs = ["mmkv"]
    self.cpp_info.system_libs = ["hilog_ndk.z", "pthread"]  # 按平台
```

下游强制 .so 时：`-Wl,--whole-archive core -Wl,--no-whole-archive`
或 patch 包装 TU 显式引用核心符号。

## 四、降级方案

--whole-archive 后导出仍不全（visibility 差异）→ patch 包装 TU extern
引用核心 API；仍不通 → 回退静态交付，PR 说明消费者自行 whole-archive。

## 五、红线

- 禁止把空壳 .so 当"编译成功"交付（消费者一链就炸）
- 禁止用 dummy 符号凑数骗过 nm 检查
- 交付形态变更（.so→.a）必须在 notes.md 和 PR 说明中写明理由

## 六、实证

mmkv 2.4.2（Tencent MMKV，PR #9693）：
- `POSIX/src` SHARED 包装 → libmmkv.so 空壳（llvm-nm -D 实测仅 _init/_fini）
- 改交付 `Core` 静态库 → libmmkv.a
- conan-verify G2（干净构建）/G3（同名库隔离）/G4（产物完整性）全绿
- 上游测试 21/21 PASS（本机 OHOS aarch64）
- test_package 消费者 C++/C bridge round-trip 全绿

## 关联

- E092（CMake HarmonyOS 平台模块缺失）——本条是"构建系统行为"类的另一独立模式
