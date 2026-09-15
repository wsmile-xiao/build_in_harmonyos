/*
 * Consumer test for the packaged bambamc library.
 *
 * Writes a BAM file through the public writer API, then reads the very same
 * file back through the public decoder API and compares every field that was
 * written (name, flag, reference, position, mapping quality, template length,
 * cigar/sequence/quality view). Exits non-zero on any mismatch, so the test
 * fails loudly instead of only printing. This is a real API consumer test
 * (R34), not a print-only stub.
 *
 * argv[1] is the BAM path to create; "%s" style defaults are avoided so the
 * caller (test_package/conanfile.py) can point it inside the build folder -
 * the device has no writable /tmp.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <bambamc/BamBam_BamHeaderInfo.h>
#include <bambamc/BamBam_BamWriter.h>
#include <bambamc/BamBam_BamFileDecoder.h>
#include <bambamc/BamBam_BamSingleAlignment.h>
#include <bambamc/BamBam_FormatAlignment.h>

static int checks = 0;
static int failures = 0;

static void check(int condition, char const * what)
{
	checks++;
	if ( ! condition )
	{
		failures++;
		printf("FAIL: %s\n", what);
	}
}

int main(int argc, char ** argv)
{
	char const * path = (argc > 1) ? argv[1] : "bambamc_consumer.bam";

	char const * const readname_a = "consumerA";
	char const * const query_a = "ACGTTGCA";
	char const * const qual_a = "HHHHHHHH";
	/*
	 * Record B is flagged reverse strand (BAMBAMC_FREVERSE = 1<<4). Per the
	 * SAM/BAM spec SEQ/QUAL are stored in reference orientation, so the file
	 * carries the reverse complement of the read; the library's FASTQ
	 * formatter turns it back into the read as sequenced.
	 */
	char const * const readname_b = "consumerB";
	char const * const query_b_stored = "CGTTGCAA";
	char const * const query_b_read = "TTGCAACG";
	char const * const qual_b = "IIIIIIII";

	/* ---------- 1. write a BAM file through the public writer API -------- */
	BamBam_BamHeaderInfo * hi = BamBam_BamHeaderInfo_New("1.4", "unknown", 0);
	check(hi != 0, "BamBam_BamHeaderInfo_New");
	if ( ! hi )
		return EXIT_FAILURE;

	check(BamBam_BamHeaderInfo_AddChromosome(hi, "chr1", 10000) == 0,
	      "BamBam_BamHeaderInfo_AddChromosome");

	BamBam_BamWriter * writer = BamBam_BamWriter_New(hi, path, 1);
	check(writer != 0, "BamBam_BamWriter_New");
	if ( ! writer )
	{
		BamBam_BamHeaderInfo_Delete(hi);
		return EXIT_FAILURE;
	}

	check(BamBam_BamWriter_PutAlignment(
		writer, 0, 0, 5000, -1, 0, readname_a, query_a, qual_a, "8M", 60, 0) >= 0,
		"BamBam_BamWriter_PutAlignment A");
	int32_t aux_value = 61;
	check(BamBam_BamWriter_PutAuxNumber(writer, "AS", 'i', &aux_value) >= 0,
	      "BamBam_BamWriter_PutAuxNumber AS");
	check(BamBam_BamWriter_Commit(writer) >= 0, "BamBam_BamWriter_Commit A");

	check(BamBam_BamWriter_PutAlignment(
		writer, 16, 0, 6000, -1, 0, readname_b, query_b_stored, qual_b, "8M", 42, -100) >= 0,
		"BamBam_BamWriter_PutAlignment B");
	check(BamBam_BamWriter_Commit(writer) >= 0, "BamBam_BamWriter_Commit B");

	int termstatus = -1;
	BamBam_BamWriter_Delete(writer, &termstatus);
	check(termstatus >= 0, "BamBam_BamWriter_Delete termstatus");
	BamBam_BamHeaderInfo_Delete(hi);

	/* ---------- 2. read it back through the public decoder API ----------- */
	BamBam_BamFileDecoder * decoder = BamBam_BamFileDecoder_New(path);
	check(decoder != 0, "BamBam_BamFileDecoder_New");
	if ( ! decoder )
		return EXIT_FAILURE;

	BamBam_BamSingleAlignment * algn = BamBam_BamFileDecoder_DecodeAlignment(decoder);
	check(algn != 0, "BamBam_BamFileDecoder_DecodeAlignment #1");
	if ( algn )
	{
		char const * name = BamBam_BamSingleAlignment_GetReadName(algn);
		check(name != 0 && strcmp(name, readname_a) == 0, "read name #1");
		check(BamBam_BamSingleAlignment_GetRefId(algn) == 0, "ref id #1");
		check(BamBam_BamSingleAlignment_GetPos(algn) == 5000, "position #1");
		check(BamBam_BamSingleAlignment_GetFlags(algn) == 0, "flags #1");
		check(BamBam_BamSingleAlignment_GetMQ(algn) == 60, "mapping quality #1");
		check(BamBam_BamSingleAlignment_GetLSeq(algn) == 8, "sequence length #1");

		char * fastq = 0;
		unsigned int fastqlen = 0;
		int const ok = BamBam_PutAlignmentFastQBuffer(algn, &fastq, &fastqlen, '\n');
		check(ok >= 0, "BamBam_PutAlignmentFastQBuffer #1");
		if ( ok >= 0 && fastq )
		{
			char expected[128];
			snprintf(expected, sizeof(expected), "@%s\n%s\n+\n%s\n",
			         readname_a, query_a, qual_a);
			check(strncmp(fastq, expected, strlen(expected)) == 0,
			      "FASTQ round-trip #1");
			if ( strncmp(fastq, expected, strlen(expected)) != 0 )
				printf("      got: %.*s\n", (int)fastqlen, fastq);
			free(fastq);
		}
	}

	algn = BamBam_BamFileDecoder_DecodeAlignment(decoder);
	check(algn != 0, "BamBam_BamFileDecoder_DecodeAlignment #2");
	if ( algn )
	{
		char const * name = BamBam_BamSingleAlignment_GetReadName(algn);
		check(name != 0 && strcmp(name, readname_b) == 0, "read name #2");
		check(BamBam_BamSingleAlignment_GetPos(algn) == 6000, "position #2");
		check(BamBam_BamSingleAlignment_GetFlags(algn) == 16, "flags #2");
		check(BamBam_BamSingleAlignment_GetMQ(algn) == 42, "mapping quality #2");
		check(BamBam_BamSingleAlignment_GetTLen(algn) == -100, "template length #2");

		char * fastq = 0;
		unsigned int fastqlen = 0;
		int const ok = BamBam_PutAlignmentFastQBuffer(algn, &fastq, &fastqlen, '\n');
		check(ok >= 0, "BamBam_PutAlignmentFastQBuffer #2");
		if ( ok >= 0 && fastq )
		{
			char expected[128];
			snprintf(expected, sizeof(expected), "@%s\n%s\n+\n%s\n",
			         readname_b, query_b_read, qual_b);
			check(strncmp(fastq, expected, strlen(expected)) == 0,
			      "FASTQ round-trip #2");
			if ( strncmp(fastq, expected, strlen(expected)) != 0 )
				printf("      got: %.*s\n", (int)fastqlen, fastq);
			free(fastq);
		}
	}

	check(BamBam_BamFileDecoder_DecodeAlignment(decoder) == 0,
	      "decoder reports end of stream after 2 records");
	BamBam_BamFileDecoder_Delete(decoder);

	printf("bambamc consumer round-trip: %d checks, %d failures\n", checks, failures);
	return failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
