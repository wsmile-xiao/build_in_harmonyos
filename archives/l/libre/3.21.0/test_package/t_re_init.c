#include <re.h>
#include <unistd.h>
#include "_check.h"

static void fdhandler(int flags, void *arg)
{
	unsigned *seen = arg;
	*seen |= (unsigned)flags;
}

int main(void)
{
	unsigned seen = 0;
	struct re_fhs *fhs = NULL;
	int fd;

	CHECK(libre_init() == 0);
	CHECK(fd_setsize(64) == 0);
	CHECK(re_nfds() >= 0);

	/* 注册描述符句柄并关闭，验证事件循环句柄生命周期 */
	fd = socket(AF_INET, SOCK_DGRAM, 0);
	CHECK(fd >= 0);
	if (fd >= 0) {
		CHECK(fd_listen(&fhs, fd, FD_READ, fdhandler, &seen) == 0);
		CHECK(fhs != NULL);
		fhs = fd_close(fhs);
		CHECK(fhs == NULL);
		CHECK(seen == 0);
		(void)close(fd);
	}

	libre_close();

	return errors ? 1 : 0;
}
