
#line 1 "factor.rl"
// factor.rl written by Alfredo Beaumont <alfredo.beaumont@gmail.com>
// Based on lisp.rl

/************************* Required for every parser *************************/
#ifndef OHCOUNT_FACTOR_PARSER_H
#define OHCOUNT_FACTOR_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *FACTOR_LANG = LANG_FACTOR;

// the languages entities
const char *factor_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  FACTOR_SPACE = 0, FACTOR_COMMENT, FACTOR_STRING, FACTOR_ANY
};

/*****************************************************************************/


#line 29 "factor.h"
static const char _factor_actions[] = {
	0, 1, 0, 1, 4, 1, 5, 1, 
	7, 1, 8, 1, 10, 1, 13, 1, 
	14, 1, 15, 1, 16, 1, 17, 2, 
	1, 6, 2, 3, 2, 2, 5, 11, 
	2, 6, 12, 3, 3, 2, 0, 3, 
	3, 2, 10, 3, 9, 0, 6
};

static const char _factor_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	2, 2, 2, 2, 2, 3, 3, 3, 
	4
};

static const char _factor_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 1, 1, 
	0, 0, 0, 0, 1, 0, 0, 1, 
	0
};

static const short _factor_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _factor_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _factor_key_offsets[] = {
	0, 0, 1, 2, 3, 4, 5, 17, 
	29, 32, 33, 34, 34, 46, 48, 51, 
	63
};

static const short _factor_trans_keys[] = {
	84, 79, 68, 79, 58, 9, 10, 12, 
	32, 34, 92, 269, 525, 0, 11, 14, 
	255, 9, 10, 12, 32, 34, 92, 269, 
	525, 0, 11, 14, 255, 10, 12, 13, 
	10, 10, 9, 10, 12, 32, 33, 34, 
	269, 525, 0, 8, 14, 255, 9, 32, 
	10, 12, 13, 9, 10, 12, 32, 34, 
	92, 269, 525, 0, 11, 14, 255, 10, 
	0
};

static const char _factor_single_lengths[] = {
	0, 1, 1, 1, 1, 1, 8, 8, 
	1, 1, 1, 0, 8, 2, 1, 8, 
	1
};

static const char _factor_range_lengths[] = {
	0, 0, 0, 0, 0, 0, 2, 2, 
	1, 0, 0, 0, 2, 0, 1, 2, 
	0
};

static const char _factor_index_offsets[] = {
	0, 0, 2, 4, 6, 8, 10, 21, 
	32, 35, 37, 39, 40, 51, 54, 57, 
	68
};

static const char _factor_indicies[] = {
	0, 1, 2, 1, 3, 1, 4, 1, 
	5, 1, 8, 9, 9, 8, 10, 11, 
	12, 9, 7, 7, 6, 14, 15, 15, 
	14, 16, 17, 18, 15, 13, 13, 6, 
	6, 6, 7, 9, 6, 19, 1, 1, 
	21, 19, 19, 21, 22, 23, 24, 25, 
	20, 20, 1, 21, 21, 26, 27, 27, 
	28, 8, 9, 9, 8, 10, 11, 12, 
	9, 7, 7, 29, 19, 30, 0
};

static const char _factor_trans_targs[] = {
	2, 0, 3, 4, 5, 11, 12, 6, 
	6, 7, 12, 8, 9, 6, 6, 7, 
	12, 8, 9, 12, 12, 13, 14, 15, 
	10, 16, 12, 12, 14, 12, 12
};

static const char _factor_trans_actions[] = {
	0, 0, 0, 0, 0, 0, 21, 1, 
	0, 0, 11, 0, 0, 35, 26, 26, 
	39, 26, 26, 29, 32, 3, 23, 43, 
	5, 5, 13, 15, 0, 19, 17
};

static const char _factor_to_state_actions[] = {
	0, 7, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 7, 0, 0, 0, 
	0
};

static const char _factor_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 9, 0, 0, 0, 
	0
};

static const char _factor_eof_trans[] = {
	0, 0, 0, 0, 0, 0, 7, 7, 
	7, 7, 0, 0, 0, 27, 28, 30, 
	31
};

static const int factor_start = 1;
static const int factor_first_final = 11;
static const int factor_error = 0;

static const int factor_en_factor_line = 12;
static const int factor_en_factor_entity = 1;


#line 77 "factor.rl"


/* Parses a string buffer with Factor code.
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
void parse_factor(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  
#line 170 "factor.h"
	{
	cs = factor_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 98 "factor.rl"
  cs = (count) ? factor_en_factor_line : factor_en_factor_entity;
  
#line 181 "factor.h"
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
	_acts = _factor_actions + _factor_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = p;}
	break;
#line 203 "factor.h"
		}
	}

	_widec = (*p);
	_klen = _factor_cond_lengths[cs];
	_keys = _factor_cond_keys + (_factor_cond_offsets[cs]*2);
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
				switch ( _factor_cond_spaces[_factor_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _factor_trans_keys + _factor_key_offsets[cs];
	_trans = _factor_index_offsets[cs];

	_klen = _factor_single_lengths[cs];
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

	_klen = _factor_range_lengths[cs];
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
	_trans = _factor_indicies[_trans];
_eof_trans:
	cs = _factor_trans_targs[_trans];

	if ( _factor_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _factor_actions + _factor_trans_actions[_trans];
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
#line 32 "factor.rl"
	{
    switch(entity) {
    case FACTOR_SPACE:
      ls
      break;
    case FACTOR_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FACTOR_LANG)
      break;
    case NEWLINE:
      std_newline(FACTOR_LANG)
    }
  }
	break;
	case 3:
#line 52 "factor.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 62 "factor.rl"
	{ entity = FACTOR_SPACE; }
	break;
	case 5:
#line 65 "factor.rl"
	{ entity = NEWLINE;    }
	break;
	case 6:
#line 66 "factor.rl"
	{ entity = FACTOR_ANY;   }
	break;
	case 9:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 10:
#line 64 "factor.rl"
	{te = p+1;}
	break;
	case 11:
#line 32 "factor.rl"
	{te = p+1;{
    switch(entity) {
    case FACTOR_SPACE:
      ls
      break;
    case FACTOR_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FACTOR_LANG)
      break;
    case NEWLINE:
      std_newline(FACTOR_LANG)
    }
  }}
	break;
	case 12:
#line 32 "factor.rl"
	{te = p+1;{
    switch(entity) {
    case FACTOR_SPACE:
      ls
      break;
    case FACTOR_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FACTOR_LANG)
      break;
    case NEWLINE:
      std_newline(FACTOR_LANG)
    }
  }}
	break;
	case 13:
#line 32 "factor.rl"
	{te = p;p--;{
    switch(entity) {
    case FACTOR_SPACE:
      ls
      break;
    case FACTOR_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FACTOR_LANG)
      break;
    case NEWLINE:
      std_newline(FACTOR_LANG)
    }
  }}
	break;
	case 14:
#line 63 "factor.rl"
	{te = p;p--;}
	break;
	case 15:
#line 32 "factor.rl"
	{te = p;p--;{
    switch(entity) {
    case FACTOR_SPACE:
      ls
      break;
    case FACTOR_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FACTOR_LANG)
      break;
    case NEWLINE:
      std_newline(FACTOR_LANG)
    }
  }}
	break;
	case 16:
#line 32 "factor.rl"
	{te = p;p--;{
    switch(entity) {
    case FACTOR_SPACE:
      ls
      break;
    case FACTOR_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FACTOR_LANG)
      break;
    case NEWLINE:
      std_newline(FACTOR_LANG)
    }
  }}
	break;
	case 17:
#line 32 "factor.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case FACTOR_SPACE:
      ls
      break;
    case FACTOR_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FACTOR_LANG)
      break;
    case NEWLINE:
      std_newline(FACTOR_LANG)
    }
  }}
	break;
#line 470 "factor.h"
		}
	}

_again:
	_acts = _factor_actions + _factor_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 483 "factor.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _factor_eof_trans[cs] > 0 ) {
		_trans = _factor_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 100 "factor.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(FACTOR_LANG) }
}

#endif
