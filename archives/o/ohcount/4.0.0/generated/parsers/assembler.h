
#line 1 "assembler.rl"
// assembler.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_ASM_PARSER_H
#define OHCOUNT_ASM_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *ASM_LANG = LANG_ASSEMBLER;

// the languages entities
const char *asm_entities[] = {
  "space", "comment", "string", "number",
  "keyword", "identifier", "operator", "any"
};

// constants associated with the entities
enum {
  ASM_SPACE = 0, ASM_COMMENT, ASM_STRING, ASM_NUMBER,
  ASM_KEYWORD, ASM_IDENTIFIER, ASM_OPERATOR, ASM_ANY
};

/*****************************************************************************/


#line 30 "assembler.h"
static const char _assembler_actions[] = {
	0, 1, 1, 1, 4, 1, 5, 1, 
	7, 1, 8, 1, 9, 1, 10, 1, 
	12, 1, 13, 1, 16, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 22, 1, 
	23, 1, 24, 1, 25, 1, 26, 2, 
	1, 6, 2, 3, 2, 2, 5, 14, 
	2, 6, 15, 2, 8, 21, 2, 11, 
	6, 2, 11, 8, 3, 3, 2, 1, 
	3, 11, 0, 6
};

static const char _assembler_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 1, 2, 
	3, 3, 3, 3, 3, 3, 3, 4, 
	4, 4, 4, 4
};

static const char _assembler_cond_lengths[] = {
	0, 0, 0, 0, 0, 1, 1, 1, 
	0, 0, 0, 0, 0, 0, 1, 0, 
	0, 0, 0, 0
};

static const short _assembler_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _assembler_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _assembler_key_offsets[] = {
	0, 0, 1, 3, 8, 11, 22, 33, 
	45, 46, 47, 53, 56, 59, 61, 75, 
	77, 80, 85, 87
};

static const short _assembler_trans_keys[] = {
	42, 42, 47, 10, 34, 92, 12, 13, 
	10, 12, 13, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 42, 47, 269, 
	525, 0, 11, 14, 255, 10, 10, 32, 
	33, 47, 59, 9, 13, 32, 9, 13, 
	10, 12, 13, 42, 47, 9, 10, 12, 
	32, 33, 34, 47, 59, 269, 525, 0, 
	8, 14, 255, 9, 32, 10, 12, 13, 
	10, 34, 92, 12, 13, 42, 47, 10, 
	0
};

static const char _assembler_single_lengths[] = {
	0, 1, 2, 3, 1, 7, 7, 8, 
	1, 1, 4, 1, 1, 2, 10, 2, 
	1, 3, 2, 1
};

static const char _assembler_range_lengths[] = {
	0, 0, 0, 1, 1, 2, 2, 2, 
	0, 0, 1, 1, 1, 0, 2, 0, 
	1, 1, 0, 0
};

static const char _assembler_index_offsets[] = {
	0, 0, 2, 5, 10, 13, 23, 33, 
	44, 46, 48, 54, 57, 60, 63, 76, 
	79, 82, 87, 90
};

static const char _assembler_indicies[] = {
	2, 1, 2, 3, 1, 4, 6, 7, 
	4, 5, 4, 4, 5, 9, 10, 10, 
	9, 11, 12, 10, 8, 8, 4, 14, 
	15, 15, 14, 16, 17, 15, 13, 13, 
	4, 9, 10, 10, 9, 11, 18, 12, 
	10, 8, 8, 4, 10, 4, 19, 20, 
	22, 23, 24, 23, 22, 21, 22, 22, 
	25, 26, 26, 23, 1, 23, 27, 29, 
	19, 19, 29, 30, 31, 32, 30, 33, 
	34, 28, 28, 20, 29, 29, 35, 36, 
	36, 37, 38, 6, 7, 38, 5, 8, 
	39, 38, 19, 40, 0
};

static const char _assembler_trans_targs[] = {
	10, 1, 2, 10, 14, 3, 14, 4, 
	5, 5, 6, 7, 8, 5, 5, 6, 
	7, 8, 14, 14, 0, 10, 11, 12, 
	13, 10, 10, 10, 14, 15, 16, 17, 
	18, 9, 19, 14, 14, 16, 14, 16, 
	14
};

static const char _assembler_trans_actions[] = {
	37, 9, 9, 51, 27, 0, 17, 0, 
	1, 0, 0, 1, 0, 60, 42, 42, 
	60, 42, 15, 45, 0, 29, 7, 9, 
	57, 31, 33, 35, 48, 3, 39, 64, 
	54, 5, 5, 19, 21, 0, 25, 1, 
	23
};

static const char _assembler_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 11, 0, 0, 0, 11, 0, 
	0, 0, 0, 0
};

static const char _assembler_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 13, 0, 0, 0, 13, 0, 
	0, 0, 0, 0
};

static const char _assembler_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 0, 0, 26, 27, 28, 0, 36, 
	37, 39, 39, 41
};

static const int assembler_start = 10;
static const int assembler_first_final = 10;
static const int assembler_error = 0;

static const int assembler_en_asm_line = 14;
static const int assembler_en_asm_entity = 10;


#line 86 "assembler.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Assembler code.
 *
 * @param *buffer The string to parse.
 * @param length The length of the string to parse.
 * @param count Integer flag specifying whether or not to count lines. If yes,
 *   uses the Ragel machine optimized for counting. Otherwise uses the Ragel
 *   machine optimized for returning entity positions.
 * @param *callback Callback function. If count is set, callback is called for
 *   every line of code, comment, or blank with 'lcode', 'lcomment', and
 *   'lblank' respectively. Otherwise callback is called for each entity found.
 */
void parse_assembler(char *buffer, int length, int count,
                     void (*callback) (const char *lang, const char *entity,
                                       int s, int e, void *udata),
                     void *userdata
  ) {
  init

  
#line 186 "assembler.h"
	{
	cs = assembler_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 109 "assembler.rl"
  cs = (count) ? assembler_en_asm_line : assembler_en_asm_entity;
  
#line 197 "assembler.h"
	{
	int _klen;
	unsigned int _trans;
	short _widec;
	const char *_acts;
	unsigned int _nacts;
	const short *_keys;

	if ( p == pe )
		goto _test_eof;
	if ( cs == 0 )
		goto _out;
_resume:
	_acts = _assembler_actions + _assembler_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = p;}
	break;
#line 219 "assembler.h"
		}
	}

	_widec = (*p);
	_klen = _assembler_cond_lengths[cs];
	_keys = _assembler_cond_keys + (_assembler_cond_offsets[cs]*2);
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				switch ( _assembler_cond_spaces[_assembler_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _assembler_trans_keys + _assembler_key_offsets[cs];
	_trans = _assembler_index_offsets[cs];

	_klen = _assembler_single_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + _klen - 1;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + ((_upper-_lower) >> 1);
			if ( _widec < *_mid )
				_upper = _mid - 1;
			else if ( _widec > *_mid )
				_lower = _mid + 1;
			else {
				_trans += (unsigned int)(_mid - _keys);
				goto _match;
			}
		}
		_keys += _klen;
		_trans += _klen;
	}

	_klen = _assembler_range_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				_trans += (unsigned int)((_mid - _keys)>>1);
				goto _match;
			}
		}
		_trans += _klen;
	}

_match:
	_trans = _assembler_indicies[_trans];
_eof_trans:
	cs = _assembler_trans_targs[_trans];

	if ( _assembler_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _assembler_actions + _assembler_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 53 "common.rl"
	{
  if (!line_contains_code && !line_start) line_start = ts;
  line_contains_code = 1;
}
	break;
	case 1:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 2:
#line 33 "assembler.rl"
	{
    switch(entity) {
    case ASM_SPACE:
      ls
      break;
    case ASM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ASM_LANG)
      break;
    case NEWLINE:
      std_newline(ASM_LANG)
    }
  }
	break;
	case 3:
#line 52 "assembler.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 63 "assembler.rl"
	{ entity = ASM_SPACE; }
	break;
	case 5:
#line 66 "assembler.rl"
	{ entity = NEWLINE;   }
	break;
	case 6:
#line 67 "assembler.rl"
	{ entity = ASM_ANY;   }
	break;
	case 7:
#line 81 "assembler.rl"
	{ entity = ASM_SPACE;   }
	break;
	case 8:
#line 82 "assembler.rl"
	{ entity = ASM_COMMENT; }
	break;
	case 11:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 12:
#line 64 "assembler.rl"
	{te = p+1;}
	break;
	case 13:
#line 65 "assembler.rl"
	{te = p+1;}
	break;
	case 14:
#line 33 "assembler.rl"
	{te = p+1;{
    switch(entity) {
    case ASM_SPACE:
      ls
      break;
    case ASM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ASM_LANG)
      break;
    case NEWLINE:
      std_newline(ASM_LANG)
    }
  }}
	break;
	case 15:
#line 33 "assembler.rl"
	{te = p+1;{
    switch(entity) {
    case ASM_SPACE:
      ls
      break;
    case ASM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ASM_LANG)
      break;
    case NEWLINE:
      std_newline(ASM_LANG)
    }
  }}
	break;
	case 16:
#line 33 "assembler.rl"
	{te = p;p--;{
    switch(entity) {
    case ASM_SPACE:
      ls
      break;
    case ASM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ASM_LANG)
      break;
    case NEWLINE:
      std_newline(ASM_LANG)
    }
  }}
	break;
	case 17:
#line 64 "assembler.rl"
	{te = p;p--;}
	break;
	case 18:
#line 33 "assembler.rl"
	{te = p;p--;{
    switch(entity) {
    case ASM_SPACE:
      ls
      break;
    case ASM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ASM_LANG)
      break;
    case NEWLINE:
      std_newline(ASM_LANG)
    }
  }}
	break;
	case 19:
#line 33 "assembler.rl"
	{te = p;p--;{
    switch(entity) {
    case ASM_SPACE:
      ls
      break;
    case ASM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ASM_LANG)
      break;
    case NEWLINE:
      std_newline(ASM_LANG)
    }
  }}
	break;
	case 20:
#line 33 "assembler.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case ASM_SPACE:
      ls
      break;
    case ASM_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ASM_LANG)
      break;
    case NEWLINE:
      std_newline(ASM_LANG)
    }
  }}
	break;
	case 21:
#line 72 "assembler.rl"
	{te = p+1;{
    callback(ASM_LANG, asm_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 22:
#line 84 "assembler.rl"
	{te = p+1;}
	break;
	case 23:
#line 72 "assembler.rl"
	{te = p;p--;{
    callback(ASM_LANG, asm_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 72 "assembler.rl"
	{te = p;p--;{
    callback(ASM_LANG, asm_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 84 "assembler.rl"
	{te = p;p--;}
	break;
	case 26:
#line 84 "assembler.rl"
	{{p = ((te))-1;}}
	break;
#line 528 "assembler.h"
		}
	}

_again:
	_acts = _assembler_actions + _assembler_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 9:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 541 "assembler.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _assembler_eof_trans[cs] > 0 ) {
		_trans = _assembler_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 111 "assembler.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(ASM_LANG) }
}

#endif

/*****************************************************************************/
