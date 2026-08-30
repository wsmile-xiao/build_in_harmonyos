/*
 * test_package smoke test for libhubbub 0.3.8
 *
 * Exercises the public C API of the library (R34: must actually call the
 * package's API, not just print a string):
 *   - hubbub_parser_create          (create a parser)
 *   - hubbub_parser_setopt          (register token handler)
 *   - hubbub_parser_parse_chunk     (feed HTML data)
 *   - hubbub_parser_completed       (end of input)
 *   - hubbub_parser_read_charset    (charset report)
 *   - hubbub_parser_destroy         (cleanup)
 *
 * The token handler counts the tokens; for the input "<html><body>
 * <p>Hi&nbsp;</p></body></html>" we expect to see at least the HTML
 * start tag, a body start tag, a paragraph, some characters and the
 * matching end tags.
 */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <hubbub/hubbub.h>
#include <hubbub/parser.h>

static hubbub_error token_handler(const hubbub_token *token, void *pw)
{
	uint32_t *count = (uint32_t *) pw;

	if (token == NULL)
		return HUBBUB_BADPARM;

	(*count)++;

	/* Sanity-check the payload of the tokens we receive. */
	switch (token->type) {
	case HUBBUB_TOKEN_DOCTYPE:
		if (token->data.doctype.name.ptr == NULL)
			return HUBBUB_BADPARM;
		break;
	case HUBBUB_TOKEN_START_TAG:
	case HUBBUB_TOKEN_END_TAG:
		if (token->data.tag.name.ptr == NULL)
			return HUBBUB_BADPARM;
		break;
	case HUBBUB_TOKEN_COMMENT:
		if (token->data.comment.ptr == NULL)
			return HUBBUB_BADPARM;
		break;
	case HUBBUB_TOKEN_CHARACTER:
		if (token->data.character.ptr == NULL)
			return HUBBUB_BADPARM;
		break;
	case HUBBUB_TOKEN_EOF:
		break;
	}

	return HUBBUB_OK;
}

int main(void)
{
	static const char *html =
		"<html><head><title>Test</title></head><body>"
		"<p>Hello&nbsp;World</p></body></html>";
	hubbub_parser *parser = NULL;
	hubbub_parser_optparams params;
	uint32_t tokens = 0;
	hubbub_charset_source source = HUBBUB_CHARSET_UNKNOWN;
	const char *charset;
	hubbub_error err;
	size_t chunk;
	int ret = 0;

	/* 1. create parser */
	err = hubbub_parser_create("UTF-8", false, &parser);
	if (err != HUBBUB_OK || parser == NULL) {
		fprintf(stderr, "hubbub_parser_create failed: %s\n",
				hubbub_error_to_string(err));
		return 1;
	}

	/* 2. register token handler */
	memset(&params, 0, sizeof params);
	params.token_handler.handler = token_handler;
	params.token_handler.pw = &tokens;
	err = hubbub_parser_setopt(parser, HUBBUB_PARSER_TOKEN_HANDLER,
			&params);
	if (err != HUBBUB_OK) {
		fprintf(stderr, "hubbub_parser_setopt failed: %s\n",
				hubbub_error_to_string(err));
		ret = 2;
		goto done;
	}

	/* 3. feed input in chunks */
	for (chunk = 0; chunk < strlen(html); chunk++) {
		err = hubbub_parser_parse_chunk(parser,
				(const uint8_t *) (html + chunk), 1);
		if (err != HUBBUB_OK && err != HUBBUB_NEEDDATA) {
			fprintf(stderr, "hubbub_parser_parse_chunk failed at "
					"byte %zu: %s\n", chunk,
					hubbub_error_to_string(err));
			ret = 3;
			goto done;
		}
	}

	/* 4. end of input */
	err = hubbub_parser_completed(parser);
	if (err != HUBBUB_OK && err != HUBBUB_NEEDDATA) {
		fprintf(stderr, "hubbub_parser_completed failed: %s\n",
				hubbub_error_to_string(err));
		ret = 4;
		goto done;
	}

	/* 5. charset report (must be a non-NULL string) */
	charset = hubbub_parser_read_charset(parser, &source);
	if (charset == NULL) {
		fprintf(stderr, "hubbub_parser_read_charset returned NULL\n");
		ret = 5;
		goto done;
	}

	/* We must have received a reasonable number of tokens for this input:
	 * DOCTYPE is absent, but at minimum: html start/end, head start/end,
	 * title start/end + characters, body start/end, p start/end,
	 * "Hello World" characters (with &nbsp; entity), EOF. */
	if (tokens < 10) {
		fprintf(stderr, "too few tokens received: %" PRIu32 "\n",
				tokens);
		ret = 6;
		goto done;
	}

	printf("libhubbub API OK: parsed %" PRIu32 " tokens "
			"(charset='%s')\n", tokens, charset);

done:
	hubbub_parser_destroy(parser);
	return ret;
}
