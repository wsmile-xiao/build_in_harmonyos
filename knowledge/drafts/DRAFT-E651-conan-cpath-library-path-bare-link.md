# DRAFT-E651 — Conan 环境下直编上游源码并 -l 系统库名的测试目录必然链接失败

- 软件实证：mustach 1.2.10 test6（test-custom-write）
- 阶段：conan build() 内上游测试（make test 于子目录）
- 日期：2026-09-21

## 现象

mustach 1.2.10 的 test6/Makefile 是"消费者形态"测试：不链接库产物，直接编译
被测源码并对依赖库用裸 `-ljson-c`：

```make
test-custom-write: test-custom-write.c ../mustach-json-c.h ../mustach-json-c.c ...
	$(CC) $(CFLAGS) $(LDFLAGS) -g -o test-custom-write test-custom-write.c \
		../mustach.c ../mustach-json-c.c ../mustach-wrap.c -ljson-c
```

在 Conan 环境下 json-c 的头与库都在 cache 的 package_folder，编译器默认路径
不可见 ⇒ `fatal error: json-c/json.h: No such file or directory` 或
`cannot find -ljson-c`。发行版环境可过、Conan 下必挂，属环境差异而非上游缺陷。

## 修复（不改上游文件）

运行时注入搜索路径（clang 驱动对 CPATH/LIBRARY_PATH 与系统前缀同序处理）：

```python
jsonc = self.dependencies["json-c"]
incdirs = [p if os.path.isabs(p) else os.path.join(jsonc.package_folder, p)
           for p in jsonc.cpp_info.includedirs]
libdirs = [p if os.path.isabs(p) else os.path.join(jsonc.package_folder, p)
           for p in jsonc.cpp_info.libdirs]
self.run("env NOVALGRIND=1 CC='{cc}' CPATH='{cp}' LIBRARY_PATH='{lp}' "
         "mustach='./test-custom-write' make test".format(
             cc=cc, cp=":".join(incdirs), lp=":".join(libdirs)),
         cwd=os.path.join(self.source_folder, "test6"), env="conanbuild")
```

要点：路径来源用 `self.dependencies` 的 `cpp_info`（相对路径拼 package_folder），
不硬编码 `.conan2` 分片目录；CC 用 profile 的 compiler_executables 绝对路径。

## 判据

- 凡上游测试目录满足「直编 `../` 源码 + 裸 `-l<dep>`」形态，配方在 Conan 下
  直接跑 make test 必挂本条错误签名；
- 注入 CPATH/LIBRARY_PATH 后 rc=0 即修复确认。
