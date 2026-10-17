#include <stdint.h>
#include <fcntl.h>

#include <libv4l2.h>

int main(void)
{
    void *close_fn = (void *)(uintptr_t)&v4l2_close;
    void *ioctl_fn = (void *)(uintptr_t)&v4l2_ioctl;
    void *mmap_fn = (void *)(uintptr_t)&v4l2_mmap;
    int fd;

    if (close_fn == NULL || ioctl_fn == NULL || mmap_fn == NULL) {
        return 1;
    }

    fd = v4l2_open("/dev/null", O_RDONLY);
    if (fd >= 0) {
        v4l2_close(fd);
        return 1;
    }

    return 0;
}
