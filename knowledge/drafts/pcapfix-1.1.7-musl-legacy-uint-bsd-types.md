# pcapfix 1.1.7 — musl 无 legacy BSD u_int*_t 类型（draft）

**Category**: portability | libc | build-system | ohos · **Severity**: 3 · **Tool**: clang/make/conan

## 症状

OHOS/musl 上首次编译即报（glibc 上一路绿灯）：

```text
./pcap.h:44:3: error: unknown type name 'u_int32_t'; did you mean 'uint32_t'?
  u_int32_t incl_len;       /* number of octets of packet saved in file */
  ^~~~~~~~~
```

pcapfix 1.1.7 共 10 处，跨 pcap.c/pcap_kuznet.c/pcapng.c 三个编译单元（2026-09-18
LAN 真机 conan create 实测）。

## 根因

1. glibc 的 `<sys/types.h>`（被 `<arpa/inet.h>` 等常见头间接引入）在 `__USE_MISC`
   下定义 `u_int8_t..u_int64_t`；**musl/OHOS 从不定义**这组 BSD 别名。
2. 老工具在磁盘格式结构体直接写 `u_int32_t`（pcap 系包头结构的标准写法），且只为
   Windows 写了 typedef 兜底（pcapfix.h `#ifdef __WIN32__` 分支），默认非 Windows
   即 glibc。

## 对策

公共头（所有 .c 第一个 include 的头）非 Windows 分支加守卫 typedef 块，守卫排除
`__GLIBC__/__APPLE__/__FreeBSD__/__NetBSD__/__OpenBSD__`（避免重复定义），musl
落入映射。单一 hunk 修复全部编译单元。与 pipebench 0.40（改上游 `#ifdef sun` 块）
同族同解。

```c
#if !defined(__GLIBC__) && !defined(__APPLE__) && !defined(__FreeBSD__) && !defined(__NetBSD__) && !defined(__OpenBSD__)
  typedef uint8_t u_int8_t;
  typedef uint16_t u_int16_t;
  typedef uint32_t u_int32_t;
  typedef uint64_t u_int64_t;
#endif
```

落盘为 `patches/0001-musl-legacy-uint-types.patch`；**别忘了 conanfile build()
要调 `apply_conandata_patches(self)`**（同任务实测教训：漏调则补丁只导出不应用，
编译错误原样复现）。

## 验证

真机 `conan create`（ohos-aarch64）：未打补丁失败 → 打补丁全绿 → test_package
9/9 PASS。
