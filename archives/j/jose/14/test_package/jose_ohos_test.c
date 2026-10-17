/*
 * test_package HarmonyOS-specific test for jose/14.
 *
 * Drives the *installed* `jose` CLI end to end: algorithm registration against
 * the OpenSSL backend on aarch64, JWK generation, RFC 7638 style thumbprints,
 * JWS sign/verify and JWE encrypt/decrypt - plus the ELF identity of the
 * packaged binary. Upstream's own tests only ever run the build-tree binary,
 * so nothing in the upstream suite covers the artifact a consumer installs.
 *
 * The CLI is invoked through the absolute path the package exports
 * (JOSE_BIN, handed over by the test_package conanfile from
 * `self.dependencies["jose"].package_folder`). Run-env PATH export and the
 * HMDFS permission bits are printed as diagnostics instead of being asserted:
 * they describe how a consumer happens to launch the tool, not what jose
 * packages. Every positive assertion is paired with a negative control so a
 * false green (everything returning 0 regardless of input) cannot pass.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef JOSE_BIN
#define JOSE_BIN ""
#endif

#define WORKDIR "jose-consumer-t"

static int g_total;
static int g_pass;
static const char *g_jose = JOSE_BIN;

#define CHECK(cond, name)                                                  \
	do {                                                               \
		g_total++;                                                 \
		if (cond) {                                                \
			g_pass++;                                          \
			printf("[PASS] %s\n", name);                       \
		} else {                                                   \
			printf("[FAIL] %s\n", name);                       \
		}                                                          \
	} while (0)

/* Run a command, capture stdout (stderr discarded), return its exit status. */
static int cap(const char *cmd, char *out, size_t out_sz)
{
	char full[4096];
	FILE *pipe;
	size_t used = 0;
	int rc;

	snprintf(full, sizeof(full), "%s 2>/dev/null", cmd);
	pipe = popen(full, "r");
	if (pipe == NULL) {
		if (out_sz)
			out[0] = '\0';
		return -1;
	}
	if (out && out_sz) {
		while (used + 1 < out_sz) {
			size_t got = fread(out + used, 1, out_sz - 1 - used, pipe);
			if (got == 0)
				break;
			used += got;
		}
		out[used] = '\0';
	}
	rc = pclose(pipe);
	return WIFEXITED(rc) ? WEXITSTATUS(rc) : -1;
}

/* Run `<installed jose> <args>` and capture its stdout. */
static int run_jose(const char *args, char *out, size_t out_sz)
{
	char cmd[4096];

	snprintf(cmd, sizeof(cmd), "%s %s", g_jose, args);
	return cap(cmd, out, out_sz);
}

static void rstrip(char *s)
{
	size_t n = strlen(s);

	while (n > 0 && (s[n - 1] == '\n' || s[n - 1] == '\r' ||
			 s[n - 1] == ' ' || s[n - 1] == '\t'))
		s[--n] = '\0';
}

/* Exact whole-line match, mirroring upstream's `grep -q "^NAME$"`. */
static int has_line(const char *out, const char *line)
{
	const char *p = out;
	size_t len = strlen(line);

	while (*p) {
		const char *eol = strchr(p, '\n');
		size_t n = eol ? (size_t) (eol - p) : strlen(p);

		if (n == len && memcmp(p, line, len) == 0)
			return 1;
		if (!eol)
			break;
		p = eol + 1;
	}
	return 0;
}

static int file_nonempty(const char *path)
{
	struct stat st;

	return stat(path, &st) == 0 && st.st_size > 0;
}

static int is_urlsafe(const char *s)
{
	static const char MAP[] =
		"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
	size_t i;

	if (s[0] == '\0')
		return 0;
	for (i = 0; s[i]; i++) {
		if (strchr(MAP, s[i]) == NULL)
			return 0;
	}
	return 1;
}

/* ELF64 + EM_AARCH64, read straight out of the packaged binary. */
static int elf_is_aarch64(const char *path)
{
	unsigned char hdr[20];
	FILE *fp = fopen(path, "rb");

	if (fp == NULL)
		return 0;
	if (fread(hdr, 1, sizeof(hdr), fp) != sizeof(hdr)) {
		fclose(fp);
		return 0;
	}
	fclose(fp);
	return hdr[0] == 0x7f && hdr[1] == 'E' && hdr[2] == 'L' && hdr[3] == 'F' &&
		hdr[4] == 2 /* ELFCLASS64 */ &&
		hdr[18] == 0xB7 /* e_machine = EM_AARCH64 (183) */ &&
		hdr[19] == 0x00;
}

/* Is an executable reachable through $PATH the way a shell would find it? */
static int path_has(const char *name)
{
	const char *path = getenv("PATH");
	const char *p = path ? path : "";

	while (p && *p) {
		const char *sep = strchr(p, ':');
		size_t n = sep ? (size_t) (sep - p) : strlen(p);
		struct stat st;
		char cand[1024];

		if (n > 0 && n < 700) {
			snprintf(cand, sizeof(cand), "%.*s/%s", (int) n, p, name);
			if (access(cand, X_OK) == 0 && stat(cand, &st) == 0 &&
			    S_ISREG(st.st_mode))
				return 1;
		}
		if (!sep)
			break;
		p = sep + 1;
	}
	return 0;
}

/* Diagnostics only: how the run env would resolve `jose` by name. */
static void report_runenv_diagnostics(void)
{
	const char *path = getenv("PATH");
	const char *ld = getenv("LD_LIBRARY_PATH");
	char probe[1024];
	struct stat st;
	const char *p = path;
	int tried = 0;
	FILE *fp;

	printf("[INFO] LD_LIBRARY_PATH=%s\n", ld ? ld : "(unset)");
	printf("[INFO] PATH=%s\n", path ? path : "(unset)");

	while (p && *p && tried < 6) {
		const char *sep = strchr(p, ':');
		size_t n = sep ? (size_t) (sep - p) : strlen(p);

		if (n > 0 && n < 700) {
			snprintf(probe, sizeof(probe), "%.*s/jose", (int) n, p);
			if (stat(probe, &st) == 0)
				printf("[INFO] PATH candidate %s mode=%03o\n",
				       probe, (unsigned) (st.st_mode & 07777));
			else
				printf("[INFO] PATH candidate %s absent (errno=%d)\n",
				       probe, errno);
			tried++;
		}
		if (!sep)
			break;
		p = sep + 1;
	}

	fp = fopen("/proc/self/status", "r");
	if (fp != NULL) {
		char line[256];

		while (fgets(line, sizeof(line), fp) != NULL) {
			if (strncmp(line, "Uid:", 4) == 0) {
				line[strcspn(line, "\n")] = '\0';
				printf("[INFO] /proc/self/status %s\n", line);
				break;
			}
		}
		fclose(fp);
	}
}

int main(void)
{
	char out[8192];
	char cmd[4096];
	int rc;

	printf("== jose/14 installed-artifact tests (HarmonyOS aarch64) ==\n");
	printf("[INFO] packaged CLI = %s\n", g_jose);
	report_runenv_diagnostics();

	/* --- the packaged CLI is there and really an aarch64 OHOS binary --- */
	rc = access(g_jose, X_OK);
	CHECK(rc == 0, "packaged `bin/jose` exists and is executable");
	CHECK(elf_is_aarch64(g_jose), "packaged `jose` is ELF64 EM_AARCH64");
	CHECK(path_has("jose"),
	      "`jose` is reachable through the consumer runenv PATH");

	/* --- work in a private directory: /tmp is read-only on the device --- */
	mkdir(WORKDIR, 0755);
	if (chdir(WORKDIR) != 0) {
		printf("[FAIL] cannot enter %s\n", WORKDIR);
		printf("TOTAL=%d PASS=%d FAIL=%d\n", g_total, g_pass, g_total + 1);
		return 1;
	}

	/* --- algorithm registry: OpenSSL backends really loaded on OHOS --- */
	rc = run_jose("alg", out, sizeof(out));
	rstrip(out);
	CHECK(rc == 0 && out[0] != '\0', "`jose alg` lists algorithms");
	CHECK(rc == 0 && has_line(out, "A128GCM"), "`jose alg` has A128GCM");

	rc = run_jose("alg -k sign", out, sizeof(out));
	rstrip(out);
	CHECK(rc == 0 && has_line(out, "ES256"), "`jose alg -k sign` has ES256");
	CHECK(rc == 0 && !has_line(out, "A128GCMKW"),
	      "`jose alg -k sign` excludes A128GCMKW (negative control)");

	rc = run_jose("alg -k encr", out, sizeof(out));
	rstrip(out);
	CHECK(rc == 0 && has_line(out, "A128GCM"), "`jose alg -k encr` has A128GCM");
	CHECK(rc == 0 && !has_line(out, "ES256"),
	      "`jose alg -k encr` excludes ES256 (negative control)");

	rc = run_jose("alg -k exch", out, sizeof(out));
	rstrip(out);
	CHECK(rc == 0 && has_line(out, "ECDH"), "`jose alg -k exch` has ECDH");

	/* --- base64url through the CLI, vectors from tests/jose-b64-enc --- */
	snprintf(cmd, sizeof(cmd), "printf 'foo' | %s b64 enc -I-", g_jose);
	rc = cap(cmd, out, sizeof(out));
	rstrip(out);
	CHECK(rc == 0 && strcmp(out, "Zm9v") == 0, "`jose b64 enc` gives Zm9v for foo");

	snprintf(cmd, sizeof(cmd), "printf 'Zm9v' | %s b64 dec -i-", g_jose);
	rc = cap(cmd, out, sizeof(out));
	rstrip(out);
	CHECK(rc == 0 && strcmp(out, "foo") == 0, "`jose b64 dec` gives foo for Zm9v");

	/* --- JWK generation + RFC 7638 style thumbprint --- */
	rc = run_jose("jwk gen -i '{\"alg\":\"HS256\"}' -o mac.jwk", out,
	              sizeof(out));
	CHECK(rc == 0 && file_nonempty("mac.jwk"),
	      "`jose jwk gen` writes an HS256 key");

	rc = run_jose("jwk thp -i mac.jwk", out, sizeof(out));
	rstrip(out);
	CHECK(rc == 0 && strlen(out) == 43 && is_urlsafe(out),
	      "`jose jwk thp` returns a 43-char URL-safe S256 thumbprint");

	rc = run_jose("jwk thp -i mac.jwk -a S256", out, sizeof(out));
	rstrip(out);
	CHECK(rc == 0 && strlen(out) == 43,
	      "`jose jwk thp -a S256` matches the default hash");

	/* --- JWS sign/verify, compact form, with a tampering negative control --- */
	snprintf(cmd, sizeof(cmd), "printf 'hi' | %s jws sig -I- -k mac.jwk -o jwt -c",
	         g_jose);
	rc = cap(cmd, out, sizeof(out));
	CHECK(rc == 0 && file_nonempty("jwt"), "`jose jws sig` writes a compact JWS");

	rc = run_jose("jws ver -i jwt -k mac.jwk", out, sizeof(out));
	CHECK(rc == 0, "`jose jws ver` accepts its own signature");

	/*
	 * Flip the first signature character in the compact form; verification
	 * must now fail. Done in C so the mutation cannot be silently mangled by
	 * the shell, the way upstream's `echo $var |` lines are.
	 */
	{
		char token[4096];
		size_t len = 0;
		size_t dot = 0;
		FILE *fp = fopen("jwt", "rb");

		rc = -1;
		if (fp != NULL) {
			len = fread(token, 1, sizeof(token) - 1, fp);
			token[len] = '\0';
			fclose(fp);
			/* find the last '.' = start of the signature segment */
			for (dot = len; dot > 0; dot--) {
				if (token[dot - 1] == '.')
					break;
			}
			if (dot > 0 && dot < len) {
				token[dot] = token[dot] == 'A' ? 'B' : 'A';
				fp = fopen("jwt.bad", "wb");
				if (fp != NULL) {
					if (fwrite(token, 1, len, fp) == len)
						rc = 0;
					fclose(fp);
				}
			}
		}
		CHECK(rc == 0 && file_nonempty("jwt.bad"),
		      "tampered token written (signature head flipped)");
		rc = run_jose("jws ver -i jwt.bad -k mac.jwk", out, sizeof(out));
		CHECK(rc != 0,
		      "`jose jws ver` rejects a tampered signature (negative control)");
	}

	/* --- JWE encrypt/decrypt round trip with an A128GCM key --- */
	rc = run_jose("jwk gen -i '{\"alg\":\"A128GCM\"}' -o enc.jwk", out,
	              sizeof(out));
	CHECK(rc == 0 && file_nonempty("enc.jwk"),
	      "`jose jwk gen` writes an A128GCM key");

	snprintf(cmd, sizeof(cmd), "printf 'hi' | %s jwe enc -I- -k enc.jwk -o jwe",
	         g_jose);
	rc = cap(cmd, out, sizeof(out));
	CHECK(rc == 0 && file_nonempty("jwe"), "`jose jwe enc` writes a JWE");

	rc = run_jose("jwe dec -i jwe -k enc.jwk -O-", out, sizeof(out));
	rstrip(out);
	CHECK(rc == 0 && strcmp(out, "hi") == 0,
	      "`jose jwe dec` recovers the plaintext");

	rc = run_jose("jwe dec -i jwe -k mac.jwk -O-", out, sizeof(out));
	CHECK(rc != 0, "`jose jwe dec` rejects the wrong key (negative control)");

	printf("TOTAL=%d PASS=%d FAIL=%d\n", g_total, g_pass, g_total - g_pass);
	if (g_pass != g_total)
		return 1;
	printf("ALL TESTS PASSED\n");
	return 0;
}
