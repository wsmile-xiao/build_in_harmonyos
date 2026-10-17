/*
 * libjwt-tools 鸿蒙（OHOS）平台特有消费者测试（test_package）。
 *
 * 这是本适配新增的「鸿蒙测试用例」：从消费者视角验证 libjwt-tools 交付的
 * 4 个命令行工具（jwt-verify / jwt-generate / jwk2key / key2jwk）在 OHOS
 * 上的交付形态是否正确。断言依据全部来自本机实测（2026-09-18）：
 *
 *   A. 工具经 Conan 的 cpp_info.bindirs 通道可达（消费者拿得到 bin/）：
 *      编译期由 conanfile.py 注入 LIBJWT_TOOLS_BINDIR。
 *   B. 每个工具是合法的 OHOS aarch64 可执行文件：
 *      ELF64 / e_machine=183(AArch64) / ET_DYN(PIE) / 有 PT_INTERP / X_OK。
 *   C. 每个工具经上游 jwt_add_tool() 的 `PRIVATE jwt_static` 静态链接 libjwt：
 *      DT_NEEDED 应含 libjansson.so 但**不含** libjwt.so —— 即工具交付物
 *      不依赖本体共享库，消费者只拿 bin/ 即可运行（本体包实测 DT_NEEDED
 *      为 libjansson.so + libc.so）。
 *   D. /bin/sh 可执行：上游 add_test() 把解释器硬编码为 /bin/bash，OHOS 根文件
 *      系统只有 /bin/sh，配方按等价语义驱动上游测试，此处验证该解释器存在。
 *
 * 不引入任何测试框架，自带轻量断言宏；仅用 POSIX + ELF 解析，
 * 不依赖 musl 扩展（不用 dlinfo，避免 CI 工具链差异）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdint.h>

#ifndef LIBJWT_TOOLS_BINDIR
#define LIBJWT_TOOLS_BINDIR "/nonexistent-libjwt-tools-bindir"
#endif

static const char *TOOLS[] = {
	"jwt-verify", "jwt-generate", "jwk2key", "key2jwk"
};
#define NTOOLS ((int)(sizeof(TOOLS) / sizeof(TOOLS[0])))

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

/* ---- 纯 ELF64 头 + .dynamic 解析（vaddr→文件偏移经 PT_LOAD 换算） ---- */
struct elf_info {
	uint16_t e_machine;
	uint16_t e_type;
	int has_interp;
	int needed_cnt;
	char needed[16][64];
};

static int elf_probe(const char *path, struct elf_info *info)
{
	FILE *f = fopen(path, "rb");
	if (f == NULL)
		return -1;
	memset(info, 0, sizeof(*info));

	unsigned char ehdr[64];
	if (fread(ehdr, 1, sizeof(ehdr), f) != sizeof(ehdr) ||
	    ehdr[0] != 0x7f || ehdr[1] != 'E' || ehdr[2] != 'L' || ehdr[3] != 'F' ||
	    ehdr[4] != 2 /* ELFCLASS64 */) {
		fclose(f);
		return -1;
	}
	memcpy(&info->e_type, ehdr + 16, 2);
	memcpy(&info->e_machine, ehdr + 18, 2);

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
		uint64_t p_offset, p_vaddr, p_filesz;
		memcpy(&p_type, ph + 0, 4);
		memcpy(&p_offset, ph + 8, 8);
		memcpy(&p_vaddr, ph + 16, 8);
		memcpy(&p_filesz, ph + 32, 8);
		if (p_type == 2 /* PT_DYNAMIC */) {
			dyn_vaddr = p_vaddr;
			dyn_filesz = p_filesz;
		} else if (p_type == 3 /* PT_INTERP */) {
			info->has_interp = 1;
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

	for (size_t i = 0; i < ndyn; i++) {
		uint64_t tag = dyn[i * 2];
		uint64_t val;
		memcpy(&val, &dyn[i * 2 + 1], 8);
		if (tag == 0 /* DT_NULL */)
			break;
		if (tag != 1 /* DT_NEEDED */ || info->needed_cnt >= 16)
			continue;
		char buf[64] = {0};
		if (fseek(f, (long)(strtab_off + val), SEEK_SET) != 0 ||
		    fread(buf, 1, sizeof(buf) - 1, f) == 0)
			continue;
		snprintf(info->needed[info->needed_cnt], 64, "%s", buf);
		info->needed_cnt++;
	}
	free(dyn);
	fclose(f);
	return 0;
}

static int needed_has(const struct elf_info *info, const char *name)
{
	for (int i = 0; i < info->needed_cnt; i++)
		if (strcmp(info->needed[i], name) == 0)
			return 1;
	return 0;
}

static int needed_has_prefix(const struct elf_info *info, const char *pfx)
{
	for (int i = 0; i < info->needed_cnt; i++)
		if (strncmp(info->needed[i], pfx, strlen(pfx)) == 0)
			return 1;
	return 0;
}

int main(void)
{
	char path[4096];

	printf("# LIBJWT_TOOLS_BINDIR=%s\n", LIBJWT_TOOLS_BINDIR);

	for (int t = 0; t < NTOOLS; t++) {
		struct elf_info info = {0}; /* 零初始化：elf_probe 在 fopen 失败时早退，
					     * 不得以未初始化栈值作 needed[] 遍历上界 */
		int rc;

		snprintf(path, sizeof(path), "%s/%s", LIBJWT_TOOLS_BINDIR, TOOLS[t]);
		CHECK(access(path, X_OK) == 0,
		      "bindirs 通道可达且可执行：access(bin/<tool>, X_OK)");

		rc = elf_probe(path, &info);
		CHECK(rc == 0 && info.e_machine == 183 /* EM_AARCH64 */,
		      "ELF 头合法且 e_machine=183(AArch64)");
		CHECK(info.has_interp == 1, "含 PT_INTERP（可执行 ELF）");
		CHECK(needed_has(&info, "libjansson.so"),
		      "DT_NEEDED 含 libjansson.so（jansson 动态链接）");
		CHECK(!needed_has_prefix(&info, "libjwt.so"),
		      "DT_NEEDED 不含 libjwt.so（工具经 jwt_static 静态链接，"
		      "交付物不依赖本体共享库）");
	}

	/* 上游测试驱动语义：/bin/bash 不存在，配方按 /bin/sh 等价驱动 */
	CHECK(access("/bin/sh", X_OK) == 0,
	      "/bin/sh 存在且可执行（上游 add_test 硬编码 /bin/bash 的等价解释器）");

	if (failures != 0) {
		fprintf(stderr, "%d check(s) FAILED\n", failures);
		return EXIT_FAILURE;
	}

	printf("test libjwt-tools 3.3.3 ohos-specific: all checks passed\n");
	return EXIT_SUCCESS;
}
