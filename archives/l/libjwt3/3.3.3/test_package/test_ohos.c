/*
 * libjwt3 鸿蒙（OHOS）平台特有测试（test_package）。
 *
 * 验证本适配针对 OHOS 平台的修复在真实加载器/文件系统下的运行时语义：
 *
 *   A. 共享库 SONAME 语义
 *      CMake 缺 Modules/Platform/HarmonyOS.cmake 导致
 *      CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空（HasSOName 的判据）→ 缺 DT_SONAME；
 *      配方用 CMAKE_PLATFORM_NO_VERSIONED_SONAME + SONAME flag 修复为
 *      「单个实体 libjwt.so + 裸 SONAME」。本测试验证：
 *        - 加载器能按裸 SONAME "libjwt.so" 解析（OHOS musl 加载器无法经版本化
 *          软链别名解析，知识 E505/E274）；
 *        - .dynamic 中 DT_SONAME == "libjwt.so"（L5a 修复的运行时证据）；
 *        - 加载路径是无版本后缀的实体文件（HMDFS 无法创建版本化软链链，E330）；
 *        - DT_NEEDED 含 libjansson.so、不含 libcrypto/libssl
 *          （openssl/3.5.6 制品仓仅静态库 → OpenSSL 静态链入）。
 *
 *   B. 4 个命令行工具经 Conan bindirs 通道可达，且为合法 ELF
 *      （R38/commands.json 的声明与产物一致性；工具链 jwt_static，属本包交付物）
 *
 *   C. /bin/sh 可执行
 *      上游 add_test() 硬编码 /bin/bash（CMakeLists:315），OHOS 无此路径，
 *      配方以 POSIX shell 等价语义驱动上游测试 —— 此处验证该前提成立。
 *
 * 仅用 POSIX + dlfcn + ELF 解析，不依赖 musl 扩展（不用 dlinfo），
 * 不引入任何测试框架。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>
#include <stdint.h>

#include <jwt.h>

/* 由 conanfile.py 的 generate() 注入（Conan 的 bindirs 通道） */
#ifndef LIBJWT3_BINDIR
#define LIBJWT3_BINDIR "/nonexistent-libjwt3-bindir"
#endif

static int failures;

#define CHECK(cond, msg)						\
	do {								\
		if (!(cond)) {						\
			fprintf(stderr, "FAIL: %s (line %d)\n", (msg), __LINE__);	\
			failures++;					\
		} else {						\
			printf("ok: %s\n", (msg));			\
		}							\
	} while (0)

/* ---- 纯 ELF64 .dynamic 解析（vaddr→文件偏移经 PT_LOAD 换算） ---- */
static int elf_dyn_strings(const char *path, char *soname_out, size_t soname_sz,
			   char needed[][64], int needed_max, int *needed_cnt)
{
	FILE *f = fopen(path, "rb");
	if (f == NULL)
		return -1;

	unsigned char ehdr[64];
	if (fread(ehdr, 1, sizeof(ehdr), f) != sizeof(ehdr) ||
	    ehdr[0] != 0x7f || ehdr[1] != 'E') {
		fclose(f);
		return -1;
	}
	uint64_t phoff;
	uint16_t phentsize, phnum;
	memcpy(&phoff, ehdr + 0x20, 8);
	memcpy(&phentsize, ehdr + 0x36, 2);
	memcpy(&phnum, ehdr + 0x38, 2);

	uint64_t dyn_vaddr = 0, dyn_filesz = 0;
#define MAX_LOAD 16
	uint64_t load_vaddr[MAX_LOAD], load_off[MAX_LOAD], load_filesz[MAX_LOAD];
	int load_cnt = 0;

	for (int i = 0; i < phnum; i++) {
		unsigned char ph[56];
		if (fseek(f, (long)(phoff + (uint64_t)i * phentsize), SEEK_SET) != 0 ||
		    fread(ph, 1, sizeof(ph), f) != sizeof(ph))
			break;
		uint32_t p_type;
		memcpy(&p_type, ph + 0, 4);
		uint64_t p_offset, p_vaddr, p_filesz;
		memcpy(&p_offset, ph + 8, 8);
		memcpy(&p_vaddr, ph + 16, 8);
		memcpy(&p_filesz, ph + 32, 8);
		if (p_type == 2 /* PT_DYNAMIC */) {
			dyn_vaddr = p_vaddr;
			dyn_filesz = p_filesz;
		} else if (p_type == 1 /* PT_LOAD */ && load_cnt < MAX_LOAD) {
			load_vaddr[load_cnt] = p_vaddr;
			load_off[load_cnt] = p_offset;
			load_filesz[load_cnt] = p_filesz;
			load_cnt++;
		}
	}
	if (dyn_vaddr == 0 || load_cnt == 0) {
		fclose(f);
		return -1;
	}

	uint64_t dyn_off = UINT64_MAX;
	for (int i = 0; i < load_cnt; i++) {
		if (dyn_vaddr >= load_vaddr[i] &&
		    dyn_vaddr - load_vaddr[i] < load_filesz[i]) {
			dyn_off = load_off[i] + (dyn_vaddr - load_vaddr[i]);
			break;
		}
	}
	if (dyn_off == UINT64_MAX) {
		fclose(f);
		return -1;
	}

	uint64_t strtab_vaddr = 0;
	size_t ndyn = (size_t)(dyn_filesz / 16);
	uint64_t *dyn = (uint64_t *)malloc(ndyn * 16);
	if (dyn == NULL) {
		fclose(f);
		return -1;
	}
	if (fseek(f, (long)dyn_off, SEEK_SET) != 0 ||
	    fread(dyn, 16, ndyn, f) != ndyn) {
		free(dyn);
		fclose(f);
		return -1;
	}
	for (size_t i = 0; i < ndyn; i++) {
		if (dyn[i * 2] == 5 /* DT_STRTAB */) {
			memcpy(&strtab_vaddr, &dyn[i * 2 + 1], 8);
			break;
		}
	}
	if (strtab_vaddr == 0) {
		free(dyn);
		fclose(f);
		return -1;
	}
	uint64_t strtab_off = UINT64_MAX;
	for (int i = 0; i < load_cnt; i++) {
		if (strtab_vaddr >= load_vaddr[i] &&
		    strtab_vaddr - load_vaddr[i] < load_filesz[i]) {
			strtab_off = load_off[i] + (strtab_vaddr - load_vaddr[i]);
			break;
		}
	}
	if (strtab_off == UINT64_MAX) {
		free(dyn);
		fclose(f);
		return -1;
	}

	*needed_cnt = 0;
	for (size_t i = 0; i < ndyn; i++) {
		uint64_t tag = dyn[i * 2];
		uint64_t val;
		memcpy(&val, &dyn[i * 2 + 1], 8);
		if (tag == 0 /* DT_NULL */)
			break;
		uint64_t stroff = UINT64_MAX;
		if (tag == 14 /* DT_SONAME */)
			stroff = val;
		else if (tag == 1 /* DT_NEEDED */ && *needed_cnt < needed_max)
			stroff = val;
		if (stroff == UINT64_MAX)
			continue;
		char buf[64] = {0};
		if (fseek(f, (long)(strtab_off + stroff), SEEK_SET) != 0 ||
		    fread(buf, 1, sizeof(buf) - 1, f) == 0)
			continue;
		if (tag == 14) {
			snprintf(soname_out, soname_sz, "%s", buf);
		} else {
			snprintf(needed[*needed_cnt], 64, "%s", buf);
			(*needed_cnt)++;
		}
	}
	free(dyn);
	fclose(f);
	return 0;
}

static int needed_has(char needed[][64], int cnt, const char *name)
{
	for (int i = 0; i < cnt; i++)
		if (strcmp(needed[i], name) == 0)
			return 1;
	return 0;
}

/* 校验一个可执行文件是 ELF64（aarch64）可执行文件 */
static int is_elf_executable(const char *path)
{
	FILE *f = fopen(path, "rb");
	if (f == NULL)
		return 0;
	unsigned char ehdr[20];
	size_t n = fread(ehdr, 1, sizeof(ehdr), f);
	fclose(f);
	/* e_ident[0..3] = 0x7f 'E' 'L' 'F'；e_ident[4] = EI_CLASS（2 = ELF64） */
	return n == sizeof(ehdr) && ehdr[0] == 0x7f && ehdr[1] == 'E' &&
	       ehdr[2] == 'L' && ehdr[3] == 'F' && ehdr[4] == 2;
}

int main(void)
{
	/* ── A1: 加载器按 SONAME 解析 libjwt.so ─────────────────────────── */
	void *h = dlopen("libjwt.so", RTLD_NOW | RTLD_GLOBAL);
	CHECK(h != NULL, "dlopen(\"libjwt.so\") 经 SONAME 解析成功");
	if (h == NULL) {
		fprintf(stderr, "dlerror: %s\n", dlerror());
		fprintf(stderr, "%d check(s) FAILED\n", failures);
		return EXIT_FAILURE;
	}

	/* A2: 符号探测（v3 API：jwt_builder_new，勿用已移除的 jwt_new） */
	Dl_info info;
	void *sym = dlsym(h, "jwt_builder_new");
	CHECK(sym != NULL, "dlsym(jwt_builder_new) 解析到 v3 API 符号");
	sym = dlsym(h, "jwt_checker_verify");
	CHECK(sym != NULL, "dlsym(jwt_checker_verify) 解析到 v3 API 符号");
	sym = dlsym(h, "jwks_create");
	CHECK(sym != NULL, "dlsym(jwks_create) 解析到 v3 API 符号");
	CHECK(dlsym(h, "jwt_new") == NULL,
	      "dlsym(jwt_new) 为空（v3 已移除该 v2 API，验证版本正确）");

	CHECK(dladdr(sym, &info) != 0 && info.dli_fname != NULL,
	      "dladdr 定位到已加载 libjwt 实体路径");
	const char *base = info.dli_fname ? strrchr(info.dli_fname, '/') : NULL;
	base = base ? base + 1 : info.dli_fname;
	CHECK(base != NULL && strncmp(base, "libjwt.so", 9) == 0 &&
	      base[9] == '\0',
	      "加载路径为无版本后缀的实体文件 libjwt.so");

	/* A3: 解析 .dynamic：DT_SONAME / DT_NEEDED 运行时证据 */
	char soname[64] = {0};
	static char needed[8][64];
	int needed_cnt = 0;
	int rc = elf_dyn_strings(info.dli_fname, soname, sizeof(soname),
				 needed, 8, &needed_cnt);
	CHECK(rc == 0, "ELF .dynamic 段解析成功");
	CHECK(soname[0] != '\0' && strcmp(soname, "libjwt.so") == 0,
	      "DT_SONAME == \"libjwt.so\"（裸 SONAME，无版本化命名）");
	CHECK(needed_cnt > 0 && needed_has(needed, needed_cnt, "libjansson.so"),
	      "DT_NEEDED 含 libjansson.so（jansson 动态链接）");
	CHECK(!needed_has(needed, needed_cnt, "libcrypto.so.3") &&
	      !needed_has(needed, needed_cnt, "libcrypto.so") &&
	      !needed_has(needed, needed_cnt, "libssl.so.3") &&
	      !needed_has(needed, needed_cnt, "libssl.so"),
	      "DT_NEEDED 不含 libcrypto/libssl（OpenSSL 静态链入）");

	dlclose(h);

	/* ── B: 4 个命令行工具经 bindirs 通道可达（R38） ────────────────── */
	static const char *TOOLS[] = {
		"jwt-verify", "jwt-generate", "jwk2key", "key2jwk"
	};
	for (size_t i = 0; i < sizeof(TOOLS) / sizeof(TOOLS[0]); i++) {
		char path[512];
		snprintf(path, sizeof(path), "%s/%s", LIBJWT3_BINDIR, TOOLS[i]);
		int ok = is_elf_executable(path);
		char msg[256];
		snprintf(msg, sizeof(msg),
			 "CLI 工具 %s 经 Conan bindirs 可达且为合法 ELF 可执行文件",
			 TOOLS[i]);
		CHECK(ok, msg);
	}

	/* ── C: /bin/sh 可执行（上游测试驱动的等价解释器） ──────────────── */
	CHECK(access("/bin/sh", X_OK) == 0,
	      "/bin/sh 存在且可执行（上游测试驱动语义，/bin/bash 不存在）");

	if (failures != 0) {
		fprintf(stderr, "%d check(s) FAILED\n", failures);
		return EXIT_FAILURE;
	}

	printf("test libjwt3 3.3.3 ohos-specific: all checks passed\n");
	return EXIT_SUCCESS;
}
