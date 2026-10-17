# E547 — accountsservice 适配 OHOS：polkit 依赖回迁 + 缺失 libc API 的 stub 化

## 错误特征

meson configure 失败或编译报错：

```
Run-time dependency polkit-gobject-1 found: NO  (tried pkg-config and cmake)
ERROR: Dependency "polkit-gobject-1" not found
_UTMPX / WTMPX: No such file or directory
getspnam: No such file or directory
crypt: No such file or directory
```

## 触发条件

- 构建系统: meson
- 阶段: configure / compile

## 根因分析

1. **依赖阻塞**：accountsservice 26.27.3 的 daemon 在 meson.build:161 硬性
   `REQUIRED polkit-gobject-1`，meson_options.txt 无可关闭开关，源码
   `src/daemon.c`/`util.c`/`user.c` 无条件 include `<polkit/polkit.h>` 并调用
   `polkit_authority_*`。polkit 未发布时 configure 在 polkit 处先行失败。
2. **libc API 缺失**：OHOS libc 无 utmpx/wtmp API（登录记账）、无
   shadow-account API（getspnam/fgetspent）、crypt(3) 未在 crypt.h 声明
   （libc.so 有导出）、explicit_bzero 不存在。
3. **版本误派生**：`generate-version.sh` 在非 git checkout 时按目录名取版本，
   但若构建目录位于 git worktree 内会误按外层仓库派生 `26.34.1`。

## 解决方案

### 推荐方案

1. **依赖回迁而非丢弃**：先发布 polkit（`-Dlibs-only=true` 的
   libpolkit-gobject-1 客户端库即可满足 `polkit-gobject-1.pc`），再回本包
   finish。libaccountsservice 本身只链接 glib/gio/gio-unix，polkit 设为
   private 依赖。
2. **缺失 API stub 化**：
   - utmpx/wtmp：提供 no-op stub（utmpxname/setutxent/getutxent/endutxent）；
   - shadow-account：getspnam/fgetspent 返回 NULL 的 stub；
   - crypt(3)：配方内声明 extern 原型；
   - explicit_bzero：以可移植 volatile 覆写替代。
3. **版本钉住**：补丁钉住 26.27.3 发布 tag（0001-fix-version）。

```bash
meson setup build -Dsystemdsystemunitdir=no -Dwtmpfile=/var/log/wtmp \
  -Dtests=false -Dintrospection=false -Dvapi=false -Ddocbook=false \
  -Dgtk_doc=false -Dcreate_homed=false
meson compile -C build
conan create . --build=missing
```

### 禁止做法

- ❌ 因依赖阻塞直接丢弃包（W0 只停止当前轮，依赖发布后必须回迁）。
- ❌ stub 硬编系统调用/syscall——OHOS 沙箱拦截，应停在库 API 层。
- ❌ 伪造依赖状态或构建证据（result.json 必须如实记录 built）。

## 验证

```bash
meson setup build && meson compile -C build
conan create . --build=missing
# test_package: act_* API 链接可用（headless 无 D-Bus 时 no_service=true）
```

## 关联条目

- 相关: E546（polkit libs-only 客户端库）
