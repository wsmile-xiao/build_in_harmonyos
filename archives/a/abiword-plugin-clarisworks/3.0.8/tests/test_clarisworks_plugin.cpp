/* tests/test_clarisworks_plugin.cpp — OHOS end-to-end test for the
 * abiword-plugin-clarisworks module.
 *
 * Verifies (R34: substantive use of the package API):
 *   1. the plugin module dlopens and abi_plugin_register() fills XAP_ModuleInfo;
 *   2. the registered sniffer recognizes the ClarisWorks 5 header
 *      (version byte 5 + "BOBO" magic) with UT_CONFIDENCE_PERFECT;
 *   3. getSuffixConfidence() advertises the ".cwk" suffix;
 *   4. a synthetic ClarisWorks 5 document (embed below) is parsed
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

/* Synthetic ClarisWorks 5 (.cwk) document:
 *   bytes 0..3   : version 5 (0x05) + filler "MAR"
 *   bytes 4..7   : "BOBO" magic
 *   bytes 8..15  : ETBL block + offset2 (=0, little-endian)
 *   bytes 16..   : text "Hello CWK" CR "Second Line" CR
 *   last 24 bytes: ETBL + offset1 (=8) + padding (the parser reads the
 *   tail through the GsfInput loop, so it appears in the extracted text).
 */
static const unsigned char CWK_SAMPLE[62] = {
	0x05, 0x4d, 0x41, 0x52, 0x42, 0x4f, 0x42, 0x4f, 0x45, 0x54, 0x42, 0x4c,
	0x00, 0x00, 0x00, 0x00, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x20, 0x43, 0x57,
	0x4b, 0x0d, 0x53, 0x65, 0x63, 0x6f, 0x6e, 0x64, 0x20, 0x4c, 0x69, 0x6e,
	0x65, 0x0d, 0x45, 0x54, 0x42, 0x4c, 0x08, 0x00, 0x00, 0x00, 0x20, 0x20,
	0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20,
	0x20, 0x20,
};

int main (void)
{
	const char * so_path = getenv ("PLUGIN_SO");

	CHECK (so_path && so_path[0], "PLUGIN_SO env set");
	if (!so_path)
		return 1;

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
	CHECK (mi.name && strcmp (mi.name, "ClarisWorks Importer") == 0, "XAP_ModuleInfo.name filled");
	CHECK (mi.desc && strstr (mi.desc, "ClarisWorks") != 0, "XAP_ModuleInfo.desc filled");
	CHECK (mi.version && strcmp (mi.version, ABI_BUILD_VERSION) == 0, "XAP_ModuleInfo.version == 3.0.8");

	/* ---- 2. locate the sniffer the plugin registered ---- */
	IE_ImpSniffer * sniffer = 0;
	for (size_t i = 0; i < IE_Imp::registeredImporters ().size (); i++) {
		IE_ImpSniffer * s = IE_Imp::registeredImporters ()[i];
		if (s && s->name () == "AbiClarisWorks::CWK") {
			sniffer = s;
			break;
		}
	}
	CHECK (sniffer != 0, "sniffer 'AbiClarisWorks::CWK' registered");

	if (sniffer) {
		/* ---- 3. recognize the ClarisWorks 5 header ---- */
		char hdr[8];
		hdr[0] = 5;                 /* CW_HANDLED_VERSION */
		hdr[1] = 'M'; hdr[2] = 'A'; hdr[3] = 'R';
		hdr[4] = 'B'; hdr[5] = 'O'; hdr[6] = 'B'; hdr[7] = 'O';
		UT_Confidence_t conf = sniffer->recognizeContents (hdr, 8);
		CHECK (conf == UT_CONFIDENCE_PERFECT, "recognizeContents(CWK5 header) == PERFECT");

		/* a non-CWK buffer must not be recognized */
		UT_Confidence_t conf2 = sniffer->recognizeContents ("XXXXXXXX", 8);
		CHECK (conf2 == UT_CONFIDENCE_ZILCH, "recognizeContents(garbage) == ZILCH");

		/* ---- 4. suffix confidence advertises .cwk ---- */
		const IE_SuffixConfidence * sc = sniffer->getSuffixConfidence ();
		CHECK (sc != 0 && sc[0].suffix == "cwk" &&
		       sc[0].confidence == UT_CONFIDENCE_PERFECT, "getSuffixConfidence() -> .cwk PERFECT");

		/* ---- 5. end-to-end parse of a ClarisWorks 5 document ---- */
		PD_Document doc;
		IE_Imp * imp = 0;
		UT_Error cerr = sniffer->constructImporter (&doc, &imp);
		CHECK (cerr == UT_OK && imp != 0, "constructImporter() ok");

		GsfInput * in = gsf_input_new_from_memory (CWK_SAMPLE, sizeof (CWK_SAMPLE));
		CHECK (in != 0, "GsfInput wrap ok");
		if (in && imp) {
			UT_Error ierr = imp->importFile (in);
			CHECK (ierr == UT_OK, "importFile(CWK sample) == UT_OK");

			std::string text = doc.getExtractedText ();
			CHECK (doc.getStruxCount () >= 2, "document got Section + Block strux");
			CHECK (doc.getSpanCount () >= 2, "document got multiple text spans");
			CHECK (text.find ("Hello CWK") != std::string::npos, "extracted text contains 'Hello CWK'");
			CHECK (text.find ("Second Line") != std::string::npos, "extracted text contains 'Second Line'");

			gsf_input_free (in);
		}
		delete imp;
	}

	/* ---- 6. unregister / unload ---- */
	int ur = unreg (&mi);
	CHECK (ur == 1, "abi_plugin_unregister() returns 1");
	dlclose (handle);

	if (failures == 0) {
		printf ("PASS: abiword-plugin-clarisworks end-to-end test succeeded\n");
		return 0;
	}
	printf ("FAIL: %d check(s) failed\n", failures);
	return 1;
}
