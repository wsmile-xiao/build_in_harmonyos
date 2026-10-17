/* tests/test_pdb_plugin.cpp — OHOS end-to-end test for the
 * abiword-plugin-pdb module.
 *
 * Verifies (R34: substantive use of the package API):
 *   1. the plugin module dlopens and abi_plugin_register() fills XAP_ModuleInfo;
 *   2. the registered importer sniffer recognizes a PalmDoc (.pdb) header
 *      (type "TEXt" + creator "REAd") with UT_CONFIDENCE_PERFECT;
 *   3. getSuffixConfidence() advertises the ".pdb" suffix;
 *   4. a synthetic PalmDoc database (embedded below) is parsed end-to-end
 *      through IE_Imp::importFile and the extracted text contains the
 *      expected paragraphs;
 *   5. the exporter sniffer recognizes the ".pdb" suffix and exports a
 *      document through IE_Exp::writeDocument into a GsfOutput memory
 *      stream — the resulting PDB header / record structure is verified
 *      (type, creator, record count, record offsets, rec0 version);
 *   6. round-trip: the exported bytes are re-imported and yield the same
 *      text.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>

#include "ut_types.h"
#include "ut_assert.h"
#include "ie_imp.h"
#include "ie_exp.h"
#include "ie_exp_Text.h"
#include "pd_Document.h"
#include "xap_Module.h"
#include "gsf/gsf-input.h"
#include "gsf/gsf-output.h"

typedef int (*plugin_reg_fn) (XAP_ModuleInfo * mi);

static int failures = 0;
static int checks   = 0;

#define CHECK(cond, msg)                                                     \
	do {                                                                     \
		checks++;                                                            \
		if (cond) {                                                          \
			printf ("  [OK] %s\n", msg);                                     \
		} else {                                                             \
			printf ("  [FAIL] %s\n", msg);                                   \
			failures++;                                                      \
		}                                                                    \
	} while (0)

/* ------------------------------------------------------------------ */
/* big-endian readers (PDB stores all multi-byte fields big-endian)    */
/* ------------------------------------------------------------------ */

static unsigned read_u16be (const unsigned char * p)
{
	return ((unsigned)p[0] << 8) | (unsigned)p[1];
}

static unsigned read_u32be (const unsigned char * p)
{
	return ((unsigned)p[0] << 24) | ((unsigned)p[1] << 16) |
	       ((unsigned)p[2] << 8) | (unsigned)p[3];
}

/* ------------------------------------------------------------------ */
/* Synthetic PalmDoc (.pdb) database — plain text, 1 text record.      */
/* Header (78) + record list (2 x 8) + rec0 @100 (16) + text @116.     */
/* ------------------------------------------------------------------ */

static const unsigned char PDB_SAMPLE[138] = {
	0x74, 0x65, 0x73, 0x74, 0x2e, 0x70, 0x64, 0x62, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x54, 0x45, 0x58, 0x74, 0x52, 0x45, 0x41, 0x64, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x64, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x74, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x16,
	0x00, 0x01, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x48, 0x65, 0x6c, 0x6c,
	0x6f, 0x20, 0x50, 0x44, 0x42, 0x0d, 0x53, 0x65, 0x63, 0x6f, 0x6e, 0x64,
	0x20, 0x4c, 0x69, 0x6e, 0x65, 0x0d,
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
	CHECK (mi.name && strcmp (mi.name, "PalmDoc Importer/Exporter") == 0, "XAP_ModuleInfo.name filled");
	CHECK (mi.desc && strstr (mi.desc, "PalmDoc") != 0, "XAP_ModuleInfo.desc filled");
	CHECK (mi.version && strcmp (mi.version, ABI_BUILD_VERSION) == 0, "XAP_ModuleInfo.version == 3.0.8");

	/* ---- 2. locate the importer sniffer the plugin registered ---- */
	IE_ImpSniffer * impSniffer = 0;
	for (size_t i = 0; i < IE_Imp::registeredImporters ().size (); i++) {
		IE_ImpSniffer * s = IE_Imp::registeredImporters ()[i];
		if (s && s->name () == "AbiPalmDoc::PalmDoc") {
			impSniffer = s;
			break;
		}
	}
	CHECK (impSniffer != 0, "importer sniffer 'AbiPalmDoc::PalmDoc' registered");

	/* ---- 3. locate the exporter sniffer ---- */
	IE_ExpSniffer * expSniffer = 0;
	for (size_t i = 0; i < IE_Exp::registeredExporters ().size (); i++) {
		IE_ExpSniffer * s = IE_Exp::registeredExporters ()[i];
		if (s && s->name () == "AbiPalmDoc::PalmDoc") {
			expSniffer = s;
			break;
		}
	}
	CHECK (expSniffer != 0, "exporter sniffer 'AbiPalmDoc::PalmDoc' registered");

	if (impSniffer) {
		/* ---- 4. recognize the PalmDoc header ---- */
		UT_Confidence_t conf = impSniffer->recognizeContents (
			reinterpret_cast<const char *> (PDB_SAMPLE),
			sizeof (PDB_SAMPLE));
		CHECK (conf == UT_CONFIDENCE_PERFECT, "recognizeContents(PDB header) == PERFECT");

		/* a non-PDB buffer must not be recognized */
		UT_Confidence_t conf2 = impSniffer->recognizeContents ("XXXXXXXX", 8);
		CHECK (conf2 == UT_CONFIDENCE_ZILCH, "recognizeContents(garbage) == ZILCH");

		/* short buffer must not be recognized */
		UT_Confidence_t conf3 = impSniffer->recognizeContents (
			reinterpret_cast<const char *> (PDB_SAMPLE), 16);
		CHECK (conf3 == UT_CONFIDENCE_ZILCH, "recognizeContents(short buffer) == ZILCH");

		/* ---- 5. suffix confidence advertises .pdb ---- */
		const IE_SuffixConfidence * sc = impSniffer->getSuffixConfidence ();
		CHECK (sc != 0 && sc[0].suffix == "pdb" &&
		       sc[0].confidence == UT_CONFIDENCE_PERFECT, "getSuffixConfidence() -> .pdb PERFECT");

		/* ---- 6. end-to-end parse of the synthetic PalmDoc file ---- */
		PD_Document doc;
		IE_Imp * imp = 0;
		UT_Error cerr = impSniffer->constructImporter (&doc, &imp);
		CHECK (cerr == UT_OK && imp != 0, "constructImporter() ok");

		GsfInput * in = gsf_input_new_from_memory (PDB_SAMPLE, sizeof (PDB_SAMPLE));
		CHECK (in != 0, "GsfInput wrap ok");
		if (in && imp) {
			UT_Error ierr = imp->importFile (in);
			CHECK (ierr == UT_OK, "importFile(PDB sample) == UT_OK");

			std::string text = doc.getExtractedText ();
			CHECK (doc.getStruxCount () >= 2, "document got Section + Block strux");
			CHECK (doc.getSpanCount () >= 2, "document got multiple text spans");
			CHECK (text.find ("Hello PDB") != std::string::npos, "extracted text contains 'Hello PDB'");
			CHECK (text.find ("Second Line") != std::string::npos, "extracted text contains 'Second Line'");

			gsf_input_free (in);
		}
		delete imp;
	}

	/* ---- 7. export: build a small document and write a .pdb ---- */
	IE_Exp * exp = 0;
	if (expSniffer) {
		CHECK (expSniffer->recognizeSuffix (".pdb"), "exporter recognizeSuffix('.pdb') == true");
		CHECK (!expSniffer->recognizeSuffix (".txt"), "exporter recognizeSuffix('.txt') == false");

		static const UT_UCSChar HELLO[] = {
			'H','e','l','l','o',' ','P','D','B','\r',
			'S','e','c','o','n','d',' ','L','i','n','e','\r'
		};
		PD_Document edoc;
		edoc.appendStrux (PTX_Section, NULL);
		edoc.appendStrux (PTX_Block, NULL);
		edoc.appendSpan (HELLO, 22);

		UT_Error eerr = expSniffer->constructExporter (&edoc, &exp);
		CHECK (eerr == UT_OK && exp != 0, "constructExporter() ok");

		GsfOutput * out = gsf_output_new_from_memory ();
		CHECK (out != 0, "GsfOutput wrap ok");
		if (exp && out) {
			exp->setOutput (out, "sample.pdb");
			UT_Error werr = exp->writeDocument ();
			CHECK (werr == UT_OK, "writeDocument() == UT_OK");

			gsf_off_t osize = gsf_output_get_size (out);
			const unsigned char * odata = gsf_output_get_data (out);

			CHECK (osize >= 78, "exported PDB has at least a 78-byte header");
			if (osize >= 78) {
				CHECK (memcmp (odata + 60, "TEXt", 4) == 0, "exported type == 'TEXt'");
				CHECK (memcmp (odata + 64, "REAd", 4) == 0, "exported creator == 'REAd'");
				CHECK (memcmp (odata, "sample.pdb", 10) == 0, "exported DB name == 'sample.pdb'");
				CHECK (read_u16be (odata + 76) == 2, "exported numRecords == 2 (rec0 + 1 text)");
				CHECK (read_u32be (odata + 78) == 0x1000, "record list[0].offset == 4096 (rec0)");
			}
			if (osize >= 96) {
				CHECK (read_u32be (odata + 86) == 0x1010, "record list[1].offset == 4112 (text)");
			}
			if (osize >= 4098) {
				CHECK (read_u16be (odata + 4096) == 2, "rec0 version == 2 (compressed)");
			}
			if (osize > 4112) {
				/* the compressed text record must contain data */
				bool nonempty = false;
				for (gsf_off_t i = 4112; i < osize; i++)
					if (odata[i] != 0)
						nonempty = true;
				CHECK (nonempty, "compressed text record is non-empty");
			}

			/* ---- 8. round-trip: re-import the exported bytes ---- */
			GsfInput * rin = gsf_input_new_from_memory (odata, (size_t)osize);
			if (rin) {
				PD_Document rdoc;
				IE_Imp * rimp = 0;
				if (impSniffer) {
					impSniffer->constructImporter (&rdoc, &rimp);
					UT_Error rierr = rimp ? rimp->importFile (rin) : UT_ERROR;
					CHECK (rierr == UT_OK, "round-trip importFile(exported PDB) == UT_OK");
					std::string rtext = rdoc.getExtractedText ();
					CHECK (rtext.find ("Hello PDB") != std::string::npos, "round-trip text contains 'Hello PDB'");
					CHECK (rtext.find ("Second Line") != std::string::npos, "round-trip text contains 'Second Line'");
					delete rimp;
				}
				gsf_input_free (rin);
			}
			gsf_output_free (out);
		}
		delete exp;
	}

	/* ---- 8b. failure contract: base IE_Exp_Text must not fake success
	 *      (regression for review: _writeBytes used to return length even
	 *      with no output stream / failed write, so writeDocument()
	 *      silently succeeded with empty output) ---- */
	{
		static const UT_UCSChar TXT[] = { 'H','i','\r' };
		PD_Document bdoc;
		bdoc.appendStrux (PTX_Section, NULL);
		bdoc.appendStrux (PTX_Block, NULL);
		bdoc.appendSpan (TXT, 3);

		/* no output stream attached (setOutput never called) */
		IE_Exp_Text * baseExp = new IE_Exp_Text (&bdoc);
		UT_uint32 n = baseExp->_writeBytes (reinterpret_cast<const UT_Byte *> ("abc"), 3);
		CHECK (n == 0, "base _writeBytes() without output stream returns 0");
		UT_Error bwerr = baseExp->writeDocument ();
		CHECK (bwerr == UT_IE_IMPORTERROR, "base writeDocument() without output stream == UT_IE_IMPORTERROR");
		delete baseExp;

		/* with an output stream attached, the same path writes and reports length */
		GsfOutput * bout = gsf_output_new_from_memory ();
		CHECK (bout != 0, "base contract GsfOutput wrap ok");
		if (bout) {
			IE_Exp_Text * okExp = new IE_Exp_Text (&bdoc);
			okExp->setOutput (bout, "contract.txt");
			UT_uint32 n2 = okExp->_writeBytes (reinterpret_cast<const UT_Byte *> ("xyz"), 3);
			CHECK (n2 == 3, "base _writeBytes() with output stream returns length");
			UT_Error owerr = okExp->writeDocument ();
			CHECK (owerr == UT_OK, "base writeDocument() with output stream == UT_OK");
			CHECK (gsf_output_get_size (bout) >= 3, "base writeDocument() actually wrote bytes");
			delete okExp;
			gsf_output_free (bout);
		}
	}

	/* ---- 9. unregister / unload ---- */
	int ur = unreg (&mi);
	CHECK (ur == 1, "abi_plugin_unregister() returns 1");
	dlclose (handle);

	if (failures == 0) {
		printf ("PASS: abiword-plugin-pdb end-to-end test succeeded (%d/%d checks)\n",
		        checks - failures, checks);
		return 0;
	}
	printf ("FAIL: %d/%d checks failed\n", failures, checks);
	return 1;
}
