/* edshim.c — mmh 0.4 上游测试套件在 OHOS 真机的最小 `ed` 实现（驱动差异 D7）。
 *
 * 背景：设备的 toybox 无 ed，HNP 工具集也没有。tests/show/test-longlines
 * 在退出 trap 中以
 *     printf "/^mhl:/d\nw\nq\n" | ed - "$MMH/profile"
 * 清理 profile 中临时追加的一行；本体断言（997/998/999 与 CRLF 的长行
 * 折叠 diff）不依赖 ed，但 trap 执行失败会毒化用例退出码，使全绿用例
 * 被记为 FAIL。
 *
 * 本实现仅覆盖该调用使用的 POSIX ed 子集：
 *   /RE/d   删除匹配 RE 的行
 *   w       回写文件
 *   q       退出（状态 0）
 * 其余命令一律报错退出 1（不静默假装成功）。用法与 ed 相同：ed - FILE
 * （取最后一个参数为文件名）。
 */

#include <regex.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *slurp(const char *path)
{
	FILE *f = fopen(path, "rb");
	char *b, *nb;
	size_t cap = 8192, n = 0;
	int c;

	if (!f)
		return NULL;
	b = malloc(cap);
	if (!b) {
		fclose(f);
		return NULL;
	}
	while ((c = fgetc(f)) != EOF) {
		if (n + 2 > cap) {
			cap *= 2;
			nb = realloc(b, cap);
			if (!nb) {
				free(b);
				fclose(f);
				return NULL;
			}
			b = nb;
		}
		b[n++] = (char)c;
	}
	fclose(f);
	b[n] = '\0';
	return b;
}

int main(int argc, char **argv)
{
	const char *path;
	char *cur;
	char line[4096];

	if (argc < 2) {
		fputs("edshim: usage: ed - FILE\n", stderr);
		return 1;
	}
	path = argv[argc - 1];
	cur = slurp(path);
	if (!cur) {
		fputs("edshim: cannot read file\n", stderr);
		return 1;
	}

	while (fgets(line, sizeof line, stdin)) {
		size_t l = strlen(line);

		while (l && (line[l - 1] == '\n' || line[l - 1] == '\r'))
			line[--l] = '\0';
		if (l == 0)
			continue;

		if (!strcmp(line, "q"))
			return 0;

		if (!strcmp(line, "w")) {
			FILE *f = fopen(path, "wb");
			size_t len = strlen(cur);

			if (!f || fwrite(cur, 1, len, f) != len) {
				fputs("edshim: write failed\n", stderr);
				return 1;
			}
			fclose(f);
			continue;
		}

		if (line[0] == '/') {
			char *e = strrchr(line, '/');
			regex_t re;
			char *out, *p, *q;

			if (!e || e == line || strcmp(e + 1, "d")) {
				fputs("edshim: unsupported command\n", stderr);
				return 1;
			}
			*e = '\0';
			if (regcomp(&re, line + 1, REG_EXTENDED) != 0) {
				fputs("edshim: bad regex\n", stderr);
				return 1;
			}
			out = malloc(strlen(cur) + 1);
			if (!out)
				return 1;
			p = cur;
			q = out;
			while (*p) {
				char *nl = strchr(p, '\n');
				size_t len = nl ? (size_t)(nl - p) : strlen(p);
				char save = p[len];
				int hit;

				p[len] = '\0';
				hit = regexec(&re, p, 0, NULL, 0) == 0;
				p[len] = save;
				if (!hit) {
					memcpy(q, p, len);
					q += len;
					if (nl)
						*q++ = '\n';
				}
				if (!nl)
					break;
				p = nl + 1;
			}
			*q = '\0';
			regfree(&re);
			free(cur);
			cur = out;
			continue;
		}

		fputs("edshim: unsupported command\n", stderr);
		return 1;
	}

	return 0;
}
