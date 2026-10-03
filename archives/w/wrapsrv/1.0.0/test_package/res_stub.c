#define _GNU_SOURCE
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/*
 * res_stub.c -- test-only DNS transport shim for the wrapsrv test package.
 *
 * wrapsrv's entire value is "look up a DNS SRV record, then run the caller's
 * command against the selected target".  The lookup half needs a live DNS
 * server; the CI worker has no reachable resolver and cannot bind port 53 as
 * a non-root user, so it is not reproducible there.  This object is LD_PRELOADed
 * in front of the *delivered* wrapsrv binary and answers res_init()/res_query()
 * with a byte-accurate RFC 1035 message built below.
 *
 * Everything downstream stays the real upstream code: ns_initparse(),
 * ns_parserr(), the SRV rdata walk, the RFC 2782 priority/weight selection,
 * the %h/%p substitution and the system() call that runs the command.
 *
 * Per RFC 1035 section 4.1.4 / RFC 2782 the SRV target name is never
 * compressed, so the canned targets are emitted uncompressed -- which is
 * exactly the code path the shipped portability patch re-implements.
 *
 * Selected by WRAPSRV_STUB_MODE:
 *   single    (default) one SRV: prio 10, weight 100, port 8080
 *   pair                two SRVs listed worst-priority-first so that the
 *                       priority ordering can be observed
 *   nxdomain            rcode 3 (NXDOMAIN), empty answer section
 *   noanswer            rcode 0, empty answer section
 */

#define T_SRV_ 33
#define C_IN_   1

static size_t
put_name(unsigned char *p, const char *name)
{
	const char *dot = name;
	size_t len = 0;

	for (;;) {
		const char *next = strchr(dot, '.');
		size_t lbl = next ? (size_t)(next - dot) : strlen(dot);

		if (lbl > 63)
			return 0;
		if (lbl == 0)
			break;
		*p++ = (unsigned char)lbl;
		memcpy(p, dot, lbl);
		p += lbl;
		len += lbl + 1;
		if (!next)
			break;
		dot = next + 1;
	}
	*p++ = 0;
	return len + 1;
}

struct srv_rec {
	unsigned prio, weight, port;
	const char *target;
};

static size_t
build_reply(const struct srv_rec *recs, size_t nrecs, int rcode,
    unsigned char *ans, int anslen)
{
	static const char qname[] = "_stub._tcp.wrapsrv.test";
	unsigned char *p = ans;
	unsigned char *qname_ptr;
	size_t i;

	memset(ans, 0, (size_t)anslen);
	if (anslen < 512)
		return 0;

	p += 2;				/* id */
	*p++ = 0x81;			/* flags high: QR | RD */
	*p++ = (unsigned char)(rcode & 0x0f);	/* flags low: rcode */
	*p++ = 0;			/* qdcount = 1 */
	*p++ = 1;
	*p++ = (unsigned char)(nrecs >> 8);	/* ancount */
	*p++ = (unsigned char)(nrecs & 0xff);
	*p++ = 0;			/* nscount */
	*p++ = 0;
	*p++ = 0;			/* arcount */
	*p++ = 0;

	qname_ptr = p;
	p += put_name(p, qname);
	p[0] = 0; p[1] = T_SRV_;		/* qtype */
	p[2] = 0; p[3] = C_IN_;		/* qclass */
	p += 4;

	for (i = 0; i < nrecs; i++) {
		unsigned char *rdlen;

		*p++ = (unsigned char)0xc0;			/* name: ptr */
		*p++ = (unsigned char)(qname_ptr - ans);
		p[0] = 0; p[1] = T_SRV_;				/* type */
		p[2] = 0; p[3] = C_IN_;				/* class */
		p[4] = 0; p[5] = 0; p[6] = 0x00; p[7] = 0x3c;	/* ttl 60 */
		p += 8;

		rdlen = p;
		p += 2;						/* rdlength */

		p[0] = (unsigned char)(recs[i].prio >> 8);
		p[1] = (unsigned char)(recs[i].prio & 0xff);
		p[2] = (unsigned char)(recs[i].weight >> 8);
		p[3] = (unsigned char)(recs[i].weight & 0xff);
		p[4] = (unsigned char)(recs[i].port >> 8);
		p[5] = (unsigned char)(recs[i].port & 0xff);
		p += 6;

		{
			size_t rd = put_name(p, recs[i].target);

			rdlen[0] = (unsigned char)((rd + 6) >> 8);
			rdlen[1] = (unsigned char)((rd + 6) & 0xff);
			p += rd;
		}
	}

	return (size_t)(p - ans);
}

int
res_init(void)
{
	return (0);
}

int
res_query(const char *name, int class, int type, unsigned char *ans, int anslen)
{
	static const struct srv_rec single[] = {
		{ 10, 100, 8080, "primary.example.com" },
	};
	static const struct srv_rec pair[] = {
		{ 20, 10, 9090, "backup.example.com" },
		{ 10, 10, 8080, "primary.example.com" },
	};
	const char *mode = getenv("WRAPSRV_STUB_MODE");
	size_t n;

	(void)name; (void)class; (void)type;

	if (mode == NULL || strcmp(mode, "single") == 0)
		n = build_reply(single, 1, 0, ans, anslen);
	else if (strcmp(mode, "pair") == 0)
		n = build_reply(pair, 2, 0, ans, anslen);
	else if (strcmp(mode, "nxdomain") == 0)
		n = build_reply(NULL, 0, 3, ans, anslen);
	else
		n = build_reply(NULL, 0, 0, ans, anslen);

	if (n == 0)
		return (-1);
	return ((int)n);
}
