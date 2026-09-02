/* test_package/test.cpp — libsoup 3.6.5 consumer test (R34 合规)
 *
 * L1 test:
 * 1. 编译并链接 libsoup-3.0（含头文件与库）；
 * 2. SOUP_CHECK_VERSION(3,6,5) 编译期版本检查——真实头文件/库可用
 *    验证。
 */
#include <libsoup/soup.h>
#include <cstdio>

int main() {
    /* 编译期版本检查：库版本 >= 3.6.5（宏，无需链接） */
#if !SOUP_CHECK_VERSION(3, 6, 5)
#error "libsoup version too old (need >= 3.6.5)"
#endif
    /* 运行时验证：创建 SoupSession 并获取其 GType（真实链接验证） */
    GType session_type = SOUP_TYPE_SESSION;
    if (session_type == 0) {
        std::printf("libsoup 3.6.5 consumer test FAILED: "
                    "SOUP_TYPE_SESSION is 0\n");
        return 1;
    }
    std::printf("libsoup 3.6.5 consumer test OK (SOUP_CHECK_VERSION "
                "3.6.5, SOUP_TYPE_SESSION=%lu)\n",
                (unsigned long)session_type);
    return 0;
}
