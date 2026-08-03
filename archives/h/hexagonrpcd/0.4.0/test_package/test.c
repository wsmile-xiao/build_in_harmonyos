#include <libhexagonrpc/fastrpc.h>
#include <stdio.h>

int main(void)
{
	struct fastrpc_context *ctx = fastrpc_create_context(-1, 0);
	if (ctx == NULL) {
		fprintf(stderr, "fastrpc_create_context returned NULL\n");
		return 1;
	}
	if (ctx->fd != -1 || ctx->handle != 0) {
		fprintf(stderr, "unexpected context fields (fd=%d handle=%u)\n",
			ctx->fd, ctx->handle);
		return 1;
	}
	fastrpc_destroy_context(ctx);
	printf("hexagonrpcd: fastrpc context API OK\n");
	return 0;
}
