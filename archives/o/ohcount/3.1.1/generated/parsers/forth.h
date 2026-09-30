
#line 1 "forth.rl"
// forth.rl 
// derived from code written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_FORTH_PARSER_H
#define OHCOUNT_FORTH_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *FORTH_LANG = LANG_FORTH;

// the languages entities
const char *forth_entities[] = {
  "space", "comment", "string", "any",
};

// constants associated with the entities
enum {
  FORTH_SPACE = 0, FORTH_COMMENT, FORTH_STRING, FORTH_ANY
};

/*****************************************************************************/


#line 29 "forth.h"
static const char _forth_actions[] = {
	0, 1, 1, 1, 4, 1, 5, 1, 
	7, 1, 8, 1, 9, 1, 10, 1, 
	12, 1, 13, 1, 16, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 22, 1, 
	23, 1, 24, 1, 25, 1, 26, 2, 
	1, 6, 2, 3, 2, 2, 5, 14, 
	2, 6, 15, 2, 8, 21, 2, 11, 
	8, 3, 3, 2, 1, 3, 3, 2, 
	12, 3, 11, 0, 6, 3, 11, 1, 
	6
};

static const char _forth_cond_offsets[] = {
	0, 0, 0, 0, 1, 2, 2, 2, 
	2, 2, 2, 2, 3, 3, 3, 4, 
	4
};

static const char _forth_cond_lengths[] = {
	0, 0, 0, 1, 1, 0, 0, 0, 
	0, 0, 0, 1, 0, 0, 1, 0, 
	0
};

static const short _forth_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _forth_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _forth_key_offsets[] = {
	0, 0, 1, 5, 16, 27, 28, 29, 
	34, 37, 38, 41, 54, 56, 60, 71, 
	74
};

static const short _forth_trans_keys[] = {
	41, 10, 34, 12, 13, 9, 10, 12, 
	32, 41, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 41, 269, 525, 0, 
	11, 14, 255, 10, 10, 32, 40, 92, 
	9, 13, 32, 9, 13, 41, 10, 12, 
	13, 9, 10, 12, 32, 34, 40, 92, 
	269, 525, 0, 8, 14, 255, 9, 32, 
	10, 34, 12, 13, 9, 10, 12, 32, 
	41, 269, 525, 0, 11, 14, 255, 10, 
	12, 13, 10, 0
};

static const char _forth_single_lengths[] = {
	0, 1, 2, 7, 7, 1, 1, 3, 
	1, 1, 1, 9, 2, 2, 7, 1, 
	1
};

static const char _forth_range_lengths[] = {
	0, 0, 1, 2, 2, 0, 0, 1, 
	1, 0, 1, 2, 0, 1, 2, 1, 
	0
};

static const char _forth_index_offsets[] = {
	0, 0, 2, 6, 16, 26, 28, 30, 
	35, 38, 40, 43, 55, 58, 62, 72, 
	75
};

static const char _forth_indicies[] = {
	2, 1, 3, 5, 3, 4, 7, 8, 
	8, 7, 9, 10, 8, 6, 6, 3, 
	12, 13, 13, 12, 14, 15, 13, 11, 
	11, 3, 8, 3, 16, 17, 19, 20, 
	21, 19, 18, 19, 19, 22, 2, 1, 
	24, 24, 21, 26, 16, 16, 26, 27, 
	28, 29, 30, 31, 25, 25, 17, 26, 
	26, 32, 33, 5, 33, 4, 7, 8, 
	8, 7, 9, 10, 8, 6, 6, 33, 
	34, 34, 35, 16, 36, 0
};

static const char _forth_trans_targs[] = {
	7, 1, 7, 11, 2, 11, 3, 3, 
	4, 11, 5, 3, 3, 4, 11, 5, 
	11, 0, 7, 8, 9, 10, 7, 7, 
	7, 11, 12, 13, 14, 15, 6, 16, 
	11, 11, 11, 15, 11
};

static const char _forth_trans_actions[] = {
	37, 9, 51, 27, 0, 17, 1, 0, 
	0, 15, 0, 57, 42, 42, 61, 42, 
	45, 0, 29, 7, 54, 9, 31, 35, 
	33, 48, 3, 65, 69, 39, 5, 5, 
	19, 25, 21, 0, 23
};

static const char _forth_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 11, 
	0, 0, 0, 11, 0, 0, 0, 0, 
	0
};

static const char _forth_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 13, 
	0, 0, 0, 13, 0, 0, 0, 0, 
	0
};

static const char _forth_eof_trans[] = {
	0, 1, 4, 4, 4, 4, 0, 0, 
	23, 24, 25, 0, 33, 34, 34, 35, 
	37
};

static const int forth_start = 7;
static const int forth_first_final = 7;
static const int forth_error = 0;

static const int forth_en_forth_line = 11;
static const int forth_en_forth_entity = 7;


#line 85 "forth.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Forth code.
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
void parse_forth(char *buffer, int length, int count,
                 void (*callback) (const char *lang, const char *entity, int s,
                                   int e, void *udata),
                 void *userdata
  ) {
  init

  
#line 180 "forth.h"
	{
	cs = forth_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 108 "forth.rl"
  cs = (count) ? forth_en_forth_line : forth_en_forth_entity;
  
#line 191 "forth.h"
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
	_acts = _forth_actions + _forth_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = p;}
	break;
#line 213 "forth.h"
		}
	}

	_widec = (*p);
	_klen = _forth_cond_lengths[cs];
	_keys = _forth_cond_keys + (_forth_cond_offsets[cs]*2);
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
				switch ( _forth_cond_spaces[_forth_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _forth_trans_keys + _forth_key_offsets[cs];
	_trans = _forth_index_offsets[cs];

	_klen = _forth_single_lengths[cs];
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

	_klen = _forth_range_lengths[cs];
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
	_trans = _forth_indicies[_trans];
_eof_trans:
	cs = _forth_trans_targs[_trans];

	if ( _forth_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _forth_actions + _forth_trans_actions[_trans];
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
#line 32 "forth.rl"
	{
    switch(entity) {
    case FORTH_SPACE:
      ls
      break;
    case FORTH_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTH_LANG)
      break;
    case NEWLINE:
      std_newline(FORTH_LANG)
    }
  }
	break;
	case 3:
#line 51 "forth.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 62 "forth.rl"
	{ entity = FORTH_SPACE; }
	break;
	case 5:
#line 65 "forth.rl"
	{ entity = NEWLINE;     }
	break;
	case 6:
#line 66 "forth.rl"
	{ entity = FORTH_ANY;   }
	break;
	case 7:
#line 80 "forth.rl"
	{ entity = FORTH_SPACE;   }
	break;
	case 8:
#line 81 "forth.rl"
	{ entity = FORTH_COMMENT; }
	break;
	case 11:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 12:
#line 63 "forth.rl"
	{te = p+1;}
	break;
	case 13:
#line 64 "forth.rl"
	{te = p+1;}
	break;
	case 14:
#line 32 "forth.rl"
	{te = p+1;{
    switch(entity) {
    case FORTH_SPACE:
      ls
      break;
    case FORTH_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTH_LANG)
      break;
    case NEWLINE:
      std_newline(FORTH_LANG)
    }
  }}
	break;
	case 15:
#line 32 "forth.rl"
	{te = p+1;{
    switch(entity) {
    case FORTH_SPACE:
      ls
      break;
    case FORTH_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTH_LANG)
      break;
    case NEWLINE:
      std_newline(FORTH_LANG)
    }
  }}
	break;
	case 16:
#line 32 "forth.rl"
	{te = p;p--;{
    switch(entity) {
    case FORTH_SPACE:
      ls
      break;
    case FORTH_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTH_LANG)
      break;
    case NEWLINE:
      std_newline(FORTH_LANG)
    }
  }}
	break;
	case 17:
#line 63 "forth.rl"
	{te = p;p--;}
	break;
	case 18:
#line 32 "forth.rl"
	{te = p;p--;{
    switch(entity) {
    case FORTH_SPACE:
      ls
      break;
    case FORTH_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTH_LANG)
      break;
    case NEWLINE:
      std_newline(FORTH_LANG)
    }
  }}
	break;
	case 19:
#line 32 "forth.rl"
	{te = p;p--;{
    switch(entity) {
    case FORTH_SPACE:
      ls
      break;
    case FORTH_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTH_LANG)
      break;
    case NEWLINE:
      std_newline(FORTH_LANG)
    }
  }}
	break;
	case 20:
#line 32 "forth.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case FORTH_SPACE:
      ls
      break;
    case FORTH_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTH_LANG)
      break;
    case NEWLINE:
      std_newline(FORTH_LANG)
    }
  }}
	break;
	case 21:
#line 71 "forth.rl"
	{te = p+1;{
    callback(FORTH_LANG, forth_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 22:
#line 83 "forth.rl"
	{te = p+1;}
	break;
	case 23:
#line 71 "forth.rl"
	{te = p;p--;{
    callback(FORTH_LANG, forth_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 71 "forth.rl"
	{te = p;p--;{
    callback(FORTH_LANG, forth_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 83 "forth.rl"
	{te = p;p--;}
	break;
	case 26:
#line 83 "forth.rl"
	{{p = ((te))-1;}}
	break;
#line 522 "forth.h"
		}
	}

_again:
	_acts = _forth_actions + _forth_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 9:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 535 "forth.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _forth_eof_trans[cs] > 0 ) {
		_trans = _forth_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 110 "forth.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(FORTH_LANG) }
}

#endif

/*****************************************************************************/
