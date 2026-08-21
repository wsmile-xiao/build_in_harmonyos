/* tests/test_mswrite_plugin.cpp — OHOS end-to-end test for the
 * abiword-plugin-mswrite module.
 *
 * Verifies (R34: substantive use of the package API):
 *   1. the plugin module dlopens and abi_plugin_register() fills XAP_ModuleInfo;
 *   2. the registered sniffer recognizes the Microsoft Write header
 *      (0x31 0xBE 0x00 0x00 0x00 0xAB) with UT_CONFIDENCE_PERFECT;
 *   3. getSuffixConfidence() advertises the ".wri" suffix;
 *   4. a synthetic Microsoft Write 1.x document (WRI layout below) is parsed
 *      end-to-end through IE_Imp::importFile and the extracted text
 *      contains the expected paragraphs.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>

#include "ut_types.h"
#include "ut_assert.h"
#include "ie_imp.h"
#include "pd_Document.h"
#include "xap_Module.h"
#include "gsf/gsf-input.h"

typedef int (*plugin_reg_fn) (XAP_ModuleInfo * mi);

static int failures = 0;

#define CHECK(cond, msg)                                                     \
	do {                                                                     \
		if (cond) {                                                          \
			printf ("  [OK] %s\n", msg);                                     \
		} else {                                                             \
			printf ("  [FAIL] %s\n", msg);                                   \
			failures++;                                                      \
		}                                                                    \
	} while (0)

/*
 * Minimal Microsoft Write 1.x (.wri) document.
 *
 * Layout (all little-endian):
 *   offset 0x00..0x7F : WRI file header (128 bytes)
 *     wIdent (0-1)     = 0xBE31            -> bytes 31 BE
 *     dty    (2-3)     = 0
 *     wTool  (4-5)     = 0xAB00            -> bytes 00 AB
 *     reserved1..4     = 0
 *     fcMac  (0x0E-11) = 0x80 + textlen    (end of text; 0x95)
 *     pnPara (0x12-13) = 4                 (PAP page, 4*0x80)
 *     pnFfntb(0x1C-1D) = 3                 (FFNTB page, 3*0x80)
 *     szSsht (30..93)  = 0 (64 bytes)
 *     pnMac  (0x5E-5F) = 5                 (last page; != pnFfntb -> has fonts)
 *   offset 0x80..0x94 : text  "Hello WRI\rSecond Line\r"  (fcMac = 0x95)
 *   offset 0x100..    : CHP table page (read_txt pnChar = (fcMac+127)/128 = 2)
 *     fc     (0-3)     = 0x80 (fcFirst)
 *     page[0x7f]       = 1 (cfod: one FOD)
 *     FOD0: fcLim(4-7) = fcMac, bfprop(8-9) = 0xffff (default props)
 *   offset 0x180..    : FFNTB font table (pnFfntb*0x80 = 3*0x80)
 *     word 0          = font count = 1
 *     cbFfn (2 bytes) = 10  (1 ffid + 9 name bytes)
 *     ffid (1 byte)   = 0
 *     name (9 bytes)  = "Helvetica"
 *     cbFfn (2 bytes) = 0   (end of table)
 *   offset 0x200..    : PAP table page (pnPara*0x80 = 4*0x80)
 *     fc     (0-3)     = 0x80 (fcFirst)
 *     page[0x7f]       = 1 (cfod: one FOD)
 *     FOD0: fcLim(4-7) = fcMac, bfprop(8-9) = 0xffff (default props)
 */
static unsigned char WRI_SAMPLE[0x280];

static void build_wri_sample (void)
{
	memset (WRI_SAMPLE, 0, sizeof (WRI_SAMPLE));

	const char text[] = "Hello WRI\rSecond Line\r";
	const UT_uint32 textlen = sizeof (text) - 1;          /* 21 */
	const UT_uint32 fcMac = 0x80 + textlen;               /* 0x95 */

	/* header */
	WRI_SAMPLE[0] = 0x31;  WRI_SAMPLE[1] = 0xBE;          /* wIdent 0xBE31 */
	WRI_SAMPLE[4] = 0x00;  WRI_SAMPLE[5] = 0xAB;          /* wTool 0xAB00 */
	WRI_SAMPLE[0x0E] = fcMac & 0xFF;                      /* fcMac LE32 */
	WRI_SAMPLE[0x0F] = (fcMac >> 8) & 0xFF;
	WRI_SAMPLE[0x10] = 0;
	WRI_SAMPLE[0x11] = 0;
	WRI_SAMPLE[0x12] = 4;  WRI_SAMPLE[0x13] = 0;          /* pnPara = 4 */
	WRI_SAMPLE[0x1C] = 3;  WRI_SAMPLE[0x1D] = 0;          /* pnFfntb = 3 */
	WRI_SAMPLE[0x5E] = 5;  WRI_SAMPLE[0x5F] = 0;          /* pnMac = 5 */

	/* text at 0x80 */
	memcpy (WRI_SAMPLE + 0x80, text, textlen);

	/* CHP table page at 0x100 (read_txt pnChar = 2) */
	unsigned char * chp = WRI_SAMPLE + 0x100;
	chp[0] = 0x80;  chp[1] = 0;  chp[2] = 0;  chp[3] = 0; /* fc = fcFirst */
	chp[4] = fcMac & 0xFF;                                /* FOD0 fcLim */
	chp[5] = (fcMac >> 8) & 0xFF;
	chp[6] = 0;  chp[7] = 0;
	chp[8] = 0xFF;  chp[9] = 0xFF;                        /* FOD0 bfprop = default */
	chp[0x7F] = 1;                                        /* cfod = 1 */

	/* FFNTB font table at 0x180 */
	unsigned char * ffntb = WRI_SAMPLE + 0x180;
	ffntb[0] = 1;  ffntb[1] = 0;                          /* font count = 1 */
	ffntb[2] = 10; ffntb[3] = 0;                          /* cbFfn = 10 */
	ffntb[4] = 0;                                         /* ffid = 0 */
	memcpy (ffntb + 5, "Helvetica", 9);                   /* name */
	ffntb[14] = 0; ffntb[15] = 0;                         /* end of table */

	/* PAP table page at 0x200 (pnPara * 0x80) */
	unsigned char * pap = WRI_SAMPLE + 0x200;
	pap[0] = 0x80;  pap[1] = 0;  pap[2] = 0;  pap[3] = 0; /* fc = fcFirst */
	pap[4] = fcMac & 0xFF;                                /* FOD0 fcLim */
	pap[5] = (fcMac >> 8) & 0xFF;
	pap[6] = 0;  pap[7] = 0;
	pap[8] = 0xFF;  pap[9] = 0xFF;                        /* FOD0 bfprop = default */
	pap[0x7F] = 1;                                        /* cfod = 1 */
}

int main (void)
{
	const char * so_path = getenv ("PLUGIN_SO");

	CHECK (so_path && so_path[0], "PLUGIN_SO env set");
	if (!so_path)
		return 1;

	build_wri_sample ();

	/* ---- 1. dlopen the plugin module ---- */
	void * handle = dlopen (so_path, RTLD_NOW | RTLD_LOCAL);
	CHECK (handle != 0, "dlopen(plugin .so)");
	if (!handle) {
		fprintf (stderr, "  dlopen error: %s\n", dlerror ());
		return 1;
	}

	plugin_reg_fn reg   = (plugin_reg_fn)dlsym (handle, "abi_plugin_register");
	plugin_reg_fn unreg = (plugin_reg_fn)dlsym (handle, "abi_plugin_unregister");
	CHECK (reg != 0, "dlsym(abi_plugin_register)");
	CHECK (unreg != 0, "dlsym(abi_plugin_unregister)");
	if (!reg || !unreg) {
		dlclose (handle);
		return 1;
	}

	XAP_ModuleInfo mi;
	memset (&mi, 0, sizeof (mi));

	int r = reg (&mi);
	CHECK (r == 1, "abi_plugin_register() returns 1");
	CHECK (mi.name && strcmp (mi.name, "MSWrite Importer") == 0, "XAP_ModuleInfo.name filled");
	CHECK (mi.desc && strstr (mi.desc, "Microsoft Write") != 0, "XAP_ModuleInfo.desc filled");
	CHECK (mi.version && strcmp (mi.version, ABI_BUILD_VERSION) == 0, "XAP_ModuleInfo.version == 3.0.8");

	/* ---- 2. locate the sniffer the plugin registered ---- */
	IE_ImpSniffer * sniffer = 0;
	for (size_t i = 0; i < IE_Imp::registeredImporters ().size (); i++) {
		IE_ImpSniffer * s = IE_Imp::registeredImporters ()[i];
		if (s && s->name () == "AbiMSWrite::MSWrite") {
			sniffer = s;
			break;
		}
	}
	CHECK (sniffer != 0, "sniffer 'AbiMSWrite::MSWrite' registered");

	if (sniffer) {
		/* ---- 3. recognize the WRI header ---- */
		/* 上游 recognizeContents 要求 iNumbytes > 8 */
		char hdr[16];
		memset (hdr, 0, sizeof (hdr));
		hdr[0] = 0x31;  hdr[1] = (char)0xBE;
		hdr[2] = 0;  hdr[3] = 0;
		hdr[4] = 0;  hdr[5] = (char)0xAB;
		UT_Confidence_t conf = sniffer->recognizeContents (hdr, sizeof (hdr));
		CHECK (conf == UT_CONFIDENCE_PERFECT, "recognizeContents(WRI header) == PERFECT");

		/* a non-WRI buffer must not be recognized */
		UT_Confidence_t conf2 = sniffer->recognizeContents ("XXXXXXXXXXXX", 12);
		CHECK (conf2 == UT_CONFIDENCE_ZILCH, "recognizeContents(garbage) == ZILCH");

		/* ---- 4. suffix confidence advertises .wri ---- */
		const IE_SuffixConfidence * sc = sniffer->getSuffixConfidence ();
		CHECK (sc != 0 && sc[0].suffix == "wri" &&
		       sc[0].confidence == UT_CONFIDENCE_PERFECT, "getSuffixConfidence() -> .wri PERFECT");

		/* ---- 5. end-to-end parse of a Microsoft Write document ---- */
		PD_Document doc;
		IE_Imp * imp = 0;
		UT_Error cerr = sniffer->constructImporter (&doc, &imp);
		CHECK (cerr == UT_OK && imp != 0, "constructImporter() ok");

		GsfInput * in = gsf_input_new_from_memory (WRI_SAMPLE, sizeof (WRI_SAMPLE));
		CHECK (in != 0, "GsfInput wrap ok");
		if (in && imp) {
			UT_Error ierr = imp->importFile (in);
			CHECK (ierr == UT_OK, "importFile(WRI sample) == UT_OK");

			std::string text = doc.getExtractedText ();
			CHECK (text.find ("Hello WRI") != std::string::npos, "extracted text contains 'Hello WRI'");
			CHECK (text.find ("Second Line") != std::string::npos, "extracted text contains 'Second Line'");
		}
		/* 无论 importFile/constructImporter 是否成功都释放 GsfInput
		 * （审查 P3：原实现仅在成功路径释放，imp==0 时泄漏） */
		if (in)
			gsf_input_free (in);
		delete imp;
	}

	/* ---- 6. unregister / unload ---- */
	int ur = unreg (&mi);
	CHECK (ur == 1, "abi_plugin_unregister() returns 1");
	dlclose (handle);

	if (failures == 0) {
		printf ("PASS: abiword-plugin-mswrite end-to-end test succeeded\n");
		return 0;
	}
	printf ("FAIL: %d check(s) failed\n", failures);
	return 1;
}
