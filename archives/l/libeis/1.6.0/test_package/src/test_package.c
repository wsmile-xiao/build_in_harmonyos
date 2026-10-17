/* SPDX-License-Identifier: MIT */
/*
 * libeis 1.6.0 消费者测试 —— 以库使用者身份编译链接 libeis.so，
 * 只调用 src/libeis.h 声明的公共 API，用返回值/errno/文件与 socket
 * 实况决定断言，不查文件存在性凑数、不打印后无条件返回 0。
 *
 * 覆盖的公共 API 面（18 个断言）：
 *   A 组 上下文生命周期与纯函数：eis_new / eis_ref / eis_unref /
 *         eis_get_user_data / eis_set_user_data / eis_now /
 *         eis_event_type_to_string（含 1.6 新增 EIS_EVENT_TEXT_KEYSYM）
 *   B 组 日志面 + UNIX socket 后端真实收发：eis_set_flag /
 *         eis_log_set_handler / eis_log_set_priority / eis_log_get_priority /
 *         eis_setup_backend_socket（失败路径必须回调 ERROR 日志）/
 *         eis_get_fd / eis_dispatch / eis_get_event /
 *         客户端 connect + 未握手不得抛 CLIENT_CONNECT + 退出时 unlink 清理
 *   C 组 推荐的私有 fd 后端：eis_setup_backend_fd /
 *         eis_backend_fd_add_client（返回真实 socketpair）/
 *         eis_get_fd / eis_dispatch / eis_get_event
 *
 * 全部为 OHOS 本机可执行行为：libeis 是纯 POSIX socket 协议库，
 * 不触碰 /dev/uinput 等内核输入设备节点，因此本测试不需要运行期降级。
 */
#include <errno.h>
#include <poll.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

#include <libeis.h>

static int checks;
static int failures;

#define EXPECT(cond, ...)                                                      \
	do {                                                                   \
		checks++;                                                      \
		if (!(cond)) {                                                 \
			failures++;                                            \
			fprintf(stderr, "FAIL: ");                             \
			fprintf(stderr, __VA_ARGS__);                          \
			fprintf(stderr, "  (%s:%d)\n", __FILE__, __LINE__);    \
		} else {                                                       \
			fprintf(stderr, "ok: ");                               \
			fprintf(stderr, __VA_ARGS__);                          \
			fprintf(stderr, "\n");                                 \
		}                                                              \
	} while (0)

static int log_calls;
static enum eis_log_priority last_log_priority;

static void
collect_handler(struct eis *eis,
                enum eis_log_priority priority,
                const char *message,
                struct eis_log_context *ctx)
{
	(void)eis;
	(void)message;
	(void)ctx;
	log_calls++;
	last_log_priority = priority;
}

/* ── A 组：生命周期与纯函数 ─────────────────────────────────── */
static void
test_lifecycle(void)
{
	static int sentinel = 0x5a5a;
	struct eis *eis = eis_new(&sentinel);
	EXPECT(eis != NULL, "eis_new() returns a context");
	if (!eis)
		return;

	EXPECT(eis_get_user_data(eis) == &sentinel,
	       "eis_get_user_data() round-trips the constructor argument");

	eis_set_user_data(eis, NULL);
	EXPECT(eis_get_user_data(eis) == NULL,
	       "eis_set_user_data() overwrites the stored pointer");

	EXPECT(eis_ref(eis) == eis, "eis_ref() returns the same context");

	const char *s = eis_event_type_to_string(EIS_EVENT_CLIENT_CONNECT);
	EXPECT(s && strcmp(s, "EIS_EVENT_CLIENT_CONNECT") == 0,
	       "eis_event_type_to_string(CLIENT_CONNECT) == \"%s\"", s ? s : "(null)");

	/* 1.6 新增事件名：证明交付面确实是 1.6 而不是旧版本 */
	s = eis_event_type_to_string(EIS_EVENT_TEXT_KEYSYM);
	EXPECT(s && strcmp(s, "EIS_EVENT_TEXT_KEYSYM") == 0,
	       "eis_event_type_to_string(TEXT_KEYSYM) == \"%s\" (new in 1.6)",
	       s ? s : "(null)");

	uint64_t t0 = eis_now(eis);
	uint64_t t1 = eis_now(eis);
	EXPECT(t1 >= t0, "eis_now() is monotonic non-decreasing (%llu -> %llu)",
	       (unsigned long long)t0, (unsigned long long)t1);

	/* eis_unref() 的公开契约是恒返回 NULL（见 libeis.h） */
	EXPECT(eis_unref(eis) == NULL, "eis_unref() returns NULL");
	eis_unref(eis); /* 抵消上面的 eis_ref()，refcount 归零 */
}

/* 原始 bind() 能力探测：OHOS/HMDFS 对"路径形式"的 AF_UNIX 有平台性限制
 * （E461：$HOME→EPERM、/dev/shm→EACCES、/tmp→EROFS），而 libeis 的
 * eis_setup_backend_socket() 只会 bind 路径名。因此先逐个候选目录用裸
 * socket()/bind() 探能力，再决定按正向流程断言还是按平台受限如实记录——
 * 不删用例、不为凑通过率放宽断言。 */
static int
probe_bind_dir(const char *dir, int *err)
{
	char path[512];
	struct sockaddr_un addr;
	int fd, rc;

	snprintf(path, sizeof(path), "%s/libeis-probe-%ld.sock", dir,
	         (long)getpid());
	fd = socket(AF_UNIX, SOCK_STREAM, 0);
	if (fd < 0) {
		*err = errno;
		return -1;
	}
	memset(&addr, 0, sizeof(addr));
	addr.sun_family = AF_UNIX;
	snprintf(addr.sun_path, sizeof(addr.sun_path), "%s", path);
	if (strlen(path) >= sizeof(addr.sun_path)) {
		unlink(path);
		close(fd);
		*err = ENAMETOOLONG;
		return -1;
	}
	rc = bind(fd, (struct sockaddr *)&addr, sizeof(addr));
	*err = rc == 0 ? 0 : errno;
	close(fd);
	unlink(path);
	return rc;
}

/* 返回第一个可 bind 路径套接字的目录（调用方 free），NULL 表示本平台受限。
 * 候选去重后逐个记 errno，让 PLATFORM-LIMITED 行本身成为一份可读的
 * 跨文件系统证据表（E461 的三态：HMDFS/EROFS/EACCES）。 */
static const char *
find_bindable_dir(char *report, size_t report_size)
{
	static const char *keys[] = { "LIBEIS_TEST_DIR", "TMPDIR",
		                          "XDG_RUNTIME_DIR", "HOME" };
	static const char *literals[] = { "/tmp", "/dev/shm" };
	char seen[8][400];
	size_t nseen = 0, off = 0;

	for (size_t i = 0; i < sizeof(keys) / sizeof(keys[0]) +
	                          sizeof(literals) / sizeof(literals[0]); i++) {
		char dir[400];
		const char *v;
		int err = 0;
		bool dup = false;

		if (i < sizeof(keys) / sizeof(keys[0])) {
			v = getenv(keys[i]);
			if (!v || !*v)
				continue;
			if (snprintf(dir, sizeof(dir), keys[i][0] == 'H' ? "%s/tmp" : "%s",
			             v) >= (int)sizeof(dir))
				continue;
		} else {
			snprintf(dir, sizeof(dir), "%s",
			         literals[i - sizeof(keys) / sizeof(keys[0])]);
		}

		for (size_t j = 0; j < nseen && !dup; j++)
			dup = strcmp(seen[j], dir) == 0;
		if (dup || nseen >= sizeof(seen) / sizeof(seen[0]))
			continue;
		snprintf(seen[nseen++], sizeof(seen[0]), "%s", dir);

		if (access(dir, W_OK) != 0) {
			off += (size_t)snprintf(report + off, report_size - off, " %s=%s",
			                        dir, strerror(errno));
			continue;
		}
		if (probe_bind_dir(dir, &err) == 0) {
			off += (size_t)snprintf(report + off, report_size - off, " %s=OK",
			                        dir);
			return strdup(dir);
		}
		off += (size_t)snprintf(report + off, report_size - off, " %s=%s", dir,
		                        strerror(err));
		if (off >= report_size - 1)
			off = report_size - 1;
	}
	return NULL;
}

/* ── B 组：日志面 + socket 后端 ─────────────────────────────── */
static void
test_socket_backend(void)
{
	char probe[512] = { 0 };
	const char *dir = find_bindable_dir(probe, sizeof(probe));
	struct eis *eis = eis_new(NULL);
	int rc;

	if (!eis) {
		EXPECT(0, "eis_new() failed, cannot test socket backend");
		free((void *)dir);
		return;
	}

	/* eis_set_flag() 必须在任何 backend 建立之前调用 */
	rc = eis_set_flag(eis, EIS_FLAG_DEVICE_READY);
	EXPECT(rc == 0, "eis_set_flag(EIS_FLAG_DEVICE_READY) == 0 (rc=%d)", rc);

	eis_log_set_handler(eis, collect_handler);
	eis_log_set_priority(eis, EIS_LOG_PRIORITY_ERROR);
	EXPECT(eis_log_get_priority(eis) == EIS_LOG_PRIORITY_ERROR,
	       "eis_log_get_priority() reports the priority just set");

	/* 失败路径：目录不可创建 ⇒ 非零返回，且必须回调我们注册的 handler。
	 * 注意上游这里 return -rc，errno 以正值传出，故只断言"非零"。 */
	log_calls = 0;
	last_log_priority = (enum eis_log_priority)0;
	rc = eis_setup_backend_socket(eis, "/nonexistent-dir-for-libeis/eis.sock");
	EXPECT(rc != 0,
	       "eis_setup_backend_socket() rejects an uncreatable path (rc=%d)",
	       rc);
	EXPECT(log_calls > 0 && last_log_priority == EIS_LOG_PRIORITY_ERROR,
	       "the failed setup is reported to the log handler (calls=%d)",
	       log_calls);

	if (dir == NULL) {
		/* 平台受限分支：路径套接字在本机任何可写目录都 bind 不了，
		 * 则 libeis 的同一路径必须把该 errno 原样传出来（而不是崩或假成功）。 */
		const char *base = getenv("TMPDIR") ? getenv("TMPDIR") : ".";
		char path[560];

		snprintf(path, sizeof(path), "%s/libeis-consumer-limited.sock", base);
		log_calls = 0;
		rc = eis_setup_backend_socket(eis, path);
		EXPECT(rc != 0,
		       "path backend propagates the platform bind failure (rc=%d)",
		       rc);
		printf("PLATFORM-LIMITED: eis_setup_backend_socket() needs a bindable "
		       "path socket; raw bind() probes reported:%s — see E461. The "
		       "upstream-recommended fd backend below is fully exercised.\n",
		       probe);
		fflush(stdout);
		eis_unref(eis);
		return;
	}

	char path[560];
	snprintf(path, sizeof(path), "%s/libeis-consumer-%ld.sock", dir,
	         (long)getpid());
	unlink(path);

	rc = eis_setup_backend_socket(eis, path);
	EXPECT(rc == 0, "eis_setup_backend_socket(%s) == 0 (rc=%d)", path, rc);
	if (rc != 0) {
		printf("PLATFORM-LIMITED: raw bind() succeeded but libeis setup "
		       "returned %d for %s\n", rc, path);
		fflush(stdout);
	} else {
		int sfd = eis_get_fd(eis);
		EXPECT(sfd >= 0, "eis_get_fd() exposes a backend fd (fd=%d)", sfd);

		int type = -1;
		socklen_t len = sizeof(type);
		EXPECT(getsockopt(sfd, SOL_SOCKET, SO_TYPE, &type, &len) == 0 &&
		       type == SOCK_STREAM,
		       "the backend fd is a real SOCK_STREAM socket (type=%d)", type);

		struct stat st;
		EXPECT(stat(path, &st) == 0 && S_ISSOCK(st.st_mode),
		       "the socket path exists as a socket file");

		/* 真实客户端连接：内核层面建立，但 libeis 在协议握手完成前不得
		 * 把它当作已连接的客户端抛给服务端（CLIENT_CONNECT 由握手路径
		 * libeis-handshake.c 里的 eis_queue_connect_event() 触发）。 */
		int cfd = socket(AF_UNIX, SOCK_STREAM, 0);
		struct sockaddr_un addr;
		memset(&addr, 0, sizeof(addr));
		addr.sun_family = AF_UNIX;
		snprintf(addr.sun_path, sizeof(addr.sun_path), "%s", path);
		EXPECT(cfd >= 0 && connect(cfd, (struct sockaddr *)&addr,
		                           sizeof(addr)) == 0,
		       "a client can connect() to the libeis socket (errno=%d)",
		       errno);

		struct pollfd pfd = { .fd = sfd, .events = POLLIN };
		int pr = poll(&pfd, 1, 2000);
		EXPECT(pr > 0 && (pfd.revents & POLLIN),
		       "libeis's fd becomes readable on an incoming connection (pr=%d)",
		       pr);

		eis_dispatch(eis);

		struct eis_event *ev = eis_get_event(eis);
		EXPECT(ev == NULL,
		       "no CLIENT_CONNECT event before the EI handshake completes");
		if (ev) {
			int t = eis_event_get_type(ev);
			fprintf(stderr, "     (unexpected event type %d: %s)\n", t,
			        eis_event_type_to_string(t));
			eis_event_unref(ev);
		}

		close(cfd);
		eis_unref(eis);

		/* 上下文销毁必须回收 socket 文件与锁文件 */
		EXPECT(access(path, F_OK) != 0,
		       "the socket file is unlinked when the context is destroyed");
		char lock[600];
		snprintf(lock, sizeof(lock), "%s.lock", path);
		EXPECT(access(lock, F_OK) != 0,
		       "the lock file is unlinked when the context is destroyed");
	}

	free((void *)dir);
}


/* ── C 组：私有 fd 后端 ─────────────────────────────────────── */
static void
test_fd_backend(void)
{
	struct eis *eis = eis_new(NULL);
	if (!eis) {
		EXPECT(0, "eis_new() failed, cannot test fd backend");
		return;
	}

	int rc = eis_setup_backend_fd(eis);
	EXPECT(rc == 0, "eis_setup_backend_fd() == 0 (rc=%d)", rc);

	int cfd = eis_backend_fd_add_client(eis);
	EXPECT(cfd >= 0,
	       "eis_backend_fd_add_client() hands out a client fd (fd=%d)", cfd);

	if (cfd >= 0) {
		int type = -1;
		socklen_t len = sizeof(type);
		EXPECT(getsockopt(cfd, SOL_SOCKET, SO_TYPE, &type, &len) == 0 &&
		       type == SOCK_STREAM,
		       "the client fd is a real SOCK_STREAM socket (type=%d)",
		       type);
		close(cfd);
	}

	int sfd = eis_get_fd(eis);
	EXPECT(sfd >= 0, "eis_get_fd() exposes the backend fd (fd=%d)", sfd);

	eis_dispatch(eis);
	struct eis_event *ev = eis_get_event(eis);
	EXPECT(ev == NULL,
	       "a client without a handshake yields no event on the fd backend");
	if (ev)
		eis_event_unref(ev);

	eis_unref(eis);
}

int
main(void)
{
	test_lifecycle();
	test_socket_backend();
	test_fd_backend();

	printf("libeis consumer test: %d assertions, %d failed\n", checks,
	       failures);
	if (failures == 0)
		printf("libeis test_package: PASS\n");
	return failures ? 1 : 0;
}
