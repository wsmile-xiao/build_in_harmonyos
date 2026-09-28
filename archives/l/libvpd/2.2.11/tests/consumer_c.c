// consumer_c.c — 消费者验证（C API，业务上层组件视角）
// 仅使用 libvpd 已安装/导出的公开头文件 (libvpd-2/vpdretriever.h) 与公开
// C API；通过正常链接目标 (libvpd) 编译链接，并在运行时调用公开入口。
// 可观察结果：new_vpdretriever 在无 VPD 数据库的主机上返回 NULL（预期），
// 证明符号已正确链接、函数可被调用执行且无崩溃。
#include <stdio.h>
#include <stdlib.h>

#include <libvpd-2/vpdretriever.h>

int main(void)
{
    struct vpdretriever *r = new_vpdretriever(NULL, NULL);
    if (r != NULL) {
        /* 主机存在 VPD 库时：正常释放 */
        printf("consumer_c: new_vpdretriever -> allocated, freeing\n");
        free_vpdretriever(r);
        printf("consumer_c: free_vpdretriever OK\n");
        return 0;
    }
    /* 主机无 VPD 库（本机无 /var/lib/lsvpd/db）：API 正常返回 NULL 而非崩溃 */
    printf("consumer_c: new_vpdretriever -> NULL as expected (no VPD db on this host)\n");
    return 0;
}