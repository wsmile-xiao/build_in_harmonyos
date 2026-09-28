#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	const char *arch = sys_arch_get();
	const char *os = sys_os_get();
	const char *ver = sys_libre_version_get();
	struct pl pl;
	struct pl exp;

	CHECK(arch != NULL && strlen(arch) > 0);
	CHECK(os != NULL && strlen(os) > 0);
	CHECK(ver != NULL && strchr(ver, '.') != NULL);

	pl_set_str(&pl, arch);
	pl_set_str(&exp, "aarch64");
	CHECK(pl_casecmp(&pl, &exp) == 0);

	sys_usleep(1000);

	/* 同一调用应稳定返回同一字符串 */
	CHECK(strcmp(sys_arch_get(), arch) == 0);

	libre_close();

	return errors ? 1 : 0;
}
