# DRAFT-7939-gpgmepy-python-ext-selfsign-hmdfs

## Python C 扩展自签名适配 HMDFS dlopen

### 问题

Conan 打包的 Python C 扩展 .so 在 HMDFS 上 dlopen 失败，报签名错误。

### 根因

Conan copy() 对 ELF 文件做字节级复制时修改偏移量，破坏原有代码签名。HMDFS 要求所有 .so 必须有有效签名，签名失效后 dlopen 返回 EPERM。

### 处理方法

在 package() 中 copy 完成后，对目标 .so 执行：(1) llvm-objcopy --remove-section .codesign 清除旧签名，(2) binary-sign-tool sign -selfSign 1 重新自签名，(3) chmod 755 恢复权限。

### 落地

gpgmepy 2.0.0 配方 package() 中对 _gpgme*.so 执行自签名。

### 适用范围

所有在 OHOS HMDFS 上运行的 Conan 打包 Python C 扩展（lxml、pycairo 等同理）。与 E212 同属 HMDFS 签名问题。
