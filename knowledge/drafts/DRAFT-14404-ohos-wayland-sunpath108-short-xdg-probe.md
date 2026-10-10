# DRAFT-14404-ohos-wayland-sunpath108-short-xdg-probe

## 现象

KWayland 测试 in-process `Display::start()` 直接失败：

```
socket path "/storage/Users/currentUser/.conan2/p/b/<hash>/b/build/Release/.../wayland-0"
plus null terminator exceeds 108 bytes
```

conan 缓存构建树前缀 69+ 字符 + XDG_RUNTIME_DIR 前缀 + 最长 50 字符测试
socket 名 → 超 POSIX sun_path 108 字节硬限。该校验在 libwayland 内部 bind
前执行（LD_PRELOAD 拦不到）。

## 根因

POSIX AF_UNIX `sun_path` 上限 108 字节；conan 缓存构建树路径深是结构性
问题（cache 布局决定，不可改）。DRAFT-10004（qtwayland）已记录同模式，
但其短路径解法钉死在特定机器路径（`/data/storage/el2/base/temp`），跨机不可复用。

## 修复

测试环境短路径**候选探测**（可写探测首个胜出）+ 失败即抛：

```python
def _short_dir(base_name):
    for candidate in (f"/tmp/{base_name}", f"~/.kf5/{base_name}"):  # 展开 ~
        # makedirs + 探针文件写入/删除 = 可写验证
        ...
    # 均不可用 → build_folder 兜底（随后长度断言会 fail-fast）
```

+ **长度断言 fail-fast**：`len(xdg) + 1 + 50 > 108` → `RuntimeError`
（不让错误深到 libwayland 层变成晦涩报错）。OHOS /tmp 只读（E002）时
自然落到 `$HOME/.kf5/`（实例 38 字符，38+1+50=89 ≤ 108）。

## 验证

- kf5wayland/5.116.0 PR #13869：XDG=`$HOME/.kf5/xfullxdg`，ctest 29/29 全过
- 断言在"无短可写路径"场景先于 libwayland 报错抛出（fail-fast 路径）

## 适用范围

- 所有 in-process 测试用 wayland display socket 且构建树在 conan 缓存深路径
  的包（DRAFT-10004 场景的跨机通用化）；
- 同模式可扩展到其他有路径长度硬限的 API（AF_UNIX 之外的类似校验）；
- TMPDIR 同样需要短路径（OHOS /tmp 只读，E002 配合）。
