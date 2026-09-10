#include <epoxy/gl.h>
#include <stdio.h>

int main(void) {
    /* R40 标注（需人工确认适配完整性）：libepoxy 属「图形/渲染」领域（OpenGL/EGL
     * 函数指针分发库）。OHOS 无 OpenGL 库（libGL.so.1 / libOpenGL.so.0 均不存在），
     * epoxy_gl_version() 会在运行期 dlopen GL 库失败并 abort（Signal 6），故测试仅
     * 覆盖「头文件可编译 + 链接可行 + 字符串工具可运行」最小子集，未覆盖 GL dispatch
     * 查表、EGL/GLX dispatch 核心路径（OHOS 无窗口系统下不可行）。若后续 OHOS 引入
     * EGL 支持，需补充实际 GL context 创建与函数指针查询测试并更新本标注。
     * 当前用纯字符串解析函数 epoxy_extension_in_string()——只遍历扩展名字符串，
     * 不触碰 GL 库符号，可真实验证 libepoxy 可链接、核心分发表字符串路径可用。 */
    if (!epoxy_extension_in_string("GL_EXT_texture GL_ARB_multitexture",
                                   "GL_ARB_multitexture")) {
        fprintf(stderr, "FAIL: extension not found in list\n");
        return 1;
    }
    if (epoxy_extension_in_string("GL_EXT_texture GL_ARB_multitexture",
                                  "GL_ARB_framebuffer_object")) {
        fprintf(stderr, "FAIL: absent extension reported as present\n");
        return 1;
    }
    return 0;
}
