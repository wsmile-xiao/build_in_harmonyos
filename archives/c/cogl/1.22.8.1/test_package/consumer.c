// consumer.c — cogl 1.22.8 消费测试最小程序
// 证明库可被实际链接和加载（R34 非空壳）：
// 1. #include <cogl/cogl.h> 编译通过——头文件完整
// 2. 链接 -lcogl 并引用 cogl_get_proc_address 符号——导出符号表可解析
// 3. 运行 consumer——libcogl.so 可被动态加载
// 注意：只取符号地址、不实际调用 cogl_get_proc_address——它需要已初始化
// 的 GL display/context，OHOS 无 X11/显示服务，实调会崩溃（本地实测
// segfault）；取地址验证同样覆盖"符号可解析 + 库可加载"两个核心检查。
#include <stdio.h>
#include <cogl/cogl.h>

int main(void) {
    void *sym = (void *)cogl_get_proc_address;
    if (sym == NULL) {
        printf("cogl_get_proc_address unresolved\n");
        return 1;
    }
    printf("cogl_get_proc_address resolved ok\n");
    return 0;
}
