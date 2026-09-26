
#line 1 "classic_basic.rl"
/************************* Required for every parser *************************/
#ifndef OHCOUNT_CLASSIC_BASIC_PARSER_H
#define OHCOUNT_CLASSIC_BASIC_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *CB_LANG = LANG_CLASSIC_BASIC;

// the languages entities
const char *cb_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  CB_SPACE = 0, CB_COMMENT, CB_STRING, CB_ANY,
};

/*****************************************************************************/


#line 26 "classic_basic.h"
static const char _classic_basic_actions[] = {
	0, 1, 1, 1, 2, 1, 3, 1, 
	5, 1, 6, 1, 7, 1, 8, 1, 
	10, 1, 13, 1, 14, 1, 15, 1, 
	16, 1, 17, 1, 18, 1, 19, 1, 
	20, 1, 21, 1, 22, 2, 3, 11, 
	2, 4, 12, 2, 9, 4, 2, 9, 
	6, 3, 9, 0, 4
};

static const char _classic_basic_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 1, 1
};

static const char _classic_basic_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 1, 0, 
	0, 0, 0, 0
};

static const short _classic_basic_cond_keys[] = {
	13, 13, 0
};

static const char _classic_basic_cond_spaces[] = {
	0, 0
};

static const char _classic_basic_key_offsets[] = {
	0, 0, 2, 4, 9, 12, 17, 19, 
	21, 25, 26, 32, 35, 38, 40, 55, 
	57, 62, 66, 69
};

static const short _classic_basic_trans_keys[] = {
	77, 109, 9, 32, 10, 34, 92, 12, 
	13, 10, 12, 13, 9, 32, 39, 82, 
	114, 69, 101, 77, 109, 9, 32, 48, 
	57, 10, 32, 39, 82, 114, 9, 13, 
	32, 9, 13, 10, 12, 13, 69, 101, 
	9, 10, 12, 32, 34, 269, 525, 0, 
	8, 14, 47, 48, 57, 58, 255, 9, 
	32, 10, 34, 92, 12, 13, 9, 32, 
	48, 57, 10, 12, 13, 10, 0
};

static const char _classic_basic_single_lengths[] = {
	0, 2, 2, 3, 1, 5, 2, 2, 
	2, 1, 4, 1, 1, 2, 7, 2, 
	3, 2, 1, 1
};

static const char _classic_basic_range_lengths[] = {
	0, 0, 0, 1, 1, 0, 0, 0, 
	1, 0, 1, 1, 1, 0, 4, 0, 
	1, 1, 1, 0
};

static const char _classic_basic_index_offsets[] = {
	0, 0, 3, 6, 11, 14, 20, 23, 
	26, 30, 32, 38, 41, 44, 47, 59, 
	62, 67, 71, 74
};

static const char _classic_basic_indicies[] = {
	1, 1, 0, 2, 2, 0, 3, 5, 
	6, 3, 4, 3, 3, 4, 7, 7, 
	8, 9, 9, 3, 10, 10, 3, 8, 
	8, 3, 7, 7, 11, 3, 12, 13, 
	15, 2, 16, 16, 15, 14, 15, 15, 
	17, 18, 18, 2, 20, 20, 19, 22, 
	12, 12, 22, 23, 25, 26, 21, 21, 
	24, 21, 13, 22, 22, 27, 28, 5, 
	6, 28, 4, 7, 7, 11, 28, 29, 
	29, 30, 12, 31, 0
};

static const char _classic_basic_trans_targs[] = {
	10, 2, 12, 14, 3, 14, 4, 5, 
	18, 6, 7, 8, 14, 0, 10, 11, 
	13, 10, 10, 10, 1, 14, 15, 16, 
	17, 9, 19, 14, 14, 14, 18, 14
};

static const char _classic_basic_trans_actions[] = {
	35, 9, 9, 25, 0, 15, 0, 0, 
	1, 0, 0, 0, 37, 0, 27, 7, 
	46, 29, 31, 33, 9, 40, 3, 49, 
	43, 5, 5, 17, 23, 19, 0, 21
};

static const char _classic_basic_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 11, 0, 0, 0, 11, 0, 
	0, 0, 0, 0
};

static const char _classic_basic_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 13, 0, 0, 0, 13, 0, 
	0, 0, 0, 0
};

static const char _classic_basic_eof_trans[] = {
	0, 1, 1, 4, 4, 4, 4, 4, 
	4, 0, 0, 18, 19, 20, 0, 28, 
	29, 29, 30, 32
};

static const int classic_basic_start = 10;
static const int classic_basic_first_final = 10;
static const int classic_basic_error = 0;

static const int classic_basic_en_cb_line = 14;
static const int classic_basic_en_cb_entity = 10;


#line 71 "classic_basic.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Structured BASIC code.
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
void parse_classic_basic(char *buffer, int length, int count,
                         void (*callback) (const char *lang, const char *entity,
                                           int s, int e, void *udata),
                         void *userdata
  ) {
  init

  
#line 170 "classic_basic.h"
	{
	cs = classic_basic_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 94 "classic_basic.rl"
  cs = (count) ? classic_basic_en_cb_line : classic_basic_en_cb_entity;
  
#line 181 "classic_basic.h"
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
	_acts = _classic_basic_actions + _classic_basic_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = p;}
	break;
#line 203 "classic_basic.h"
		}
	}

	_widec = (*p);
	_klen = _classic_basic_cond_lengths[cs];
	_keys = _classic_basic_cond_keys + (_classic_basic_cond_offsets[cs]*2);
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
				switch ( _classic_basic_cond_spaces[_classic_basic_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _classic_basic_trans_keys + _classic_basic_key_offsets[cs];
	_trans = _classic_basic_index_offsets[cs];

	_klen = _classic_basic_single_lengths[cs];
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

	_klen = _classic_basic_range_lengths[cs];
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
	_trans = _classic_basic_indicies[_trans];
_eof_trans:
	cs = _classic_basic_trans_targs[_trans];

	if ( _classic_basic_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _classic_basic_actions + _classic_basic_trans_actions[_trans];
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
#line 50 "classic_basic.rl"
	{ entity = CB_SPACE; }
	break;
	case 3:
#line 53 "classic_basic.rl"
	{ entity = NEWLINE;  }
	break;
	case 4:
#line 54 "classic_basic.rl"
	{ entity = CB_ANY;   }
	break;
	case 5:
#line 66 "classic_basic.rl"
	{ entity = CB_SPACE;   }
	break;
	case 6:
#line 67 "classic_basic.rl"
	{ entity = CB_COMMENT; }
	break;
	case 9:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 10:
#line 52 "classic_basic.rl"
	{te = p+1;}
	break;
	case 11:
#line 29 "classic_basic.rl"
	{te = p+1;{
    switch(entity) {
    case CB_SPACE:
      ls
      break;
    case CB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CB_LANG)
      break;
    case NEWLINE:
      std_newline(CB_LANG)
    }
  }}
	break;
	case 12:
#line 29 "classic_basic.rl"
	{te = p+1;{
    switch(entity) {
    case CB_SPACE:
      ls
      break;
    case CB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CB_LANG)
      break;
    case NEWLINE:
      std_newline(CB_LANG)
    }
  }}
	break;
	case 13:
#line 29 "classic_basic.rl"
	{te = p;p--;{
    switch(entity) {
    case CB_SPACE:
      ls
      break;
    case CB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CB_LANG)
      break;
    case NEWLINE:
      std_newline(CB_LANG)
    }
  }}
	break;
	case 14:
#line 51 "classic_basic.rl"
	{te = p;p--;}
	break;
	case 15:
#line 29 "classic_basic.rl"
	{te = p;p--;{
    switch(entity) {
    case CB_SPACE:
      ls
      break;
    case CB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CB_LANG)
      break;
    case NEWLINE:
      std_newline(CB_LANG)
    }
  }}
	break;
	case 16:
#line 29 "classic_basic.rl"
	{te = p;p--;{
    switch(entity) {
    case CB_SPACE:
      ls
      break;
    case CB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CB_LANG)
      break;
    case NEWLINE:
      std_newline(CB_LANG)
    }
  }}
	break;
	case 17:
#line 29 "classic_basic.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case CB_SPACE:
      ls
      break;
    case CB_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CB_LANG)
      break;
    case NEWLINE:
      std_newline(CB_LANG)
    }
  }}
	break;
	case 18:
#line 69 "classic_basic.rl"
	{te = p+1;}
	break;
	case 19:
#line 59 "classic_basic.rl"
	{te = p;p--;{
    callback(CB_LANG, cb_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 20:
#line 59 "classic_basic.rl"
	{te = p;p--;{
    callback(CB_LANG, cb_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 21:
#line 69 "classic_basic.rl"
	{te = p;p--;}
	break;
	case 22:
#line 69 "classic_basic.rl"
	{{p = ((te))-1;}}
	break;
#line 480 "classic_basic.h"
		}
	}

_again:
	_acts = _classic_basic_actions + _classic_basic_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 493 "classic_basic.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _classic_basic_eof_trans[cs] > 0 ) {
		_trans = _classic_basic_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 96 "classic_basic.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(CB_LANG) }
}

#endif

/*****************************************************************************/
