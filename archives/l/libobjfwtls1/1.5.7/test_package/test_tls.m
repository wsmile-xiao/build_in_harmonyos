/*
 * test_package for libobjfwtls1 1.5.7
 *
 * Genuinely exercises the ObjFWTLS public API without needing any network:
 *   1. +[OFX509Certificate supportsPEMFiles] must be true, which proves the
 *      OpenSSL backend was compiled into libobjfwtls (with --without-tls the
 *      class has no working implementation and this returns false).
 *   2. Feeding invalid PEM content to
 *      +[OFX509Certificate certificateChainFromPEMFileAtIRI:privateKeyIRI:]
 *      must be rejected by the real OpenSSL X.509 parser instead of a stub:
 *      either an OFException is thrown, or a nil/empty chain is returned.
 *      Only a non-empty chain without an exception means garbage was
 *      wrongly accepted and must fail.
 */
#include <stdbool.h>
#include <stdio.h>

#import <ObjFW/ObjFW.h>
#import <ObjFWTLS/ObjFWTLS.h>

// Do NOT #import the OpenSSL backend headers: the installed
// OFOpenSSLX509Certificate.h does `#import "OFX509Certificate.h"`
// (quoted), but OFX509Certificate.h installs into include/ObjFW/ while
// the backend header lives in include/ObjFWTLS/, so the quoted import
// fails with "'OFX509Certificate.h' file not found". Forward
// declarations suffice for the static-link anchor below
// ([OFOpenSSLX509Certificate class] / [OFOpenSSLTLSStream class]).
@class OFOpenSSLX509Certificate;
@class OFOpenSSLTLSStream;

extern int _ObjFWTLS_reference;

static bool checkRejectedWithContent(OFString *content, OFString *path);

int
main(void)
{
	void *pool = objc_autoreleasePoolPush();
	int ret = 0;

	/* Static-link anchor: pull the OpenSSL backend objects so their
	 * +load registers OFX509CertificateImplementation. Without a direct
	 * reference the static linker drops them (test only uses the base
	 * class), +load never runs and supportsPEMFiles reads as false.
	 * A --without-tls library has no such symbols, so the link itself
	 * fails loudly instead of silently reporting no PEM support. */
	{
		volatile Class keptX509 = [OFOpenSSLX509Certificate class];
		volatile Class keptStream = [OFOpenSSLTLSStream class];
		volatile int keptRef = _ObjFWTLS_reference;
		(void)keptX509;
		(void)keptStream;
		(void)keptRef;
	}

	/* 1. The OpenSSL backend must be compiled in. */
	if (![OFX509Certificate supportsPEMFiles]) {
		[OFStdErr writeString:
		    @"FAIL: OFX509Certificate does not support PEM files "
		    @"(TLS backend missing?)\n"];
		objc_autoreleasePoolPop(pool);
		return 1;
	}
	[OFStdOut writeString:
	    @"libobjfwtls OK: PEM support available (OpenSSL backend)\n"];

	/* 2. Invalid PEM content must be rejected by the real parser. */
	if (!checkRejectedWithContent(@"this is not a PEM file\n",
	    @"invalid_test.pem"))
		ret = 1;
	if (!checkRejectedWithContent(@"-----BEGIN CERTIFICATE-----\n"
	    @"!!!NOT-BASE64!!!\n"
	    @"-----END CERTIFICATE-----\n",
	    @"invalid_block.pem"))
		ret = 1;

	objc_autoreleasePoolPop(pool);
	return ret;
}

/* Write content to path, parse it, return true when correctly rejected. */
static bool
checkRejectedWithContent(OFString *content, OFString *path)
{
	void *pool = objc_autoreleasePoolPush();
	OFIRI *IRI;
	bool ok = false;
	const char *cpath = [path UTF8String];
	FILE *f = fopen(cpath, "w");
	if (f == NULL) {
		[OFStdErr writeFormat: @"FAIL: cannot write %@: fopen failed\n",
		    path];
		objc_autoreleasePoolPop(pool);
		return false;
	}
	fputs([content UTF8String], f);
	fclose(f);

	IRI = [OFIRI fileIRIWithPath: path];

	@try {
		OFArray *chain = [OFX509Certificate
		    certificateChainFromPEMFileAtIRI: IRI
						 privateKeyIRI: nil];
		if (chain == nil || [chain count] == 0) {
			[OFStdOut writeFormat:
			    @"libobjfwtls OK: invalid PEM rejected "
			    @"(empty chain for %@)\n", path];
			ok = true;
		} else {
			[OFStdErr writeFormat:
			    @"FAIL: invalid PEM accepted as %lu certs "
			    @"(%@) without an exception\n",
			    (unsigned long)[chain count], path];
			ok = false;
		}
	} @catch (OFException *e) {
		[OFStdOut writeFormat:
		    @"libobjfwtls OK: invalid PEM rejected (%@: %@)\n",
		    path, [e className]];
		ok = true;
	}

	remove(cpath);

	objc_autoreleasePoolPop(pool);
	return ok;
}
