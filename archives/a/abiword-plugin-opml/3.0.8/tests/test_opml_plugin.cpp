/* tests/test_opml_plugin.cpp — OHOS end-to-end test for the
 * abiword-plugin-opml module.
 *
 * Verifies (R34: substantive use of the package API):
 *   1. the plugin module dlopens and abi_plugin_register() fills XAP_ModuleInfo;
 *   2. the registered sniffer recognizes an OPML document header
 *      ("<opml") with UT_CONFIDENCE_PERFECT;
 *   3. getSuffixConfidence() advertises the ".opml" suffix;
 *   4. a real OPML 2.0 document is parsed end-to-end through
 *      IE_Imp::importFile: sections/blocks struxes are appended, outline
 *      titles are extracted as text, hyperlinks are created for outlines
 *      carrying a url, bullet lists are registered and the head metadata
 *      (dc.title / dc.creator) is stored on the document.
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

/* A real OPML 2.0 document (as produced by feed readers). */
static const char OPML_SAMPLE[] =
	"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
	"<opml version=\"2.0\">\n"
	"  <head>\n"
	"    <title>My Subscriptions</title>\n"
	"    <ownerName>Alice</ownerName>\n"
	"  </head>\n"
	"  <body>\n"
	"    <outline text=\"News\" url=\"http://example.com/news\" />\n"
	"    <outline text=\"Tech\">\n"
	"      <outline text=\"Deep Learning\" url=\"https://example.org/dl\" />\n"
	"    </outline>\n"
	"    <outline text=\"Plain Item\" />\n"
	"  </body>\n"
	"</opml>\n";

int main (void)
{
	const char * so_path = getenv ("PLUGIN_SO");

	CHECK (so_path && so_path[0], "PLUGIN_SO env set");
	if (!so_path || !so_path[0])
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
	CHECK (mi.name && strcmp (mi.name, "OPML Importer") == 0, "XAP_ModuleInfo.name filled");
	CHECK (mi.desc && strstr (mi.desc, "OPML") != 0, "XAP_ModuleInfo.desc filled");
	CHECK (mi.version && strcmp (mi.version, ABI_BUILD_VERSION) == 0, "XAP_ModuleInfo.version == 3.0.8");

	/* ---- 2. locate the sniffer the plugin registered ---- */
	IE_ImpSniffer * sniffer = 0;
	for (size_t i = 0; i < IE_Imp::registeredImporters ().size (); i++) {
		IE_ImpSniffer * s = IE_Imp::registeredImporters ()[i];
		if (s && s->name () == "AbiOPML::OPML") {
			sniffer = s;
			break;
		}
	}
	CHECK (sniffer != 0, "sniffer 'AbiOPML::OPML' registered");

	if (sniffer) {
		/* ---- 3. recognize the OPML header ---- */
		UT_Confidence_t conf = sniffer->recognizeContents ("<opml version=\"2.0\">", 20);
		CHECK (conf == UT_CONFIDENCE_PERFECT, "recognizeContents('<opml...') == PERFECT");

		/* a non-OPML buffer must not be recognized */
		UT_Confidence_t conf2 = sniffer->recognizeContents ("<html><body>hi</body></html>", 28);
		CHECK (conf2 == UT_CONFIDENCE_ZILCH, "recognizeContents(garbage) == ZILCH");

		/* ---- 4. suffix confidence advertises .opml ---- */
		const IE_SuffixConfidence * sc = sniffer->getSuffixConfidence ();
		CHECK (sc != 0 && sc[0].suffix == "opml" &&
		       sc[0].confidence == UT_CONFIDENCE_PERFECT, "getSuffixConfidence() -> .opml PERFECT");

		/* ---- 5. end-to-end parse of a real OPML document ---- */
		PD_Document doc;
		IE_Imp * imp = 0;
		UT_Error cerr = sniffer->constructImporter (&doc, &imp);
		CHECK (cerr == UT_OK && imp != 0, "constructImporter() ok");

		GsfInput * in = gsf_input_new_from_memory (OPML_SAMPLE, sizeof (OPML_SAMPLE) - 1);
		CHECK (in != 0, "GsfInput wrap ok");
		if (in && imp) {
			UT_Error ierr = imp->importFile (in);
			CHECK (ierr == UT_OK, "importFile(OPML sample) == UT_OK");

			std::string text = doc.getExtractedText ();
			CHECK (doc.getStruxCount () >= 5, "document got Section + 4 Block struxes");
			CHECK (doc.getSpanCount () >= 7, "document got multiple text spans");
			CHECK (text.find ("News") != std::string::npos, "extracted text contains 'News'");
			CHECK (text.find ("Tech") != std::string::npos, "extracted text contains 'Tech'");
			CHECK (text.find ("Deep Learning") != std::string::npos, "extracted text contains 'Deep Learning'");
			CHECK (text.find ("Plain Item") != std::string::npos, "extracted text contains 'Plain Item'");

			/* 2 outlines carry a url -> 2 hyperlink open/close pairs = 4 PTO_Hyperlink objects */
			CHECK (doc.countObjects (PTO_Hyperlink) == 4, "4 PTO_Hyperlink objects (2 url outlines)");
			/* every outline gets a PTO_Field list-label object -> 4 */
			CHECK (doc.countObjects (PTO_Field) == 4, "4 PTO_Field list-label objects");

			/* 2 bullet lists are registered (root + nested) */
			CHECK (doc.getListCount () == 2, "2 fl_AutoNum lists registered");

			/* head metadata is stored */
			const char * title   = doc.getMetaDataProp ("dc.title");
			const char * creator = doc.getMetaDataProp ("dc.creator");
			CHECK (title && strcmp (title, "My Subscriptions") == 0, "metadata dc.title == 'My Subscriptions'");
			CHECK (creator && strcmp (creator, "Alice") == 0, "metadata dc.creator == 'Alice'");

			gsf_input_free (in);
		} else if (in) {
			/* imp construction failed: do not leak the wrapped input */
			gsf_input_free (in);
		}
		delete imp;
	}

	/* ---- 6. unregister / unload ---- */
	int ur = unreg (&mi);
	CHECK (ur == 1, "abi_plugin_unregister() returns 1");
	dlclose (handle);

	if (failures == 0) {
		printf ("PASS: abiword-plugin-opml end-to-end test succeeded\n");
		return 0;
	}
	printf ("FAIL: %d check(s) failed\n", failures);
	return 1;
}
