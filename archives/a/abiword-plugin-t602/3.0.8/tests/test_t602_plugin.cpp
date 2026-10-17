/* tests/test_t602_plugin.cpp — OHOS end-to-end test for the
 * abiword-plugin-t602 module.
 *
 * Verifies (R34: substantive use of the package API):
 *   1. the plugin module dlopens and abi_plugin_register() fills XAP_ModuleInfo;
 *   2. the registered sniffer recognizes the T602 file header
 *      ("@CT " magic) with UT_CONFIDENCE_PERFECT;
 *   3. getSuffixConfidence() advertises the ".602" suffix;
 *   4. a synthetic T602 document (embed below) is parsed end-to-end
 *      through IE_Imp::importFile and the extracted text contains the
 *      expected paragraphs; a ".HE Page #" header line produces a
 *      PTO_Field page-number object.
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
static int passes   = 0;

#define CHECK(cond, msg)                                                     \
	do {                                                                     \
		if (cond) {                                                          \
			printf ("  [OK] %s\n", msg);                                     \
			passes++;                                                        \
		} else {                                                             \
			printf ("  [FAIL] %s\n", msg);                                   \
			failures++;                                                      \
		}                                                                    \
	} while (0)

/* Synthetic T602 (602Text) document.  T602 is a line-oriented format with
 * dot commands ('.' / '@' at line start):
 *   @CT 1        charset 1 = CP852
 *   Hello T602   first paragraph
 *   more text    second paragraph
 *   .HE Page #   document header (page-number field on '#')
 *   Second       third paragraph (rendered after the header)
 * '\r' = 0x0d = T602 hard line break / paragraph separator.
 */
static const char T602_SAMPLE[] =
	"@CT 1\r"
	"Hello T602\r"
	"more text\r"
	".HE Page #\r"
	"Second\r";

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
	CHECK (mi.name && strcmp (mi.name, "T602 Importer") == 0, "XAP_ModuleInfo.name filled");
	CHECK (mi.desc && strstr (mi.desc, "T602") != 0, "XAP_ModuleInfo.desc filled");
	CHECK (mi.version && strcmp (mi.version, ABI_BUILD_VERSION) == 0, "XAP_ModuleInfo.version == 3.0.8");

	/* ---- 2. locate the sniffer the plugin registered ---- */
	IE_ImpSniffer * sniffer = 0;
	for (size_t i = 0; i < IE_Imp::registeredImporters ().size (); i++) {
		IE_ImpSniffer * s = IE_Imp::registeredImporters ()[i];
		if (s && s->name () == "AbiT602::T602") {
			sniffer = s;
			break;
		}
	}
	CHECK (sniffer != 0, "sniffer 'AbiT602::T602' registered");

	if (sniffer) {
		/* ---- 3. recognize the T602 header ---- */
		const char * hdr = "@CT 1 charset";
		UT_Confidence_t conf = sniffer->recognizeContents (hdr, (UT_uint32)strlen (hdr));
		CHECK (conf == UT_CONFIDENCE_PERFECT, "recognizeContents('@CT ' header) == PERFECT");

		/* a non-T602 buffer must not be recognized */
		UT_Confidence_t conf2 = sniffer->recognizeContents ("XXXXXXXX", 8);
		CHECK (conf2 == UT_CONFIDENCE_ZILCH, "recognizeContents(garbage) == ZILCH");

		/* ---- 4. suffix confidence advertises .602 ---- */
		const IE_SuffixConfidence * sc = sniffer->getSuffixConfidence ();
		CHECK (sc != 0 && sc[0].suffix == "602" &&
		       sc[0].confidence == UT_CONFIDENCE_PERFECT, "getSuffixConfidence() -> .602 PERFECT");

		/* ---- 4b. dialog labels ---- */
		const char * ddesc = 0, * dsuffix = 0;
		IEFileType dft = IEFT_Unknown;
		bool dlg = sniffer->getDlgLabels (&ddesc, &dsuffix, &dft);
		CHECK (dlg && ddesc && strstr (ddesc, "T602") != 0, "getDlgLabels() -> T602 desc");

		/* ---- 5. end-to-end parse of a T602 document ---- */
		PD_Document doc;
		IE_Imp * imp = 0;
		UT_Error cerr = sniffer->constructImporter (&doc, &imp);
		CHECK (cerr == UT_OK && imp != 0, "constructImporter() ok");

		GsfInput * in = gsf_input_new_from_memory (T602_SAMPLE, sizeof (T602_SAMPLE) - 1);
		CHECK (in != 0, "GsfInput wrap ok");
		if (in && imp) {
			UT_Error ierr = imp->importFile (in);
			CHECK (ierr == UT_OK, "importFile(T602 sample) == UT_OK");

			std::string text = doc.getExtractedText ();
			CHECK (doc.getStruxCount () >= 2, "document got Section + Block strux");
			CHECK (doc.getSpanCount () >= 2, "document got multiple text spans");
			CHECK (doc.getFmtCount () >= 1, "document got text-property events (appendFmt)");
			CHECK (doc.hasObject (PTO_Field), "header '#': page-number PTO_Field object appended");
			CHECK (text.find ("Hello T602") != std::string::npos, "extracted text contains 'Hello T602'");
			CHECK (text.find ("more text") != std::string::npos, "extracted text contains 'more text'");
			CHECK (text.find ("Second") != std::string::npos, "extracted text contains 'Second'");

			gsf_input_free (in);
		}
		delete imp;
	}

	/* ---- 6. unregister / unload ---- */
	int ur = unreg (&mi);
	CHECK (ur == 1, "abi_plugin_unregister() returns 1");
	dlclose (handle);

	printf ("RESULT: %d passed, %d failed\n", passes, failures);
	if (failures == 0) {
		printf ("PASS: abiword-plugin-t602 end-to-end test succeeded\n");
		return 0;
	}
	printf ("FAIL: %d check(s) failed\n", failures);
	return 1;
}
