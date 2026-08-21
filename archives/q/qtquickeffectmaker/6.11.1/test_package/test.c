/* test_package/test.c — qtquickeffectmaker 6.11.1 consumer test
 *
 * 上游 qtquickeffectmaker 不产出 C++ 链接库（src/ 仅 doc，安装产物为
 * qqem 应用 + QML 节点资源，无 libQt6QuickEffectMaker.so 与
 * Qt6QuickEffectMakerConfig.cmake），故消费者测试为应用级验证：
 *   1) qqem 可执行文件存在（--help 由 conanfile.py test() 运行）；
 *   2) QML 节点资源目录随包安装。
 * 本 C 源文件为 L0c（test_package 必须有测试源文件）提供编译/链接验证
 * 载体：编译一个最小可执行程序（不依赖上游库）。
 */
#include <stdio.h>

int main(void) {
    printf("qtquickeffectmaker 6.11.1 consumer test (app-level)\n");
    return 0;
}
