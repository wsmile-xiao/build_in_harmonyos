
#line 1 "rexx.rl"
// rexx.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_REXX_PARSER_H
#define OHCOUNT_REXX_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *REXX_LANG = LANG_REXX;

// the languages entities
const char *rexx_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  REXX_SPACE = 0, REXX_COMMENT, REXX_STRING, REXX_ANY
};

/*****************************************************************************/


#line 28 "rexx.h"
static const char _rexx_actions[] = {
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

static const char _rexx_cond_offsets[] = {
	0, 0, 1, 2, 3, 5, 5, 5, 
	5, 5, 7, 9, 11, 11, 13, 16, 
	16, 16, 16, 16, 17, 17, 17, 17, 
	17
};

static const char _rexx_cond_lengths[] = {
	0, 1, 1, 1, 2, 0, 0, 0, 
	0, 2, 2, 2, 0, 2, 3, 0, 
	0, 0, 0, 1, 0, 0, 0, 0, 
	0
};

static const short _rexx_cond_keys[] = {
	42, 42, 42, 42, 42, 42, 42, 42, 
	47, 47, 13, 13, 42, 42, 13, 13, 
	42, 42, 13, 13, 42, 42, 13, 13, 
	42, 42, 13, 13, 42, 42, 47, 47, 
	13, 13, 0
};

static const char _rexx_cond_spaces[] = {
	2, 2, 2, 2, 2, 0, 1, 0, 
	1, 0, 1, 0, 1, 0, 1, 1, 
	0, 0
};

static const char _rexx_key_offsets[] = {
	0, 0, 7, 14, 21, 31, 36, 39, 
	44, 47, 62, 77, 92, 93, 108, 126, 
	127, 131, 134, 135, 148, 150, 155, 160, 
	161
};

static const short _rexx_trans_keys[] = {
	47, 1322, 1578, 0, 41, 43, 255, 47, 
	1322, 1578, 0, 41, 43, 255, 47, 1322, 
	1578, 0, 41, 43, 255, 1322, 1327, 1578, 
	1583, 0, 41, 43, 46, 48, 255, 10, 
	34, 92, 12, 13, 10, 12, 13, 10, 
	39, 92, 12, 13, 10, 12, 13, 9, 
	10, 12, 32, 47, 269, 525, 810, 1066, 
	0, 8, 14, 41, 43, 255, 9, 10, 
	12, 32, 47, 269, 525, 810, 1066, 0, 
	8, 14, 41, 43, 255, 9, 10, 12, 
	32, 47, 269, 525, 810, 1066, 0, 8, 
	14, 41, 43, 255, 10, 9, 10, 12, 
	32, 47, 269, 525, 810, 1066, 0, 8, 
	14, 41, 43, 255, 9, 10, 12, 32, 
	269, 525, 810, 815, 1066, 1071, 0, 8, 
	14, 41, 43, 46, 48, 255, 10, 32, 
	47, 9, 13, 32, 9, 13, 42, 9, 
	10, 12, 32, 34, 39, 47, 269, 525, 
	0, 8, 14, 255, 9, 32, 10, 34, 
	92, 12, 13, 10, 39, 92, 12, 13, 
	42, 10, 0
};

static const char _rexx_single_lengths[] = {
	0, 3, 3, 3, 4, 3, 1, 3, 
	1, 9, 9, 9, 1, 9, 10, 1, 
	2, 1, 1, 9, 2, 3, 3, 1, 
	1
};

static const char _rexx_range_lengths[] = {
	0, 2, 2, 2, 3, 1, 1, 1, 
	1, 3, 3, 3, 0, 3, 4, 0, 
	1, 1, 0, 2, 0, 1, 1, 0, 
	0
};

static const char _rexx_index_offsets[] = {
	0, 0, 6, 12, 18, 26, 31, 34, 
	39, 42, 55, 68, 81, 83, 96, 111, 
	113, 117, 120, 122, 134, 137, 142, 147, 
	149
};

static const char _rexx_indicies[] = {
	2, 3, 4, 1, 1, 0, 2, 5, 
	6, 1, 1, 0, 7, 3, 4, 1, 
	1, 0, 3, 7, 4, 8, 1, 1, 
	1, 0, 9, 11, 12, 9, 10, 9, 
	9, 10, 9, 11, 14, 9, 13, 9, 
	9, 13, 16, 17, 17, 16, 18, 19, 
	17, 20, 21, 15, 15, 15, 9, 23, 
	24, 24, 23, 25, 26, 24, 27, 28, 
	22, 22, 22, 9, 16, 17, 17, 16, 
	18, 19, 17, 29, 30, 15, 15, 15, 
	9, 17, 9, 16, 17, 17, 16, 31, 
	19, 17, 20, 21, 15, 15, 15, 9, 
	16, 17, 17, 16, 19, 17, 20, 31, 
	21, 32, 15, 15, 15, 15, 9, 33, 
	34, 36, 37, 36, 35, 36, 36, 38, 
	1, 39, 41, 33, 33, 41, 42, 43, 
	44, 45, 46, 40, 40, 34, 41, 41, 
	47, 48, 11, 12, 48, 10, 48, 11, 
	14, 48, 13, 15, 48, 33, 49, 0
};

static const char _rexx_trans_targs[] = {
	16, 1, 2, 3, 4, 3, 4, 2, 
	16, 19, 5, 19, 6, 7, 8, 9, 
	9, 10, 11, 12, 13, 14, 9, 9, 
	10, 11, 12, 13, 14, 13, 14, 11, 
	19, 19, 0, 16, 17, 18, 16, 16, 
	19, 20, 21, 22, 23, 15, 24, 19, 
	19, 19
};

static const char _rexx_trans_actions[] = {
	31, 9, 9, 9, 9, 39, 39, 45, 
	57, 23, 0, 15, 0, 0, 0, 1, 
	0, 0, 1, 0, 1, 1, 60, 48, 
	48, 60, 48, 60, 60, 36, 36, 42, 
	33, 51, 0, 25, 7, 72, 27, 29, 
	54, 3, 64, 64, 68, 5, 5, 17, 
	21, 19
};

static const char _rexx_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	11, 0, 0, 11, 0, 0, 0, 0, 
	0
};

static const char _rexx_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	13, 0, 0, 13, 0, 0, 0, 0, 
	0
};

static const char _rexx_eof_trans[] = {
	0, 1, 1, 1, 1, 10, 10, 10, 
	10, 10, 10, 10, 10, 10, 10, 0, 
	0, 39, 40, 0, 48, 49, 49, 49, 
	50
};

static const int rexx_start = 16;
static const int rexx_first_final = 16;
static const int rexx_error = 0;

static const int rexx_en_rexx_line = 19;
static const int rexx_en_rexx_entity = 16;


#line 96 "rexx.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Pike code.
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
void parse_rexx(char *buffer, int length, int count,
                void (*callback) (const char *lang, const char *entity, int s,
                                  int e, void *udata),
                void *userdata
  ) {
  init

  int nest_count = 0;

  
#line 219 "rexx.h"
	{
	cs = rexx_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 121 "rexx.rl"
  cs = (count) ? rexx_en_rexx_line : rexx_en_rexx_entity;
  
#line 230 "rexx.h"
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
	_acts = _rexx_actions + _rexx_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 13:
#line 1 "NONE"
	{ts = p;}
	break;
#line 252 "rexx.h"
		}
	}

	_widec = (*p);
	_klen = _rexx_cond_lengths[cs];
	_keys = _rexx_cond_keys + (_rexx_cond_offsets[cs]*2);
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
				switch ( _rexx_cond_spaces[_rexx_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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
#line 62 "rexx.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
	case 2: {
		_widec = (short)(1280 + ((*p) - 0));
		if ( 
#line 88 "rexx.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _rexx_trans_keys + _rexx_key_offsets[cs];
	_trans = _rexx_index_offsets[cs];

	_klen = _rexx_single_lengths[cs];
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

	_klen = _rexx_range_lengths[cs];
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
	_trans = _rexx_indicies[_trans];
_eof_trans:
	cs = _rexx_trans_targs[_trans];

	if ( _rexx_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _rexx_actions + _rexx_trans_actions[_trans];
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
#line 31 "rexx.rl"
	{
    switch(entity) {
    case REXX_SPACE:
      ls
      break;
    case REXX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REXX_LANG)
      break;
    case NEWLINE:
      std_newline(REXX_LANG)
    }
  }
	break;
	case 3:
#line 47 "rexx.rl"
	{ nest_count = 0; }
	break;
	case 4:
#line 48 "rexx.rl"
	{ nest_count++; }
	break;
	case 5:
#line 49 "rexx.rl"
	{ nest_count--; }
	break;
	case 6:
#line 53 "rexx.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 69 "rexx.rl"
	{ entity = REXX_SPACE; }
	break;
	case 8:
#line 72 "rexx.rl"
	{ entity = NEWLINE;    }
	break;
	case 9:
#line 73 "rexx.rl"
	{ entity = REXX_ANY;   }
	break;
	case 10:
#line 91 "rexx.rl"
	{ entity = REXX_SPACE;   }
	break;
	case 11:
#line 92 "rexx.rl"
	{ entity = REXX_COMMENT; }
	break;
	case 14:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 15:
#line 70 "rexx.rl"
	{te = p+1;}
	break;
	case 16:
#line 71 "rexx.rl"
	{te = p+1;}
	break;
	case 17:
#line 31 "rexx.rl"
	{te = p+1;{
    switch(entity) {
    case REXX_SPACE:
      ls
      break;
    case REXX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REXX_LANG)
      break;
    case NEWLINE:
      std_newline(REXX_LANG)
    }
  }}
	break;
	case 18:
#line 31 "rexx.rl"
	{te = p+1;{
    switch(entity) {
    case REXX_SPACE:
      ls
      break;
    case REXX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REXX_LANG)
      break;
    case NEWLINE:
      std_newline(REXX_LANG)
    }
  }}
	break;
	case 19:
#line 31 "rexx.rl"
	{te = p;p--;{
    switch(entity) {
    case REXX_SPACE:
      ls
      break;
    case REXX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REXX_LANG)
      break;
    case NEWLINE:
      std_newline(REXX_LANG)
    }
  }}
	break;
	case 20:
#line 31 "rexx.rl"
	{te = p;p--;{
    switch(entity) {
    case REXX_SPACE:
      ls
      break;
    case REXX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REXX_LANG)
      break;
    case NEWLINE:
      std_newline(REXX_LANG)
    }
  }}
	break;
	case 21:
#line 31 "rexx.rl"
	{te = p;p--;{
    switch(entity) {
    case REXX_SPACE:
      ls
      break;
    case REXX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REXX_LANG)
      break;
    case NEWLINE:
      std_newline(REXX_LANG)
    }
  }}
	break;
	case 22:
#line 31 "rexx.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case REXX_SPACE:
      ls
      break;
    case REXX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REXX_LANG)
      break;
    case NEWLINE:
      std_newline(REXX_LANG)
    }
  }}
	break;
	case 23:
#line 78 "rexx.rl"
	{te = p+1;{
    callback(REXX_LANG, rexx_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 94 "rexx.rl"
	{te = p+1;}
	break;
	case 25:
#line 78 "rexx.rl"
	{te = p;p--;{
    callback(REXX_LANG, rexx_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 26:
#line 94 "rexx.rl"
	{te = p;p--;}
	break;
	case 27:
#line 94 "rexx.rl"
	{{p = ((te))-1;}}
	break;
#line 577 "rexx.h"
		}
	}

_again:
	_acts = _rexx_actions + _rexx_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 590 "rexx.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _rexx_eof_trans[cs] > 0 ) {
		_trans = _rexx_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 123 "rexx.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(REXX_LANG) }
}

#endif

/*****************************************************************************/
