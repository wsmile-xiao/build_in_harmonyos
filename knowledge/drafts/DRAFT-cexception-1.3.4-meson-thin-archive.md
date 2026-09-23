# DRAFT-cexception-1.3.4：Meson thin archive 的 Conan 自包含打包

## 背景

cexception 1.3.4 的上游 Meson 文件只声明 static_library()，没有 install()
规则。首次 recipe 直接复制 Meson 输出的 libcexception.a 后，库本体构建成功，
但 test_package 独立链接失败：

    ld.lld: error: .../libcexception.a: could not get the buffer for a child of
    the archive: libcexception.a.p/CException.c.o: No such file or directory

llvm-ar -t 显示该归档的成员是构建目录下的相对对象路径，说明它是 thin archive。
复制 .a 文件本身不会复制成员对象。

## 通用修复

1. 在 package() 中定位唯一的 lib*.a 和对应的 .p/*.o 成员。
2. 将对象复制到临时目录。
3. 用目标工具链的 llvm-ar rcs 生成普通、自包含归档。
4. 将新归档放入 package_folder/lib，再复制头文件和许可证。
5. 让 test_package 在独立 Conan 环境中执行真实链接和 CTest，不能只检查归档
   文件存在。

cexception 的 Release 和 Debug Conan create 均通过，消费者测试均为 1/1
CTest passed。这个草稿只描述可迁移的打包边界，不声称所有 Meson 项目都生成
thin archive；package() 应先通过成员路径和链接结果确认。

## OHOS CI 的 Meson 归档工具路径

OHOS CI 可能通过 tools.build:compiler_executables 提供绝对 clang 路径，
但运行环境的 PATH 不包含 /data/service/hnp/bin。此时仅设置编译器仍会让
Meson 在配置阶段报 Unknown linker(s): [['llvm-ar']]。通用做法是在
MesonToolchain.generate() 后读取 compiler conf，从 C 编译器同目录推导
llvm-ar（以及存在时的 llvm-ranlib），把绝对路径写入生成的
conan_meson_native.ini/conan_meson_cross.ini 的 [binaries] 段，再运行
Meson configure。应在 CI 复现中检查 machine file 和完整配置日志；不能把本机
PATH 中恰好存在工具误认为 CI 一定可见。
