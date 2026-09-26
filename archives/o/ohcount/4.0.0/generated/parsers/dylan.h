
#line 1 "dylan.rl"
// dylan.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_DYLAN_PARSER_H
#define OHCOUNT_DYLAN_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *DYLAN_LANG = LANG_DYLAN;

// the languages entities
const char *dylan_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  DYLAN_SPACE = 0, DYLAN_COMMENT, DYLAN_STRING, DYLAN_ANY
};

/*****************************************************************************/


#line 28 "dylan.h"
static const char _dylan_actions[] = {
	0, 1, 1, 1, 4, 1, 5, 1, 
	7, 1, 8, 1, 9, 1, 10, 1, 
	12, 1, 13, 1, 16, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 22, 1, 
	23, 1, 24, 1, 25, 1, 26, 2, 
	3, 2, 2, 5, 14, 2, 6, 15, 
	2, 8, 21, 2, 11, 6, 2, 11, 
	8, 3, 3, 2, 1, 3, 11, 0, 
	6
};

static const char _dylan_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 2, 3, 3, 3, 3, 3, 3, 
	3, 4, 4, 4, 4, 4, 4
};

static const char _dylan_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 0, 0, 0
};

static const short _dylan_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _dylan_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _dylan_key_offsets[] = {
	0, 0, 1, 3, 8, 11, 12, 15, 
	26, 37, 49, 50, 51, 55, 58, 60, 
	63, 76, 78, 83, 88, 90, 93
};

static const short _dylan_trans_keys[] = {
	42, 42, 47, 10, 34, 92, 12, 13, 
	10, 12, 13, 39, 10, 12, 13, 9, 
	10, 12, 32, 42, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 42, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 42, 47, 269, 525, 0, 11, 14, 
	255, 10, 10, 32, 47, 9, 13, 32, 
	9, 13, 42, 47, 10, 12, 13, 9, 
	10, 12, 32, 34, 39, 47, 269, 525, 
	0, 8, 14, 255, 9, 32, 10, 34, 
	92, 12, 13, 10, 39, 92, 12, 13, 
	42, 47, 10, 12, 13, 10, 0
};

static const char _dylan_single_lengths[] = {
	0, 1, 2, 3, 1, 1, 1, 7, 
	7, 8, 1, 1, 2, 1, 2, 1, 
	9, 2, 3, 3, 2, 1, 1
};

static const char _dylan_range_lengths[] = {
	0, 0, 0, 1, 1, 0, 1, 2, 
	2, 2, 0, 0, 1, 1, 0, 1, 
	2, 0, 1, 1, 0, 1, 0
};

static const char _dylan_index_offsets[] = {
	0, 0, 2, 5, 10, 13, 15, 18, 
	28, 38, 49, 51, 53, 57, 60, 63, 
	66, 78, 81, 86, 91, 94, 97
};

static const char _dylan_indicies[] = {
	2, 1, 2, 3, 1, 4, 6, 7, 
	4, 5, 4, 4, 5, 6, 4, 4, 
	4, 8, 10, 11, 11, 10, 12, 13, 
	11, 9, 9, 4, 15, 16, 16, 15, 
	17, 18, 16, 14, 14, 4, 10, 11, 
	11, 10, 12, 19, 13, 11, 9, 9, 
	4, 11, 4, 20, 21, 23, 24, 23, 
	22, 23, 23, 25, 1, 27, 26, 28, 
	28, 27, 30, 20, 20, 30, 31, 32, 
	33, 34, 35, 29, 29, 21, 30, 30, 
	36, 37, 6, 7, 37, 5, 37, 37, 
	38, 37, 8, 9, 39, 37, 40, 40, 
	41, 20, 42, 0
};

static const char _dylan_trans_targs[] = {
	12, 1, 2, 12, 16, 3, 16, 4, 
	5, 7, 7, 8, 9, 10, 7, 7, 
	8, 9, 10, 16, 16, 0, 12, 13, 
	14, 12, 12, 15, 12, 16, 17, 18, 
	19, 20, 11, 22, 16, 16, 6, 21, 
	16, 21, 16
};

static const char _dylan_trans_actions[] = {
	37, 9, 9, 48, 27, 0, 17, 0, 
	0, 1, 0, 0, 1, 0, 57, 39, 
	39, 57, 39, 15, 42, 0, 29, 7, 
	54, 31, 35, 9, 33, 45, 3, 61, 
	61, 51, 5, 5, 19, 25, 0, 1, 
	21, 0, 23
};

static const char _dylan_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 11, 0, 0, 0, 
	11, 0, 0, 0, 0, 0, 0
};

static const char _dylan_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 13, 0, 0, 0, 
	13, 0, 0, 0, 0, 0, 0
};

static const char _dylan_eof_trans[] = {
	0, 1, 1, 5, 5, 5, 5, 5, 
	5, 5, 5, 0, 0, 26, 27, 29, 
	0, 37, 38, 38, 38, 41, 43
};

static const int dylan_start = 12;
static const int dylan_first_final = 12;
static const int dylan_error = 0;

static const int dylan_en_dylan_line = 16;
static const int dylan_en_dylan_entity = 12;


#line 86 "dylan.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Dylan code.
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
void parse_dylan(char *buffer, int length, int count,
                 void (*callback) (const char *lang, const char *entity, int s,
                                   int e, void *udata),
                 void *userdata
  ) {
  init

  
#line 185 "dylan.h"
	{
	cs = dylan_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 109 "dylan.rl"
  cs = (count) ? dylan_en_dylan_line : dylan_en_dylan_entity;
  
#line 196 "dylan.h"
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
	_acts = _dylan_actions + _dylan_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = p;}
	break;
#line 218 "dylan.h"
		}
	}

	_widec = (*p);
	_klen = _dylan_cond_lengths[cs];
	_keys = _dylan_cond_keys + (_dylan_cond_offsets[cs]*2);
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
				switch ( _dylan_cond_spaces[_dylan_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _dylan_trans_keys + _dylan_key_offsets[cs];
	_trans = _dylan_index_offsets[cs];

	_klen = _dylan_single_lengths[cs];
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

	_klen = _dylan_range_lengths[cs];
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
	_trans = _dylan_indicies[_trans];
_eof_trans:
	cs = _dylan_trans_targs[_trans];

	if ( _dylan_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _dylan_actions + _dylan_trans_actions[_trans];
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
#line 31 "dylan.rl"
	{
    switch(entity) {
    case DYLAN_SPACE:
      ls
      break;
    case DYLAN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DYLAN_LANG)
      break;
    case NEWLINE:
      std_newline(DYLAN_LANG)
    }
  }
	break;
	case 3:
#line 50 "dylan.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 63 "dylan.rl"
	{ entity = DYLAN_SPACE; }
	break;
	case 5:
#line 66 "dylan.rl"
	{ entity = NEWLINE;     }
	break;
	case 6:
#line 67 "dylan.rl"
	{ entity = DYLAN_ANY;   }
	break;
	case 7:
#line 81 "dylan.rl"
	{ entity = DYLAN_SPACE;   }
	break;
	case 8:
#line 82 "dylan.rl"
	{ entity = DYLAN_COMMENT; }
	break;
	case 11:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 12:
#line 64 "dylan.rl"
	{te = p+1;}
	break;
	case 13:
#line 65 "dylan.rl"
	{te = p+1;}
	break;
	case 14:
#line 31 "dylan.rl"
	{te = p+1;{
    switch(entity) {
    case DYLAN_SPACE:
      ls
      break;
    case DYLAN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DYLAN_LANG)
      break;
    case NEWLINE:
      std_newline(DYLAN_LANG)
    }
  }}
	break;
	case 15:
#line 31 "dylan.rl"
	{te = p+1;{
    switch(entity) {
    case DYLAN_SPACE:
      ls
      break;
    case DYLAN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DYLAN_LANG)
      break;
    case NEWLINE:
      std_newline(DYLAN_LANG)
    }
  }}
	break;
	case 16:
#line 31 "dylan.rl"
	{te = p;p--;{
    switch(entity) {
    case DYLAN_SPACE:
      ls
      break;
    case DYLAN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DYLAN_LANG)
      break;
    case NEWLINE:
      std_newline(DYLAN_LANG)
    }
  }}
	break;
	case 17:
#line 64 "dylan.rl"
	{te = p;p--;}
	break;
	case 18:
#line 31 "dylan.rl"
	{te = p;p--;{
    switch(entity) {
    case DYLAN_SPACE:
      ls
      break;
    case DYLAN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DYLAN_LANG)
      break;
    case NEWLINE:
      std_newline(DYLAN_LANG)
    }
  }}
	break;
	case 19:
#line 31 "dylan.rl"
	{te = p;p--;{
    switch(entity) {
    case DYLAN_SPACE:
      ls
      break;
    case DYLAN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DYLAN_LANG)
      break;
    case NEWLINE:
      std_newline(DYLAN_LANG)
    }
  }}
	break;
	case 20:
#line 31 "dylan.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case DYLAN_SPACE:
      ls
      break;
    case DYLAN_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DYLAN_LANG)
      break;
    case NEWLINE:
      std_newline(DYLAN_LANG)
    }
  }}
	break;
	case 21:
#line 72 "dylan.rl"
	{te = p+1;{
    callback(DYLAN_LANG, dylan_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 22:
#line 84 "dylan.rl"
	{te = p+1;}
	break;
	case 23:
#line 72 "dylan.rl"
	{te = p;p--;{
    callback(DYLAN_LANG, dylan_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 72 "dylan.rl"
	{te = p;p--;{
    callback(DYLAN_LANG, dylan_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 84 "dylan.rl"
	{te = p;p--;}
	break;
	case 26:
#line 84 "dylan.rl"
	{{p = ((te))-1;}}
	break;
#line 527 "dylan.h"
		}
	}

_again:
	_acts = _dylan_actions + _dylan_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 9:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 540 "dylan.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _dylan_eof_trans[cs] > 0 ) {
		_trans = _dylan_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 111 "dylan.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(DYLAN_LANG) }
}

#endif

/*****************************************************************************/
