/* 消费者用例 — kamailio-xmpp 6.0.6 (xmpp.so) 的「按 core 装载协议消费」实测。

xmpp.so 由 kamailio 二进制运行时 loadmodule()（内部即 dlopen + 契约符号校验）加载；
本消费者进程复刻该协议并**真实驱动模块功能**：

  1) dlopen("libexpat.so")            —— 模块唯一外部依赖（DT_NEEDED）在 OHOS 目标机上
                                         可加载（依赖制品可用性）
  2) dlopen(xmpp.so)                  —— 模块自身全部重定位可解析（core 符号由桩提供，
                                         等价宿主进程导出 core 符号）
  3) dlsym module_version / module_flags / exports
                                      —— 复刻 core/sr_module.c 的装载契约检查项
  4) 经 dlsym 调用模块自身的 XMPP stanza 解析 API（xode_from_str / xode_get_name /
     xode_get_attrib / xode_get_tagdata / xode_to_str / xode_free）
                                      —— 真实走通「模块 → expat（XML_ParserCreate/Parse）」
                                         运行路径，是本模块在 OHOS aarch64 上功能可用的
                                         直接证据；另含负例（非法 XML 必须返回 NULL）

编译：由 test_package/conanfile.py build() 用 profile 声明的交叉 C 编译器完成，
不注入任何共享前缀（R49）；链接时不链接 expat，以证明模块自身做 XML 解析。
*/
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

typedef void *xode;

static int failures = 0;

static void check(int ok, const char *label, const char *detail)
{
	if (ok) {
		printf("[PASS] %s%s%s\n", label, detail ? " — " : "", detail ? detail : "");
	} else {
		printf("[FAIL] %s%s%s\n", label, detail ? " — " : "", detail ? detail : "");
		failures++;
	}
	fflush(stdout);
}

int main(int argc, char **argv)
{
	void *libexpat, *h;
	const char *path;
	/* core/sr_module.c 以 (char **)dlsym 取得 module_version / module_flags，再解引用
	 * *m_ver / *m_flags 得到字符串 —— 二者是模块内的 char * **数据符号**（非函数），
	 * 必须按数据符号使用，否则调用即崩溃。 */
	char **m_ver, **m_flags;
	char *(*f_get_name)(xode);
	char *(*f_get_attrib)(xode, const char *);
	char *(*f_get_tagdata)(xode, const char *);
	char *(*f_to_str)(xode);
	void (*f_free)(xode);
	xode (*f_from_str)(char *, int);
	void *exports;
	const char *xml_valid = "<presence from=\"alice@example.com\"><status>online</status></presence>";
	const char *xml_bad = "<presence><status>online</presence>";
	xode doc, bad;
	char *name, *from, *status, *serialized;

	if (argc < 2) {
		fprintf(stderr, "usage: %s <path-to-xmpp.so>\n", argv[0]);
		return 2;
	}
	path = argv[1];
	/* 逐行即时输出：CRASH 时已打印的用例结果不丢，CI 日志可直接定位失败点 */
	setvbuf(stdout, NULL, _IONBF, 0);

	/* 1) 依赖：libexpat.so 必须能在本进程内被加载（目标机可用性） */
	libexpat = dlopen("libexpat.so", RTLD_NOW | RTLD_GLOBAL);
	check(libexpat != NULL, "dlopen(libexpat.so) 依赖可加载",
		  libexpat ? NULL : dlerror());

	/* 2) 装载模块本体（RTLD_NOW：所有重定位必须当场解析成功） */
	dlerror();
	h = dlopen(path, RTLD_NOW | RTLD_GLOBAL);
	if (!h) {
		check(0, "dlopen(xmpp.so)", dlerror());
		return 1;
	}
	check(1, "dlopen(xmpp.so) 全部重定位解析成功", NULL);

	/* 3) core 装载契约符号（core/sr_module.c: dlsym module_version / module_flags） */
	m_ver = (char **)dlsym(h, "module_version");
	m_flags = (char **)dlsym(h, "module_flags");
	exports = dlsym(h, "exports");
	check(m_ver != NULL && m_flags != NULL && exports != NULL && *m_ver && *m_flags,
		  "契约符号 module_version/module_flags/exports",
		  m_ver && m_flags && exports ? "3/3 found" : "missing");

	if (!m_ver || !m_flags || !*m_ver || !*m_flags) {
		return 1;
	}
	check(strncmp(*m_ver, "kamailio 6.0.6 (aarch64/linux)", 30) == 0,
		  "SER_FULL_VERSION 目标标识（core 装载 strcmp 项）", *m_ver);
	check(strstr(*m_flags, "USE_TCP") != NULL
			  && strstr(*m_flags, "F_MALLOC") != NULL
			  && strstr(*m_flags, "USE_SCTP") == NULL
			  && strstr(*m_flags, "HAVE_RESOLV_RES") == NULL,
		  "SER_COMPILE_FLAGS 与 OHOS core 口径一致（SCTP 关、无 _res）", *m_flags);

	/* 4) 真实功能：模块自身 XMPP stanza 解析（内部走 expat） */
	f_from_str = (xode(*)(char *, int))dlsym(h, "xode_from_str");
	f_get_name = (char *(*)(xode))dlsym(h, "xode_get_name");
	f_get_attrib = (char *(*)(xode, const char *))dlsym(h, "xode_get_attrib");
	f_get_tagdata = (char *(*)(xode, const char *))dlsym(h, "xode_get_tagdata");
	f_to_str = (char *(*)(xode))dlsym(h, "xode_to_str");
	f_free = (void (*)(xode))dlsym(h, "xode_free");
	check(f_from_str && f_get_name && f_get_attrib && f_get_tagdata && f_to_str && f_free,
		  "模块 XMPP 解析 API 可经 dlsym 取得", NULL);
	if (!(f_from_str && f_get_name && f_get_attrib && f_get_tagdata && f_to_str && f_free)) {
		check(0, "模块 API 完整性", "部分符号缺失，跳过后继用例");
		return 1;
	}

	doc = f_from_str((char *)xml_valid, -1);
	check(doc != NULL, "xode_from_str 解析合法 XMPP stanza（expat 运行路径）", NULL);
	if (doc) {
		name = f_get_name(doc);
		check(name && strcmp(name, "presence") == 0, "xode_get_name == presence",
			  name ? name : "()");
		from = f_get_attrib(doc, "from");
		check(from && strcmp(from, "alice@example.com") == 0,
			  "xode_get_attrib(\"from\") 属性值正确", from ? from : "()");
		status = f_get_tagdata(doc, "status");
		check(status && strcmp(status, "online") == 0,
			  "xode_get_tagdata(\"status\") 子元素文本正确", status ? status : "()");
		serialized = f_to_str(doc);
		check(serialized && strstr(serialized, "<status>online</status>") != NULL,
			  "xode_to_str 重新序列化含子元素", serialized ? serialized : "()");
		f_free(doc);
	}

	bad = f_from_str((char *)xml_bad, -1);
	check(bad == NULL, "xode_from_str 对非法 XML 返回 NULL（expat 错误路径）", NULL);
	if (bad) {
		f_free(bad);
	}

	dlclose(h);
	if (libexpat) {
		dlclose(libexpat);
	}

	if (failures) {
		printf("\nFAILED: %d 项消费者用例未通过\n", failures);
		return 1;
	}
	printf("\nPASSED: xmpp.so 消费者用例全部通过\n");
	return 0;
}
