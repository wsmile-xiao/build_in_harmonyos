/* Consumer-side contract tests for the installed libantlr3c 3.5.3 package.
 *
 * The ANTLR v3 Java tool is a host-side generator: the generated lexer and
 * parser C code only calls the runtime API shipped in this package.  To stay
 * independent of any online generator, these tests hand-write the exact
 * calls a generated lexer would make (the runtime documents this as the
 * "manually built lexer" path) and drive the runtime through:
 *
 *   1. character stream  - antlr3StringStreamNew + istream LA/consume/index
 *   2. lexer             - antlr3LexerNewStream + overridden mTokens rules
 *   3. token stream      - antlr3CommonTokenStreamSourceNew + LT/fill
 *   4. recognition error - matchc failure path -> exception -> recover
 *   5. resource release  - free() on lexer, token stream, input stream
 *
 * Each mTokens rule below mirrors the shape of ANTLR-generated C code
 * (see upstream runtime/C/src/antlr3lexer.c for the contract): set the
 * token type, match the rule characters, and let emit() build the token.
 */
#include <antlr3.h>

#include <stdio.h>
#include <string.h>

/* Hand-written token types (a generated header would define these). */
#define T_EOF      ANTLR3_TOKEN_EOF
#define T_WORD     1   /* [a-z]+          */
#define T_NUMBER   2   /* [0-9]+          */
#define T_PLUS     3   /* '+'             */
#define T_STAR     4   /* '*'             */
#define T_BADCHAR  5   /* error recovery  */

static const char *tname(ANTLR3_UINT32 t)
{
    switch (t) {
    case T_EOF:     return "EOF";
    case T_WORD:    return "WORD";
    case T_NUMBER:  return "NUMBER";
    case T_PLUS:    return "PLUS";
    case T_STAR:    return "STAR";
    case T_BADCHAR: return "BADCHAR";
    default:        return "?";
    }
}

/* ---- a minimal generated-style lexer context ------------------------- */

typedef struct {
    pANTLR3_LEXER  lexer;          /* must be first: rec->super -> &ctx    */
    unsigned       errors;         /* bumped by our error override         */
} MiniLexer;

/*
 * mTokens equivalent of the ANTLR grammar:
 *
 *   grammar Mini;
 *   WORD   : ('a'..'z')+ ;
 *   NUMBER : ('0'..'9')+ ;
 *   PLUS   : '+' ;
 *   STAR   : '*' ;
 *
 * plus a fallback branch that reports a lexer error for anything else
 * (what a generated lexer without a catch-all rule does).
 */
static void mini_mTokens(void *ctx)
{
    MiniLexer      *mini = (MiniLexer *)ctx;
    pANTLR3_LEXER   lexer = mini->lexer;
    pANTLR3_INPUT_STREAM input = lexer->input;
    ANTLR3_UCHAR    c = input->istream->_LA(input->istream, 1);

    if (c >= 'a' && c <= 'z') {
        lexer->rec->state->type = T_WORD;
        do {
            lexer->matchRange(lexer, 'a', 'z');
        } while (input->istream->_LA(input->istream, 1) >= 'a'
              && input->istream->_LA(input->istream, 1) <= 'z');
    } else if (c >= '0' && c <= '9') {
        lexer->rec->state->type = T_NUMBER;
        do {
            lexer->matchRange(lexer, '0', '9');
        } while (input->istream->_LA(input->istream, 1) >= '0'
              && input->istream->_LA(input->istream, 1) <= '9');
    } else if (c == '+') {
        lexer->rec->state->type = T_PLUS;
        lexer->matchc(lexer, '+');
    } else if (c == '*') {
        lexer->rec->state->type = T_STAR;
        lexer->matchc(lexer, '*');
    } else {
        /* No rule matches: mimic the generated error path.  The runtime
         * nextToken() sees state->error and calls reportError()+recover(),
         * which consumes one char and continues. */
        lexer->rec->state->type = T_BADCHAR;
        lexer->rec->exConstruct(lexer->rec);
        lexer->rec->state->error = ANTLR3_TRUE;
    }
}

/* Error display override: count errors instead of printing to stderr so the
 * assertions stay exact. */
static void mini_display_error(pANTLR3_BASE_RECOGNIZER recognizer,
                               pANTLR3_UINT8 *tokenNames)
{
    /* recognizer->super is the pANTLR3_LEXER (runtime contract); the user
     * context hangs off lexer->ctx, exactly where generated code puts it. */
    pANTLR3_LEXER lexer = (pANTLR3_LEXER)recognizer->super;

    (void)tokenNames;
    ((MiniLexer *)lexer->ctx)->errors++;
}

static MiniLexer *mini_lexer_new(const char *text)
{
    MiniLexer *mini = NULL;
    pANTLR3_INPUT_STREAM input = antlr3StringStreamNew(
        (pANTLR3_UINT8)text, ANTLR3_ENC_8BIT,
        (ANTLR3_UINT32)strlen(text), (pANTLR3_UINT8)"memory");
    if (input == NULL) {
        return NULL;
    }
    mini = (MiniLexer *)ANTLR3_CALLOC(1, sizeof(MiniLexer));
    if (mini == NULL) {
        input->close(input);
        return NULL;
    }
    mini->lexer = antlr3LexerNewStream(0, input, NULL);
    if (mini->lexer == NULL) {
        input->close(input);
        ANTLR3_FREE(mini);
        return NULL;
    }
    /* Generated-code contract: lexer->ctx is the user context (passed back
     * to mTokens), while rec->super MUST stay pointing at the lexer itself —
     * the runtime casts it back to pANTLR3_LEXER in exConstruct() and the
     * exception machinery. */
    mini->lexer->ctx = mini;
    mini->lexer->mTokens = mini_mTokens;
    mini->lexer->rec->displayRecognitionError = mini_display_error;
    return mini;
}

static void mini_lexer_free(MiniLexer *mini)
{
    if (mini == NULL) {
        return;
    }
    if (mini->lexer != NULL) {
        pANTLR3_INPUT_STREAM input = mini->lexer->input;
        mini->lexer->free(mini->lexer);         /* frees rec/state/factory  */
        if (input != NULL) {
            input->close(input);
        }
    }
    ANTLR3_FREE(mini);
}

/* ---- test 1: character stream primitives ----------------------------- */

static int test_charstream(void)
{
    static const char text[] = "ab+12";
    pANTLR3_INPUT_STREAM input = antlr3StringStreamNew(
        (pANTLR3_UINT8)text, ANTLR3_ENC_8BIT,
        (ANTLR3_UINT32)strlen(text), (pANTLR3_UINT8)"cs");
    pANTLR3_INT_STREAM is;
    int failures = 0;

    if (input == NULL) {
        fprintf(stderr, "FAIL charstream: no input stream\n");
        return 1;
    }
    is = input->istream;

    if (is->_LA(is, 1) != 'a') {
        fprintf(stderr, "FAIL charstream: LA(1) expected 'a'\n");
        failures++;
    }
    is->consume(is);
    is->consume(is);
    if (is->_LA(is, 1) != '+') {
        fprintf(stderr, "FAIL charstream: LA(1) after 2 consumes expected '+'\n");
        failures++;
    }
    /* ANTLR3 3.5.3 semantics: index()/seek() deal in ABSOLUTE data pointers
     * (nextChar), not offsets — see antlr38BitIndex/antlr38BitSeek.  Use the
     * data base pointer to convert between the two worlds. */
    {
        ANTLR3_MARKER base = (ANTLR3_MARKER)input->data;

        if (is->index(is) - base != 2) {
            fprintf(stderr, "FAIL charstream: index expected 2, got %lld\n",
                    (long long)(is->index(is) - base));
            failures++;
        }
        is->seek(is, base + 4);
        if (is->_LA(is, 1) != '2') {
            fprintf(stderr, "FAIL charstream: LA(1) at seek(+4) expected '2'\n");
            failures++;
        }
        is->seek(is, base + 5);
        if (is->_LA(is, 1) != ANTLR3_CHARSTREAM_EOF) {
            fprintf(stderr, "FAIL charstream: expected EOF LA(1)\n");
            failures++;
        }
    }
    if (input->getLine(input) != 1 || input->charPositionInLine != 5) {
        fprintf(stderr, "FAIL charstream: line/position tracking broken\n");
        failures++;
    }
    input->close(input);
    if (!failures) {
        printf("PASS charstream: LA/consume/index/seek/EOF/line\n");
    }
    return failures;
}

/* ---- test 2 + 3: token stream over hand-written lexer ---------------- */

static int run_lexer_tokens(const char *text, const ANTLR3_UINT32 *types,
                            const int expect_errors)
{
    MiniLexer *mini = mini_lexer_new(text);
    pANTLR3_COMMON_TOKEN_STREAM cts;
    pANTLR3_TOKEN_STREAM ts;
    pANTLR3_COMMON_TOKEN tok;
    int i;
    int failures = 0;

    if (mini == NULL) {
        fprintf(stderr, "FAIL tokens(%s): lexer init failed\n", text);
        return 1;
    }
    cts = antlr3CommonTokenStreamSourceNew(0, mini->lexer->rec->state->tokSource);
    if (cts == NULL) {
        fprintf(stderr, "FAIL tokens(%s): token stream init failed\n", text);
        mini_lexer_free(mini);
        return 1;
    }
    ts = cts->tstream;

    /* Wait for a well-formed stream: skip (recover) tokens of type BADCHAR. */
    for (i = 0; types[i] != T_EOF; i++) {
        tok = ts->_LT(ts, 1);
        if (tok == NULL || tok->getType(tok) == ANTLR3_TOKEN_INVALID) {
            break;
        }
        if (tok->getType(tok) != types[i]) {
            fprintf(stderr,
                    "FAIL tokens(%s): token %d expected %s got %s\n",
                    text, i, tname(types[i]),
                    tok ? tname(tok->getType(tok)) : "NULL");
            failures++;
        }
        ts->istream->consume(ts->istream);
    }
    /* Final token must be EOF exactly where the plan says. */
    tok = ts->_LT(ts, 1);
    if (types[i] != T_EOF || tok == NULL
        || tok->getType(tok) != ANTLR3_TOKEN_EOF) {
        fprintf(stderr, "FAIL tokens(%s): stream did not end in EOF at %d\n",
                text, i);
        failures++;
    }
    if ((int)mini->errors != expect_errors) {
        fprintf(stderr,
                "FAIL tokens(%s): lexer errors expected %d got %u\n",
                text, expect_errors, mini->errors);
        failures++;
    }
    cts->free(cts);
    mini_lexer_free(mini);
    return failures;
}

static int test_token_stream(void)
{
    /* "abc+42*def" -> WORD PLUS NUMBER STAR WORD EOF */
    static const ANTLR3_UINT32 plan1[] = {
        T_WORD, T_PLUS, T_NUMBER, T_STAR, T_WORD, T_EOF
    };
    /* Line/column + token text are checked in test_token_details(). */
    int failures = 0;

    failures += run_lexer_tokens("abc+42*def", plan1, 0);
    if (!failures) {
        printf("PASS token_stream: WORD/PLUS/NUMBER/STAR/WORD sequence\n");
    }
    return failures;
}

/* ---- test 3b: token text/line/column details -------------------------- */

static int test_token_details(void)
{
    MiniLexer *mini = mini_lexer_new("abc\n42+x");
    pANTLR3_COMMON_TOKEN_STREAM cts;
    pANTLR3_TOKEN_STREAM ts;
    pANTLR3_COMMON_TOKEN tok;
    int failures = 0;

    if (mini == NULL) {
        fprintf(stderr, "FAIL details: lexer init failed\n");
        return 1;
    }
    cts = antlr3CommonTokenStreamSourceNew(0, mini->lexer->rec->state->tokSource);
    ts = cts->tstream;

    tok = ts->_LT(ts, 1);                     /* "abc" */
    if (tok->getType(tok) != T_WORD) {
        fprintf(stderr, "FAIL details: first token not WORD\n");
        failures++;
    }
    if (tok->getLine(tok) != 1 || tok->getCharPositionInLine(tok) != 0) {
        fprintf(stderr, "FAIL details: token line/col %u/%u\n",
                tok->getLine(tok), tok->getCharPositionInLine(tok));
        failures++;
    }
    if (tok->getText(tok) == NULL
        || strncmp((const char *)tok->getText(tok)->chars, "abc", 3) != 0) {
        fprintf(stderr, "FAIL details: WORD text\n");
        failures++;
    }
    ts->istream->consume(ts->istream);

    tok = ts->_LT(ts, 1);                     /* newline is skipped: no rule
                                                matches \n -> BADCHAR error */
    if (tok->getType(tok) != T_NUMBER || tok->getLine(tok) != 2) {
        fprintf(stderr, "FAIL details: NUMBER after newline: %s line %u\n",
                tname(tok->getType(tok)), tok->getLine(tok));
        failures++;
    }
    if (mini->errors != 1) {
        fprintf(stderr, "FAIL details: newline not counted as 1 error\n");
        failures++;
    }
    cts->free(cts);
    mini_lexer_free(mini);
    if (!failures) {
        printf("PASS details: token text/line/col and error count\n");
    }
    return failures;
}

/* ---- test 4: recognition error -> report + recover -------------------- */

static int test_syntax_error(void)
{
    /* '?' matches no rule: mTokens takes the error path (exConstruct +
     * state->error), nextToken() reports one recognition error and the
     * lexer recovery consumes exactly the offending char, so the stream
     * continues WORD("hi"), WORD("there"), EOF — the '?' never becomes a
     * token. */
    static const ANTLR3_UINT32 plan[] = { T_WORD, T_WORD, T_EOF };
    int failures = run_lexer_tokens("hi?there", plan, 1);
    if (!failures) {
        printf("PASS syntax_error: report + single-char recovery\n");
    }
    return failures;
}

/* ---- main -------------------------------------------------------------- */

int main(void)
{
    int failures = 0;

    failures += test_charstream();
    failures += test_token_stream();
    failures += test_token_details();
    failures += test_syntax_error();

    if (failures) {
        printf("libantlr3c consumer tests: %d FAILURE(S)\n", failures);
        return 1;
    }
    printf("libantlr3c consumer tests: all passed\n");
    return 0;
}
