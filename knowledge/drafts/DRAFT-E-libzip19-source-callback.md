# DRAFT: libzip ≥ 1.9 zip source 回调协议不兼容（ZIP_ER_OPNOTSUPP）

## 现象

消费者库（如 lib3mf 1.8.1）从老 libzip 迁到 libzip 1.11.x 后，通过
`zip_source_function_create` + `zip_open_from_source` 读 zip 包失败：

```
zip_open_from_source 返回 NULL，zip_err=28 (ZIP_ER_OPNOTSUPP)
```

若回调 default 分支抛异常（lib3mf 的 CNMRException），则直接 abort：
`libc++abi: terminating due to uncaught exception of type NMR::CNMRException: Error in libzip callback.`

写路径（`zip_open` 文件名直开）不受影响，**只断在读路径**——容易误判为文件损坏。

## 根因

老代码（libzip < 1.9 时代）手工拼能力位图：

```c
case ZIP_SOURCE_SUPPORTS:
    bitmap = zip_source_make_command_bitmap(ZIP_SOURCE_OPEN, ZIP_SOURCE_READ,
        ZIP_SOURCE_CLOSE, ZIP_SOURCE_STAT, ZIP_SOURCE_ERROR,
        ZIP_SOURCE_SEEK, ZIP_SOURCE_TELL, ZIP_SOURCE_SUPPORTS, -1);
    return bitmap;
...
default:
    throw ...;  /* 或 return -1 */
```

libzip ≥ 1.9 的 `zip_open_from_source` 需要位图含更多命令位（官方
`ZIP_SOURCE_SUPPORTS_SEEKABLE` 宏才齐），老位图差位 → open 直接报 28。
且新 libzip 会向回调下发 `ZIP_SOURCE_GET_FILE_ATTRIBUTES`、
`ZIP_SOURCE_ACCEPT_EMPTY` 等新命令，default 抛异常 → 运行期崩溃。

## 修复

```c
case ZIP_SOURCE_SUPPORTS:
    /* use the official capability mask */
    return ZIP_SOURCE_SUPPORTS_SEEKABLE;
...
default:
    return 0;   /* unhandled commands: benign */
```

实测（HarmonyOS PC aarch64，libzip 1.11.4）：修复后 zip 读回完整恢复。

## 适用范围

任何含自写 zip source 回调且从 libzip < 1.9 升到 ≥ 1.9 的消费者库
（lib3mf 系、OPC/OOXML 读取器等）。修复点是**消费者回调**，不是 libzip。

## 验证

- CI 构建：#46345（PR #9877，lib3mf 1.8.1 适配）
- 本机消费者往返测试：模型写 3MF → 读回 → 顶点/三角形数校验 5/5 通过
