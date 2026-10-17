/* khronos-api 头文件消费验证：包含 GL 4.6 核心头并断言版本宏 */
#include <khronos-api/GL/glcorearb.h>

#ifndef GL_VERSION_4_6
#error "GL_VERSION_4_6 is not defined (expected OpenGL 4.6 headers)"
#endif

int main(void)
{
    return 0;
}
