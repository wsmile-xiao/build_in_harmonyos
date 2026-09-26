
#line 1 "ocaml.rl"
/************************* Required for every parser *************************/
#ifndef OHCOUNT_OCAML_PARSER_H
#define OHCOUNT_OCAML_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *OCAML_LANG = LANG_OCAML;

// the languages entities
const char *ocaml_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  OCAML_SPACE = 0, OCAML_COMMENT, OCAML_STRING, OCAML_ANY
};

/*****************************************************************************/


#line 26 "ocaml.h"
static const char _ocaml_actions[] = {
	0, 1, 1, 1, 7, 1, 8, 1, 
	10, 1, 11, 1, 12, 1, 13, 1, 
	16, 1, 19, 1, 20, 1, 21, 1, 
	22, 1, 24, 1, 25, 1, 26, 1, 
	27, 2, 1, 15, 2, 4, 1, 2, 
	4, 11, 2, 5, 1, 2, 5, 11, 
	2, 6, 2, 2, 8, 17, 2, 9, 
	18, 2, 11, 23, 3, 6, 2, 1, 
	3, 14, 0, 9, 3, 14, 3, 9, 
	3, 14, 3, 11
};

static const char _ocaml_cond_offsets[] = {
	0, 0, 1, 2, 3, 5, 5, 5, 
	7, 9, 11, 11, 13, 16, 16, 16, 
	16, 16, 17, 17, 17, 17
};

static const char _ocaml_cond_lengths[] = {
	0, 1, 1, 1, 2, 0, 0, 2, 
	2, 2, 0, 2, 3, 0, 0, 0, 
	0, 1, 0, 0, 0, 0
};

static const short _ocaml_cond_keys[] = {
	42, 42, 42, 42, 42, 42, 41, 41, 
	42, 42, 13, 13, 42, 42, 13, 13, 
	42, 42, 13, 13, 42, 42, 13, 13, 
	42, 42, 13, 13, 41, 41, 42, 42, 
	13, 13, 0
};

static const char _ocaml_cond_spaces[] = {
	2, 2, 2, 2, 2, 0, 1, 0, 
	1, 0, 1, 0, 1, 0, 1, 1, 
	0, 0
};

static const char _ocaml_key_offsets[] = {
	0, 0, 7, 14, 22, 31, 36, 39, 
	54, 69, 84, 85, 101, 118, 119, 123, 
	126, 127, 139, 141, 146, 147
};

static const short _ocaml_trans_keys[] = {
	40, 1322, 1578, 0, 41, 43, 255, 40, 
	1322, 1578, 0, 41, 43, 255, 40, 41, 
	1322, 1578, 0, 39, 43, 255, 40, 1321, 
	1322, 1577, 1578, 0, 39, 43, 255, 10, 
	34, 92, 12, 13, 10, 12, 13, 9, 
	10, 12, 32, 40, 269, 525, 810, 1066, 
	0, 11, 14, 41, 43, 255, 9, 10, 
	12, 32, 40, 269, 525, 810, 1066, 0, 
	11, 14, 41, 43, 255, 9, 10, 12, 
	32, 40, 269, 525, 810, 1066, 0, 11, 
	14, 41, 43, 255, 10, 9, 10, 12, 
	32, 40, 41, 269, 525, 810, 1066, 0, 
	11, 14, 39, 43, 255, 9, 10, 12, 
	32, 40, 269, 525, 809, 810, 1065, 1066, 
	0, 11, 14, 39, 43, 255, 10, 32, 
	40, 9, 13, 32, 9, 13, 42, 9, 
	10, 12, 32, 34, 40, 269, 525, 0, 
	8, 14, 255, 9, 32, 10, 34, 92, 
	12, 13, 42, 10, 0
};

static const char _ocaml_single_lengths[] = {
	0, 3, 3, 4, 5, 3, 1, 9, 
	9, 9, 1, 10, 11, 1, 2, 1, 
	1, 8, 2, 3, 1, 1
};

static const char _ocaml_range_lengths[] = {
	0, 2, 2, 2, 2, 1, 1, 3, 
	3, 3, 0, 3, 3, 0, 1, 1, 
	0, 2, 0, 1, 0, 0
};

static const char _ocaml_index_offsets[] = {
	0, 0, 6, 12, 19, 27, 32, 35, 
	48, 61, 74, 76, 90, 105, 107, 111, 
	114, 116, 127, 130, 135, 137
};

static const char _ocaml_indicies[] = {
	2, 3, 4, 1, 1, 0, 2, 5, 
	6, 1, 1, 0, 2, 7, 3, 4, 
	1, 1, 0, 2, 7, 3, 8, 4, 
	1, 1, 0, 9, 11, 12, 9, 10, 
	9, 9, 10, 14, 15, 15, 14, 16, 
	17, 15, 18, 19, 13, 13, 13, 9, 
	21, 22, 22, 21, 23, 24, 22, 25, 
	26, 20, 20, 20, 9, 14, 15, 15, 
	14, 16, 17, 15, 27, 28, 13, 13, 
	13, 9, 15, 9, 14, 15, 15, 14, 
	16, 29, 17, 15, 18, 19, 13, 13, 
	13, 9, 14, 15, 15, 14, 16, 17, 
	15, 29, 18, 30, 19, 13, 13, 13, 
	9, 31, 32, 34, 35, 34, 33, 34, 
	34, 36, 1, 37, 39, 31, 31, 39, 
	40, 41, 42, 43, 38, 38, 32, 39, 
	39, 44, 45, 11, 12, 45, 10, 13, 
	45, 31, 46, 0
};

static const char _ocaml_trans_targs[] = {
	14, 1, 2, 3, 4, 3, 4, 1, 
	14, 17, 5, 17, 6, 7, 7, 8, 
	9, 10, 11, 12, 7, 7, 8, 9, 
	10, 11, 12, 11, 12, 7, 17, 17, 
	0, 14, 15, 16, 14, 14, 17, 18, 
	19, 20, 13, 21, 17, 17, 17
};

static const char _ocaml_trans_actions[] = {
	31, 9, 9, 9, 9, 39, 39, 45, 
	57, 23, 0, 15, 0, 1, 0, 0, 
	1, 0, 1, 1, 60, 48, 48, 60, 
	48, 60, 60, 36, 36, 42, 33, 51, 
	0, 25, 7, 72, 27, 29, 54, 3, 
	64, 68, 5, 5, 17, 21, 19
};

static const char _ocaml_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 11, 0, 
	0, 11, 0, 0, 0, 0
};

static const char _ocaml_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 13, 0, 
	0, 13, 0, 0, 0, 0
};

static const char _ocaml_eof_trans[] = {
	0, 1, 1, 1, 1, 10, 10, 10, 
	10, 10, 10, 10, 10, 0, 0, 37, 
	38, 0, 45, 46, 46, 47
};

static const int ocaml_start = 14;
static const int ocaml_first_final = 14;
static const int ocaml_error = 0;

static const int ocaml_en_ocaml_line = 17;
static const int ocaml_en_ocaml_entity = 14;


#line 94 "ocaml.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Objective Caml code.
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
void parse_ocaml(char *buffer, int length, int count,
                 void (*callback) (const char *lang, const char *entity, int s,
                                   int e, void *udata),
                 void *userdata
  ) {
  init

  int nest_count = 0;

  
#line 203 "ocaml.h"
	{
	cs = ocaml_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 119 "ocaml.rl"
  cs = (count) ? ocaml_en_ocaml_line : ocaml_en_ocaml_entity;
  
#line 214 "ocaml.h"
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
	_acts = _ocaml_actions + _ocaml_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 13:
#line 1 "NONE"
	{ts = p;}
	break;
#line 236 "ocaml.h"
		}
	}

	_widec = (*p);
	_klen = _ocaml_cond_lengths[cs];
	_keys = _ocaml_cond_keys + (_ocaml_cond_offsets[cs]*2);
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
				switch ( _ocaml_cond_spaces[_ocaml_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
	case 1: {
		_widec = (short)(768 + ((*p) - 0));
		if ( 
#line 60 "ocaml.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
	case 2: {
		_widec = (short)(1280 + ((*p) - 0));
		if ( 
#line 86 "ocaml.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _ocaml_trans_keys + _ocaml_key_offsets[cs];
	_trans = _ocaml_index_offsets[cs];

	_klen = _ocaml_single_lengths[cs];
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

	_klen = _ocaml_range_lengths[cs];
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
	_trans = _ocaml_indicies[_trans];
_eof_trans:
	cs = _ocaml_trans_targs[_trans];

	if ( _ocaml_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _ocaml_actions + _ocaml_trans_actions[_trans];
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
#line 29 "ocaml.rl"
	{
    switch(entity) {
    case OCAML_SPACE:
      ls
      break;
    case OCAML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCAML_LANG)
      break;
    case NEWLINE:
      std_newline(OCAML_LANG)
    }
  }
	break;
	case 3:
#line 45 "ocaml.rl"
	{ nest_count = 0; }
	break;
	case 4:
#line 46 "ocaml.rl"
	{ nest_count++; }
	break;
	case 5:
#line 47 "ocaml.rl"
	{ nest_count--; }
	break;
	case 6:
#line 51 "ocaml.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 67 "ocaml.rl"
	{ entity = OCAML_SPACE; }
	break;
	case 8:
#line 70 "ocaml.rl"
	{ entity = NEWLINE;      }
	break;
	case 9:
#line 71 "ocaml.rl"
	{ entity = OCAML_ANY;   }
	break;
	case 10:
#line 89 "ocaml.rl"
	{ entity = OCAML_SPACE;   }
	break;
	case 11:
#line 90 "ocaml.rl"
	{ entity = OCAML_COMMENT; }
	break;
	case 14:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 15:
#line 68 "ocaml.rl"
	{te = p+1;}
	break;
	case 16:
#line 69 "ocaml.rl"
	{te = p+1;}
	break;
	case 17:
#line 29 "ocaml.rl"
	{te = p+1;{
    switch(entity) {
    case OCAML_SPACE:
      ls
      break;
    case OCAML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCAML_LANG)
      break;
    case NEWLINE:
      std_newline(OCAML_LANG)
    }
  }}
	break;
	case 18:
#line 29 "ocaml.rl"
	{te = p+1;{
    switch(entity) {
    case OCAML_SPACE:
      ls
      break;
    case OCAML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCAML_LANG)
      break;
    case NEWLINE:
      std_newline(OCAML_LANG)
    }
  }}
	break;
	case 19:
#line 29 "ocaml.rl"
	{te = p;p--;{
    switch(entity) {
    case OCAML_SPACE:
      ls
      break;
    case OCAML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCAML_LANG)
      break;
    case NEWLINE:
      std_newline(OCAML_LANG)
    }
  }}
	break;
	case 20:
#line 29 "ocaml.rl"
	{te = p;p--;{
    switch(entity) {
    case OCAML_SPACE:
      ls
      break;
    case OCAML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCAML_LANG)
      break;
    case NEWLINE:
      std_newline(OCAML_LANG)
    }
  }}
	break;
	case 21:
#line 29 "ocaml.rl"
	{te = p;p--;{
    switch(entity) {
    case OCAML_SPACE:
      ls
      break;
    case OCAML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCAML_LANG)
      break;
    case NEWLINE:
      std_newline(OCAML_LANG)
    }
  }}
	break;
	case 22:
#line 29 "ocaml.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case OCAML_SPACE:
      ls
      break;
    case OCAML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCAML_LANG)
      break;
    case NEWLINE:
      std_newline(OCAML_LANG)
    }
  }}
	break;
	case 23:
#line 76 "ocaml.rl"
	{te = p+1;{
    callback(OCAML_LANG, ocaml_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 92 "ocaml.rl"
	{te = p+1;}
	break;
	case 25:
#line 76 "ocaml.rl"
	{te = p;p--;{
    callback(OCAML_LANG, ocaml_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 26:
#line 92 "ocaml.rl"
	{te = p;p--;}
	break;
	case 27:
#line 92 "ocaml.rl"
	{{p = ((te))-1;}}
	break;
#line 561 "ocaml.h"
		}
	}

_again:
	_acts = _ocaml_actions + _ocaml_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 574 "ocaml.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _ocaml_eof_trans[cs] > 0 ) {
		_trans = _ocaml_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 121 "ocaml.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(OCAML_LANG) }
}

#endif

/*****************************************************************************/
