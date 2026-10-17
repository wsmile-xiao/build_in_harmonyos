# KDE 库在 KIOCORE_ONLY 基线上的 KIOWidgets 裁剪范式

**素材来源**：libktorrent 26.04.0 适配（KDE Gear，2026-09-20）

## 问题

ohpcd kio 包是 KIOCORE_ONLY 形态（KIOGui/KIOWidgets/KIOFileWidgets 不构建）。KDE Gear
上游库普遍链接 KF6::KIOWidgets，configure 直接失败。连锁三断点：KIOWidgets target 缺失 →
KSharedConfig 头丢失（原由 KIOWidgets 传递）→ KIO::ERR_* 枚举丢失（原经 JobUiDelegate
链式包含）。

## 修法（四步裁剪）

1. `KIOWidgets` → `KIOCore + ConfigCore`（kconfig 的 KSharedConfig）
2. 顶层 `find_package(KF6)` 加 `Config` 组件
3. 删 JobUiDelegate 头的 TU 补 `#include <KIO/Global>`（ERR_* 来源）
4. widgets 专属调用（createDefaultJobUiDelegate / showErrorMessage）注释化——headless
   场景 KJob 的 error()/errorText() 照常报错，零功能损失

## 决策依据

先量化 KIO 用量：`grep -rhon "KIO::[A-Za-z_]*" src/ | grep -oE "KIO::[A-Za-z_]+" | sort |
uniq -c | sort -rn`。libktorrent 实测 35 处 KIO::Job + 10 HideProgressInfo + file_move/
del/storedGet/ERR_* 全是 KIOCore API；widgets 专属仅 3 处（1×createDefaultJobUiDelegate
+ 2×showErrorMessage）——安全裁剪。

## 验证

- conan create 全绿（KTorrent6 库 + test_package）
- 上游 38 个 ecm_add_test 全注册全执行 **100% 通过**
- rc4encryptortest 等 MSE 加密测试通过（配合 LibGcrypt 后端，另见 crypto 后端条目）

## 不适用场景

库内含真 widgets 级 KIO 用量（KDirOperator/KFileWidget/KOpenWithDialog 等）——需等
kbookmarks/kjobwidgets/kiconthemes 发布后重评。
