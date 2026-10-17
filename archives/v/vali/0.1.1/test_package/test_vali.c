/*
 * test_vali.c — vali/0.1.1 的消费者用例（installed-package consumer test）
 *
 * 目的：以"库的使用者"身份，只用 vali 对外公开的 API（include/vali.h）跑一次
 * 真实的 Varlink 往返通信。不依赖任何代码生成器产物 —— 方法名与 JSON 报文都
 * 由本文件手工构造，因此它验证的是"链接出来的 libvali 真能收发 Varlink 报文"，
 * 而不是"生成的桩代码能编译"。
 *
 * 覆盖点：
 *   1. 成功路径：client → service 的请求/回复往返，JSON 参数与结果逐字段核对
 *   2. 错误路径：服务端 close_with_error 后客户端拿到 vali_error.name，并可用
 *      vali_error_finish() 释放
 *   3. 单向调用：vali_client_call_oneway() 不被回复阻塞，且随后仍能正常发下一次
 *      请求（服务端对 oneway 调用必须丢弃回复体）
 *   4. 多回复（streaming）：vali_client_call_more() + vali_client_call_wait() 循环，
 *      直到 vali_client_call_is_done() 为真
 *      ⚠️ vali.h 里 vali_client_call_more() 的文档注释说"while
 *      vali_client_call_has_more() returns true" —— 这个函数**在头文件里根本不存在**
 *      （只有 vali_client_call_is_done / vali_client_call_wait /
 *        vali_client_call_destroy）。文档注释是陈旧的，以声明为准。
 *   5. 生命周期：service/conn/client/registry 的创建与销毁、fork 出的服务子进程
 *      正常退出（WIFEXITED && WEXITSTATUS == 0）
 *   6. vali_error_finish() 的契约：它**不是幂等**的（不置零字段），
 *      对同一结构体连调两次会 double free；只能对零值安全调用
 *
 * ── 为什么不用 assert() ──
 * CMake 的 Release 配置（以及任何定义了 NDEBUG 的构建）会把 assert() 预处理成
 * 空语句，测试会退化成"必然通过"的假测试 —— CI 的 L1e 破坏性反向验证专门针对
 * 这种情况。所以这里自研 CHECK / CHECK_STREQ 宏：任何构建配置下都真实生效，
 * 失败会打印文件:行号并累计，最后由 main() 用非 0 退出码上报。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>

#include <vali.h>
/* json-c 的头装在 <prefix>/include/json-c/ 下；公共 API 用的是
 * <json-c/json.h> 这个"带目录前缀"的规范路径，而不是发行版才有的顶层兼容头
 * <json_object.h>（详见 archives/v/vali/0.1.1/notes.md §3.2）。 */
#include <json-c/json.h>

/* ── 自研断言宏（NDEBUG 无关）────────────────────────────────────────── */
static int checks_run = 0;
static int checks_failed = 0;

#define CHECK(cond)                                                          \
	do {                                                                     \
		checks_run++;                                                        \
		if (!(cond)) {                                                       \
			checks_failed++;                                                 \
			fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);  \
		}                                                                    \
	} while (0)

#define CHECK_STREQ(actual, expected)                                        \
	do {                                                                     \
		const char *_a = (actual);                                           \
		const char *_e = (expected);                                         \
		checks_run++;                                                        \
		if (_a == NULL || _e == NULL || strcmp(_a, _e) != 0) {               \
			checks_failed++;                                                 \
			fprintf(stderr, "FAIL %s:%d: %s == %s (\"%s\" vs \"%s\")\n",     \
			        __FILE__, __LINE__, #actual, #expected,                  \
			        _a != NULL ? _a : "(null)", _e != NULL ? _e : "(null)"); \
		}                                                                    \
	} while (0)

/* ── 服务端（跑在 fork 出来的子进程里）────────────────────────────────── */
static bool service_running = true;

static const char *ECHO_METHOD = "org.example.test.Echo";
static const char *COUNT_METHOD = "org.example.test.Count";
static const char *STOP_METHOD = "org.example.test.Stop";
static const char *UNKNOWN_ERROR = "org.example.test.UnknownMethod";

static void on_call(struct vali_service_call *call, void *user_data) {
	(void)user_data;
	const char *method = vali_service_call_get_method(call);
	struct json_object *params = vali_service_call_get_parameters(call);

	if (method != NULL && strcmp(method, ECHO_METHOD) == 0) {
		/* 把入参里的 name 原样回显，便于客户端核对报文真的走通了 */
		const char *name = NULL;
		if (params != NULL) {
			struct json_object *value = NULL;
			if (json_object_object_get_ex(params, "name", &value)) {
				name = json_object_get_string(value);
			}
		}
		struct json_object *reply = json_object_new_object();
		json_object_object_add(reply, "echo",
		                       json_object_new_string(name != NULL ? name : ""));
		/* 顺带把"这次调用是不是 oneway"告诉客户端，作为服务端视角的证据 */
		json_object_object_add(reply, "oneway",
		                       json_object_new_boolean(vali_service_call_is_oneway(call)));
		vali_service_call_close_with_reply(call, reply);
	} else if (method != NULL && strcmp(method, COUNT_METHOD) == 0) {
		if (!vali_service_call_is_more(call)) {
			/* 客户端没有要求多回复：只能一次性回完 */
			vali_service_call_close_with_reply(call, NULL);
			return;
		}
		int upto = 0;
		if (params != NULL) {
			struct json_object *value = NULL;
			if (json_object_object_get_ex(params, "n", &value)) {
				upto = json_object_get_int(value);
			}
		}
		for (int i = 0; i <= upto; i++) {
			struct json_object *item = json_object_new_object();
			json_object_object_add(item, "n", json_object_new_int(i));
			if (i == upto) {
				vali_service_call_close_with_reply(call, item);
			} else {
				vali_service_call_reply(call, item);
			}
		}
	} else if (method != NULL && strcmp(method, STOP_METHOD) == 0) {
		service_running = false;
		vali_service_call_close_with_reply(call, NULL);
	} else {
		vali_service_call_close_with_error(call, UNKNOWN_ERROR, NULL);
	}
}

/* 子进程：在给定的 FD 上跑服务端事件循环，直到收到 Stop */
static void run_service(int fd) {
	struct vali_service *service = vali_service_create();
	if (service == NULL) {
		_exit(1);
	}

	const struct vali_service_call_handler handler = {
		.func = on_call,
		.user_data = NULL,
	};
	vali_service_set_call_handler(service, handler);

	struct vali_service_conn *conn = vali_service_create_conn(service, fd);
	if (conn == NULL) {
		_exit(1);
	}

	while (service_running && vali_service_dispatch(service)) {
		/* 事件循环由本进程驱动：vali 只提供 dispatch，不接管线程 */
	}
	vali_service_dispatch(service); /* 把最后一次回复刷出去 */

	vali_service_destroy(service);
	_exit(0);
}

/* ── 客户端（跑在主进程里）───────────────────────────────────────────── */
static void test_echo_and_error(struct vali_client *client) {
	/* 1) 成功路径：带参数调用，核对回显与 oneway 标记 */
	struct json_object *in = json_object_new_object();
	json_object_object_add(in, "name", json_object_new_string("ohos-vali"));
	struct json_object *out = NULL;
	struct vali_error err = {0};

	CHECK(vali_client_call(client, ECHO_METHOD, in, &out, &err));
	CHECK(err.name == NULL);
	CHECK(out != NULL);
	if (out != NULL) {
		struct json_object *echo = NULL;
		if (json_object_object_get_ex(out, "echo", &echo)) {
			CHECK_STREQ(json_object_get_string(echo), "ohos-vali");
		} else {
			CHECK(0);
		}
		struct json_object *oneway = NULL;
		if (json_object_object_get_ex(out, "oneway", &oneway)) {
			CHECK(json_object_get_boolean(oneway) == 0);
		} else {
			CHECK(0);
		}
		json_object_put(out);
	}

	/* 2) 错误路径：服务端 close_with_error，客户端应拿到错误名而不是崩溃 */
	struct vali_error call_err = {0};
	CHECK(!vali_client_call(client, "org.example.test.Nope", NULL, NULL, &call_err));
	CHECK_STREQ(call_err.name, UNKNOWN_ERROR);
	vali_error_finish(&call_err);
	/* ★ vali_error_finish() 不是幂等的：实现是
	 *     free(err->name); json_object_put(err->parameters);
	 * 它**不把字段置零**（client.c:167），所以对同一个结构体连调两次就是
	 * double free。头文件那句 "can be called safely on a zero error" 说的是
	 * "对零值结构安全"，不是"可重复调用安全"。复用前必须自己清零。
	 * 这里同时验证这条契约：清零后再调一次不应崩。 */
	call_err = (struct vali_error){0};
	vali_error_finish(&call_err);
}

static void test_oneway(struct vali_client *client) {
	/* 单向调用：不需要回复，返回即成功 */
	struct json_object *in = json_object_new_object();
	json_object_object_add(in, "name", json_object_new_string("fire-and-forget"));
	CHECK(vali_client_call_oneway(client, ECHO_METHOD, in));

	/* 紧接着再发一次普通调用：若服务端错误地回复了 oneway 请求，
	 * 客户端的 reply 匹配就会错位，这里会立刻暴露 */
	struct json_object *out = NULL;
	struct vali_error err = {0};
	CHECK(vali_client_call(client, ECHO_METHOD, NULL, &out, &err));
	CHECK(out != NULL);
	if (out != NULL) {
		struct json_object *echo = NULL;
		if (json_object_object_get_ex(out, "echo", &echo)) {
			/* 入参为 NULL ⇒ 服务端回显空串 */
			CHECK_STREQ(json_object_get_string(echo), "");
		} else {
			CHECK(0);
		}
		json_object_put(out);
	}
	vali_error_finish(&err);
}

static void test_more_replies(struct vali_client *client) {
	/* 多回复（streaming）：vali_client_call_more + vali_client_call_wait 循环 */
	struct json_object *in = json_object_new_object();
	json_object_object_add(in, "n", json_object_new_int(3));

	struct vali_client_call *call = vali_client_call_more(client, COUNT_METHOD, in);
	CHECK(call != NULL);
	if (call == NULL) {
		return;
	}

	for (int i = 0; i <= 3; i++) {
		CHECK(!vali_client_call_is_done(call));
		struct json_object *item = NULL;
		CHECK(vali_client_call_wait(call, &item, NULL));
		if (item != NULL) {
			struct json_object *value = NULL;
			if (json_object_object_get_ex(item, "n", &value)) {
				CHECK(json_object_get_int(value) == i);
			} else {
				CHECK(0);
			}
			json_object_put(item);
		}
	}

	CHECK(vali_client_call_is_done(call));
	vali_client_call_destroy(call);
}

int main(void) {
	int sockets[2] = {-1, -1};
	if (socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) != 0) {
		perror("socketpair");
		return 1;
	}

	pid_t pid = fork();
	if (pid < 0) {
		perror("fork");
		return 1;
	}
	if (pid == 0) {
		/* 子进程：只保留自己那一端 */
		close(sockets[1]);
		run_service(sockets[0]);
		_exit(0);
	}

	close(sockets[0]);

	struct vali_client *client = vali_client_connect_fd(sockets[1]);
	CHECK(client != NULL);
	if (client == NULL) {
		return 1;
	}

	test_echo_and_error(client);
	test_oneway(client);
	test_more_replies(client);

	/* 收尾：请求服务端退出，然后确认子进程干净退出 */
	CHECK(vali_client_call(client, STOP_METHOD, NULL, NULL, NULL));
	vali_client_destroy(client);

	int status = 0;
	CHECK(waitpid(pid, &status, 0) >= 0);
	CHECK(WIFEXITED(status));
	CHECK(WEXITSTATUS(status) == 0);

	fprintf(stderr, "test_vali: %d checks run, %d failed\n", checks_run, checks_failed);
	if (checks_failed != 0) {
		return 1;
	}
	fprintf(stderr, "test_vali: ALL CHECKS PASSED\n");
	return 0;
}
