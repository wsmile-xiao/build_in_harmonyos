# catgirl configure 配置提示

## HarmonyOS 平台适配

### 问题1：uname != "Linux"
HarmonyOS 的 `uname` 输出不是 "Linux"，导致 configure 无法正确识别平台。

**解决方案**：
- configure 生成 config.mk 后，需要手动添加：
  ```
  OBJS += compat_readpassphrase.o
  ```

### 问题2：musl libc 缺少 explicit_bzero
musl libc 不提供 BSD 的 `explicit_bzero` 函数。

**解决方案**：
- 在 config.mk 中添加宏定义：
  ```
  CFLAGS += -D'explicit_bzero(b,l)=__builtin_memset((b),0,(l))'
  ```

### 问题3：静态链接 libtls
libtls 需要依赖 libssl 和 libcrypto，使用 pkg-config 生成的参数会导致动态链接。

**解决方案**：
- 修改 config.mk 的 LDFLAGS：
  ```
  LDFLAGS = -static $(LIBTLS) $(LIBSSL) $(LIBCRYPTO) $(LIBNCURSESW)
  LIBTLS = /storage/Users/currentUser/usr/local/lib/libtls.a
  LIBSSL = /storage/Users/currentUser/usr/local/lib/libssl.a
  LIBCRYPTO = /storage/Users/currentUser/usr/local/lib/libcrypto.a
  LIBNCURSESW = /storage/Users/currentUser/usr/local/lib/libncursesw.a
  ```

## 编译流程建议

```bash
# 1. 配置
./configure --prefix=$HOME/usr/local

# 2. 修改 config.mk（按上述方案）

# 3. 编译
make -j2

# 4. 安装
make install
```
