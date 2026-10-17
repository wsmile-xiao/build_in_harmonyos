/*
 * Small hand-written replacement for src/pgen/lexer.l.
 * It keeps the build independent from flex/lex on CI workers.
 */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <gcli/pgen.h>

#include "y.tab.h"

FILE *yyin = NULL;
int yycol = 1, yyrow = 1;
char *yyfile = NULL;

static int pushed = EOF;

void
yyerror(const char *msg)
{
	fprintf(stderr, "%s:%d:%d: error: %s\n", yyfile, yyrow, yycol, msg);
	exit(1);
}

int
yywrap(void)
{
	return 1;
}

static int
next_char(void)
{
	int ch;
	if (pushed != EOF) {
		ch = pushed;
		pushed = EOF;
		return ch;
	}
	return fgetc(yyin ? yyin : stdin);
}

static void
push_char(int ch)
{
	pushed = ch;
}

static char *
append_char(char *buf, size_t *len, size_t *cap, int ch)
{
	if (*len + 1 >= *cap) {
		size_t next = *cap ? *cap * 2 : 32;
		char *tmp = realloc(buf, next);
		if (!tmp)
			yyerror("out of memory");
		buf = tmp;
		*cap = next;
	}
	buf[(*len)++] = (char)ch;
	buf[*len] = '\0';
	return buf;
}

static int
keyword_or_ident(char *text)
{
	if (strcmp(text, "parser") == 0) {
		free(text);
		return PARSER;
	}
	if (strcmp(text, "include") == 0) {
		free(text);
		return INCLUDE;
	}
	if (strcmp(text, "is") == 0) {
		free(text);
		return IS;
	}
	if (strcmp(text, "object") == 0) {
		free(text);
		return OBJECT;
	}
	if (strcmp(text, "with") == 0) {
		free(text);
		return WITH;
	}
	if (strcmp(text, "as") == 0) {
		free(text);
		return AS;
	}
	if (strcmp(text, "use") == 0) {
		free(text);
		return USE;
	}
	if (strcmp(text, "array") == 0) {
		free(text);
		return ARRAY;
	}
	if (strcmp(text, "of") == 0) {
		free(text);
		return OF;
	}
	if (strcmp(text, "select") == 0) {
		free(text);
		return SELECT;
	}
	if (strcmp(text, "struct") == 0) {
		free(text);
		return STRUCT;
	}

	yylval.ident.text = text;
	return IDENT;
}

int
yylex(void)
{
	int ch;

	for (;;) {
		ch = next_char();
		if (ch == EOF)
			return 0;
		if (ch == '\n') {
			yycol = 1;
			yyrow += 1;
			continue;
		}
		if (ch == ' ' || ch == '\t') {
			yycol += 1;
			continue;
		}
		if (ch == '#') {
			while ((ch = next_char()) != EOF && ch != '\n')
				;
			if (ch == '\n') {
				yycol = 1;
				yyrow += 1;
			}
			continue;
		}
		break;
	}

	if (ch == '=') {
		int next = next_char();
		if (next == '>') {
			yycol += 2;
			return FATARROW;
		}
		if (next != EOF)
			push_char(next);
		yyerror("unrecognized character");
	}

	switch (ch) {
	case '(':
		yycol += 1;
		return OPAREN;
	case ')':
		yycol += 1;
		return CPAREN;
	case ';':
		yycol += 1;
		return SEMICOLON;
	case ',':
		yycol += 1;
		return COMMA;
	case '"': {
		char *text = NULL;
		size_t len = 0, cap = 0;
		while ((ch = next_char()) != EOF && ch != '"')
			text = append_char(text, &len, &cap, ch);
		if (ch != '"') {
			free(text);
			yyerror("unterminated string literal");
		}
		if (!text)
			text = strdup("");
		if (!text)
			yyerror("out of memory");
		yycol += (int)len + 2;
		yylval.strlit.text = text;
		return STRLIT;
	}
	default:
		break;
	}

	if (isalpha((unsigned char)ch)) {
		char *text = NULL;
		size_t len = 0, cap = 0;
		do {
			text = append_char(text, &len, &cap, ch);
			ch = next_char();
		} while (isalnum((unsigned char)ch) || ch == '_' || ch == '*' || ch == '.');
		if (ch != EOF)
			push_char(ch);
		yycol += (int)len;
		return keyword_or_ident(text);
	}

	yyerror("unrecognized character");
	return 0;
}
