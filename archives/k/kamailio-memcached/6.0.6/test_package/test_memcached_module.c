/*
 * test_package consumer harness — kamailio-memcached 6.0.6
 *
 * `memcached.so` is a Kamailio *module*: a dlopen() plugin whose Kamailio
 * core symbols (dprint_*, _km_log_func, pv_*, MD5StringArray, ...) are
 * resolved from the Kamailio host at load time.  The harness plays the host
 * (kamailio_host_stubs.c is linked -rdynamic, like the Kamailio binary),
 * dlopens the *packaged* module and exercises it.
 *
 * Checks (each successful one prints "CHECK-OK: <name>"):
 *   1  module-dlopen-lazy
 *   2  module-exports-symbol
 *   3  module-exports-name-memcached
 *   4  module-libmemcached-libversion-symbol
 *   5  module-libmemcached-version-string
 *   6  module-libmemcached-api-callable
 *   7  ohos-elf64-aarch64-module                       [OHOS specific]
 *   8  ohos-dt-needed-only-system-runtime              [OHOS specific]
 *   9  ohos-no-build-path-rpath                        [OHOS specific]
 *  10  ohos-kamailio-host-abi-required                 [OHOS specific]
 */

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <elf.h>

#ifndef MODULE_SO
#error "MODULE_SO must be defined (path to the packaged memcached.so)"
#endif

static int g_ok = 0;
static int g_fail = 0;

static void check(const char *name, int condition)
{
	if (condition) {
		printf("CHECK-OK: %s\n", name);
		g_ok++;
	} else {
		printf("CHECK-FAIL: %s\n", name);
		g_fail++;
		fflush(stdout);
	}
}

/* ── minimal ELF64 reader (dynamic section + undefined symbols) ───── */
#define MAX_NEEDED 16
#define MAX_UNDEF 128

typedef struct {
	int class64;
	int machine_aarch64;
	int needed_count;
	char needed[MAX_NEEDED][64];
	int has_rpath;
	int has_runpath;
	char rpath[512];
	int undef_count;
	char undef[MAX_UNDEF][96];
} elf_info_t;

static int elf_scan(const char *path, elf_info_t *out)
{
	FILE *fp;
	long size;
	unsigned char *buf;
	Elf64_Ehdr *eh;
	Elf64_Shdr *shdrs;
	int i;

	memset(out, 0, sizeof(*out));
	fp = fopen(path, "rb");
	if (!fp)
		return -1;
	fseek(fp, 0, SEEK_END);
	size = ftell(fp);
	fseek(fp, 0, SEEK_SET);
	if (size <= 0) {
		fclose(fp);
		return -1;
	}
	buf = (unsigned char *)malloc((size_t)size);
	if (!buf) {
		fclose(fp);
		return -1;
	}
	if (fread(buf, 1, (size_t)size, fp) != (size_t)size) {
		free(buf);
		fclose(fp);
		return -1;
	}
	fclose(fp);

	if (size < (long)sizeof(Elf64_Ehdr) || memcmp(buf, ELFMAG, SELFMAG) != 0) {
		free(buf);
		return -1;
	}
	eh = (Elf64_Ehdr *)buf;
	out->class64 = (eh->e_ident[EI_CLASS] == ELFCLASS64);
	out->machine_aarch64 = (eh->e_machine == EM_AARCH64);
	shdrs = (Elf64_Shdr *)(buf + eh->e_shoff);

	/* dynamic section: DT_NEEDED / DT_RPATH / DT_RUNPATH */
	for (i = 0; i < eh->e_phnum; i++) {
		Elf64_Phdr *ph =
				(Elf64_Phdr *)(buf + eh->e_phoff + (size_t)i * eh->e_phentsize);
		Elf64_Dyn *dyn;
		const char *strtab = NULL;
		if (ph->p_type != PT_DYNAMIC)
			continue;
		dyn = (Elf64_Dyn *)(buf + ph->p_offset);
		for (Elf64_Dyn *d = dyn; d->d_tag != DT_NULL; d++) {
			if (d->d_tag == DT_STRTAB)
				strtab = (const char *)(buf + d->d_un.d_ptr);
		}
		if (!strtab)
			continue;
		for (Elf64_Dyn *d = dyn; d->d_tag != DT_NULL; d++) {
			if (d->d_tag == DT_NEEDED && out->needed_count < MAX_NEEDED) {
				const char *name = strtab + d->d_un.d_val;
				if ((const unsigned char *)name >= buf
						&& (const unsigned char *)name < buf + size) {
					snprintf(out->needed[out->needed_count],
							sizeof(out->needed[0]), "%s", name);
					out->needed_count++;
				}
			} else if (d->d_tag == DT_RPATH || d->d_tag == DT_RUNPATH) {
				const char *val = strtab + d->d_un.d_val;
				if (d->d_tag == DT_RPATH)
					out->has_rpath = 1;
				else
					out->has_runpath = 1;
				if ((const unsigned char *)val >= buf
						&& (const unsigned char *)val < buf + size)
					snprintf(out->rpath, sizeof(out->rpath), "%s", val);
			}
		}
	}

	/* section headers: collect undefined (SHN_UNDEF) dynamic symbols */
	for (i = 0; i < eh->e_shnum; i++) {
		Elf64_Shdr *sh = &shdrs[i];
		Elf64_Sym *syms;
		const char *strtab;
		size_t count, j;
		if (sh->sh_type != SHT_DYNSYM || sh->sh_entsize == 0)
			continue;
		syms = (Elf64_Sym *)(buf + sh->sh_offset);
		count = (size_t)(sh->sh_size / sh->sh_entsize);
		strtab = (const char *)(buf + shdrs[sh->sh_link].sh_offset);
		for (j = 0; j < count && out->undef_count < MAX_UNDEF; j++) {
			const char *name;
			if (syms[j].st_shndx != SHN_UNDEF)
				continue;
			name = strtab + syms[j].st_name;
			if (!name || !name[0])
				continue;
			if ((const unsigned char *)name < buf
					|| (const unsigned char *)name >= buf + size)
				continue;
			snprintf(out->undef[out->undef_count],
					sizeof(out->undef[0]), "%s", name);
			out->undef_count++;
		}
	}

	free(buf);
	return 0;
}

static int has_undef(const elf_info_t *info, const char *name)
{
	int i;
	for (i = 0; i < info->undef_count; i++)
		if (strcmp(info->undef[i], name) == 0)
			return 1;
	return 0;
}

static int has_undef_prefix(const elf_info_t *info, const char *prefix)
{
	int i;
	size_t n = strlen(prefix);
	for (i = 0; i < info->undef_count; i++)
		if (strncmp(info->undef[i], prefix, n) == 0)
			return 1;
	return 0;
}

static int needed_only_system_runtime(const elf_info_t *info)
{
	int i, have_cxx = 0;
	for (i = 0; i < info->needed_count; i++) {
		if (strcmp(info->needed[i], "libc.so") == 0)
			continue;
		if (strcmp(info->needed[i], "libc++_shared.so") == 0
				|| strcmp(info->needed[i], "libc++.so") == 0) {
			have_cxx = 1;
			continue;
		}
		return 0; /* anything else (e.g. libmemcached.so) is unexpected */
	}
	return have_cxx;
}

int main(void)
{
	const char *path = MODULE_SO;
	void *handle;
	void *sym;
	const char *(*lib_version)(void);
	void *(*mc_create)(void *);
	void (*mc_free)(void *);
	void *mc;
	int scan_ok;
	elf_info_t info;

	printf("module          = %s\n", path);

	/* 1: the packaged module loads into a Kamailio-shaped host. */
	handle = dlopen(path, RTLD_LAZY | RTLD_LOCAL);
	printf("dlopen(LAZY)    = %p\n", handle);
	check("module-dlopen-lazy", handle != NULL);
	if (!handle) {
		printf("dlerror: %s\n", dlerror());
		printf("RESULT %d/%d\n", g_ok, g_ok + g_fail);
		return 1;
	}

	/* 2: module interface table exported by every Kamailio module. */
	sym = dlsym(handle, "exports");
	check("module-exports-symbol", sym != NULL);

	/* 3: the interface table really is this module's: `struct module_exports`
	 * starts with `char *name`, and memcached.c initialises it to
	 * "memcached" (memcached.c:96-97). */
	{
		const char *mod_name = sym ? *(const char *const *)sym : NULL;
		if (mod_name)
			printf("module name     = %s\n", mod_name);
		check("module-exports-name-memcached",
				mod_name != NULL && strcmp(mod_name, "memcached") == 0);
	}

	/* 4/5: libmemcached is statically linked into the module — resolve the
	 * version call through the module handle and execute it. */
	lib_version = (const char *(*)(void))dlsym(handle, "memcached_lib_version");
	check("module-libmemcached-libversion-symbol", lib_version != NULL);
	{
		const char *v = lib_version ? lib_version() : NULL;
		if (v)
			printf("libmemcached    = %s\n", v);
		check("module-libmemcached-version-string",
				v != NULL && strcmp(v, "1.0.18") == 0);
	}

	/* 6: actually call the embedded libmemcached API. */
	mc_create = (void *(*)(void *))dlsym(handle, "memcached_create");
	mc_free = (void (*)(void *))dlsym(handle, "memcached_free");
	mc = NULL;
	if (mc_create && mc_free) {
		mc = mc_create(NULL);
		if (mc)
			mc_free(mc);
	}
	check("module-libmemcached-api-callable",
			mc_create != NULL && mc_free != NULL && mc != NULL);

	/* 7/8/9/10 [OHOS]: inspect the delivered ELF itself.  Every check below
	 * is evaluated exactly once, so the static check-name inventory is
	 * identical to the runtime CHECK-OK count (10). */
	scan_ok = (elf_scan(path, &info) == 0);
	if (scan_ok) {
		printf("DT_NEEDED       =");
		for (int i = 0; i < info.needed_count; i++)
			printf(" %s", info.needed[i]);
		printf("\n");
		if (info.has_rpath || info.has_runpath)
			printf("RPATH/RUNPATH  = %s\n", info.rpath);
		/* OHOS/musl resolves every relocation at dlopen() time, so the
		 * module can only be loaded by a host that provides the Kamailio
		 * core ABI: the module must still import the core symbols, and the
		 * libmemcached code must be fully embedded (no memcached_* import). */
		printf("undefined syms  = %d (kamailio core ABI + OHOS system runtime)\n",
				info.undef_count);
	} else {
		memset(&info, 0, sizeof(info));
	}

	check("ohos-elf64-aarch64-module",
			scan_ok && info.class64 && info.machine_aarch64);
	check("ohos-dt-needed-only-system-runtime",
			scan_ok && info.needed_count > 0 && needed_only_system_runtime(&info));
	check("ohos-no-build-path-rpath",
			scan_ok && !(info.has_rpath || info.has_runpath));
	check("ohos-kamailio-host-abi-required",
			scan_ok && has_undef(&info, "pv_get_null")
					&& has_undef(&info, "_km_log_func")
					&& has_undef(&info, "MD5StringArray")
					&& !has_undef_prefix(&info, "memcached_"));

	dlclose(handle);
	printf("RESULT %d/%d\n", g_ok, g_ok + g_fail);
	return g_fail == 0 ? 0 : 1;
}
