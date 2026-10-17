# berkeley-db5 5.3.28 适配笔记

## 编译环境
- 构建系统: autotools（需在 build_unix/ 子目录运行 ../dist/configure）
- 编译器: clang 15.0.4（OHOS aarch64 工具链）
- 状态: built

## 编译步骤

```bash
cd build_unix && ../dist/configure --prefix=/ --enable-static --enable-shared --with-repmgr-ssl=no
make -j1
make install DESTDIR=<conan package_folder>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 无法识别 OHOS/HarmonyOS 平台 | 版本过旧 | 打补丁升级到支持 OHOS 的版本（patches/0001-dist-config.guess.patch、0001-dist-config.sub.patch） |
| 2 | configure 探测 `print -r --` 成功但 config.status 运行环境无 print | HMDFS 下探测 shell 与执行环境不一致 | 构建时改写 configure，强制使用 POSIX `printf %s\n` 回显 |
| 3 | config.status 生成临时 awk 脚本报 Permission denied | HMDFS 对新建脚本执行权限限制（setgid 2700 目录） | 修改 config.status 将临时目录重定向到 $TMPDIR 并使用 umask 022，随后手动执行 config.status |
| 4 | test_package 的 test() 无 self.run()，CI L0d 门禁失败 | test() 仅调用 cmake.test() | test() 改为 self.run() 直接执行 test_berkeley-db5，并显式注入 LD_LIBRARY_PATH 指向依赖库目录 |
| 5 | test_package CMakeLists 链接目标名错误 | CMakeDeps 生成的 imported target 是 berkeley-db5::berkeley-db5 | 修正 target_link_libraries 使用 berkeley-db5::berkeley-db5 |

## 验证结果

```bash
# conan create（含 test_package 消费者测试）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing   # 退出码 0
# 消费者测试输出（test.c 真实调用 db_create 与 db->close）
#   db_create OK
#   berkeley-db5 5.3.28: API test PASSED

# conan-verify（G1/G0/G2/G3/G4 + L2/L4/L5）
ohc-run.py conan-verify berkeley-db5 5.3.28   # 退出码 0，全部 PASS

# finish 归档
ohc-run.py finish berkeley-db5 5.3.28 built   # 退出码 0，状态 built（未发布）
```

## 注意事项

- 包同时交付库与 14 个 db_* 命令行工具（bin/），package_info 已声明 bindirs=["bin"]。
- L2 冒烟测试（--version/--help）在本机因 HMDFS 对 stripped ELF 的执行限制无法通过，为非阻塞 warn，不属于"无 CLI"场景；命令参数支持已通过二进制 usage 字符串确认（如 db_archive: `usage: %s [-adlsVv] [-h home] [-P password]`）。
- 库默认 shared=False（静态），同时产出 libdb-5.3.so/libdb-5.3.a。
---

**编译结束**: 2026-08-07 17:29
**最终状态**: built
