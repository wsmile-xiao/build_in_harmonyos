# E322: OHOS ELF 重签必须用 env=None，conanbuild env 破坏 binary-sign-tool

## 基本信息
- **严重度**: 3 (blocking)
- **类别**: ohos | codesign | conan | meson
- **触发工具**: conan
- **阶段**: package
- **首次发现**: gdk-pixbuf 2.42.12 编译 (2026-08-07)

## 错误签名

package 阶段 / 运行期：
```
binary-sign-tool ... Error loading shared library
binary-sign-tool: invalid signature
/usr/lib/ld.so: EPERM: Operation not permitted (加载 .so)
```

## 根因分析

OHOS 工具链在链接时自动给 ELF 添加 `.codesign` 签名段；`meson install` 会重写
RPATH（修改 dynstr），使签名失效，动态加载器以 EPERM 拒绝加载该 `.so`。

需在 conanfile 的 `package()` 中重新签名。但 conanfile 的 `self.run()` 默认应用
conanbuild env，其 `LD_LIBRARY_PATH` 会破坏 Java 版 `binary-sign-tool` 的类加载
环境，生成无效签名，加载仍报 EPERM。

## 受影响范围

OHOS 平台上所有被 meson/install 重写 rpath 的库与命令行工具（meson 系 GNOME 库）。

## 解决方案

### 方案 1（推荐）：package() 中重签 + self.run(env=None)

```python
# package() 中 meson.install() 之后：
# 1. 用 llvm-objcopy 移除失效的 .codesign 段
# 2. 用 binary-sign-tool 重新签名 bin/ 与 lib/ 下所有 ELF
# 3. self.run(..., env=None) 避免 conanbuild env 干扰签名工具
self.run('binary-sign-tool sign -inFile f -outFile f -selfSign 1', env=None)
```

### 禁止做法
- ❌ 不要在 `self.run()` 中省略 `env=None` 重签——conanbuild env 的 LD_LIBRARY_PATH 会生成无效签名
- ❌ 不要跳过签名（未签名 ELF 在 OHOS 上无法加载）

## 验证
```bash
# 重签后运行冒烟测试
gdk-pixbuf-query-loaders --version   # 正常输出即为签名有效
```

## 关联条目
- 相关: E321（gmodule pc 合成）
