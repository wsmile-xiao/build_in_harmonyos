
#line 1 "smalltalk.rl"
// smalltalk.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_SMALLTALK_PARSER_H
#define OHCOUNT_SMALLTALK_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *SMALLTALK_LANG = LANG_SMALLTALK;

// the languages entities
const char *smalltalk_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  SMALLTALK_SPACE = 0, SMALLTALK_COMMENT, SMALLTALK_STRING, SMALLTALK_ANY
};

/*****************************************************************************/


#line 28 "smalltalk.h"
static const char _smalltalk_actions[] = {
	0, 1, 1, 1, 4, 1, 5, 1, 
	7, 1, 8, 1, 9, 1, 10, 1, 
	12, 1, 13, 1, 16, 1, 17, 1, 
	18, 1, 19, 1, 21, 1, 22, 1, 
	23, 1, 24, 2, 3, 2, 2, 5, 
	14, 2, 6, 15, 2, 8, 20, 2, 
	11, 8, 3, 3, 2, 1, 3, 3, 
	2, 12, 3, 11, 0, 6, 3, 11, 
	1, 6
};

static const char _smalltalk_cond_offsets[] = {
	0, 0, 0, 1, 2, 2, 2, 2, 
	2, 2, 2, 3, 3, 4, 4
};

static const char _smalltalk_cond_lengths[] = {
	0, 0, 1, 1, 0, 0, 0, 0, 
	0, 0, 1, 0, 1, 0, 0
};

static const short _smalltalk_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _smalltalk_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _smalltalk_key_offsets[] = {
	0, 0, 1, 12, 23, 24, 28, 29, 
	33, 36, 37, 49, 51, 62, 66
};

static const short _smalltalk_trans_keys[] = {
	34, 9, 10, 12, 32, 34, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	34, 269, 525, 0, 11, 14, 255, 10, 
	10, 39, 12, 13, 10, 32, 34, 9, 
	13, 32, 9, 13, 34, 9, 10, 12, 
	32, 34, 39, 269, 525, 0, 8, 14, 
	255, 9, 32, 9, 10, 12, 32, 34, 
	269, 525, 0, 11, 14, 255, 10, 39, 
	12, 13, 10, 0
};

static const char _smalltalk_single_lengths[] = {
	0, 1, 7, 7, 1, 2, 1, 2, 
	1, 1, 8, 2, 7, 2, 1
};

static const char _smalltalk_range_lengths[] = {
	0, 0, 2, 2, 0, 1, 0, 1, 
	1, 0, 2, 0, 2, 1, 0
};

static const char _smalltalk_index_offsets[] = {
	0, 0, 2, 12, 22, 24, 28, 30, 
	34, 37, 39, 50, 53, 63, 67
};

static const char _smalltalk_indicies[] = {
	2, 1, 5, 6, 6, 5, 7, 8, 
	6, 4, 4, 3, 10, 11, 11, 10, 
	12, 13, 11, 9, 9, 3, 6, 3, 
	3, 15, 3, 14, 16, 17, 19, 20, 
	19, 18, 19, 19, 21, 2, 1, 24, 
	16, 16, 24, 25, 26, 27, 28, 23, 
	23, 17, 24, 24, 29, 5, 6, 6, 
	5, 7, 8, 6, 4, 4, 30, 30, 
	15, 30, 14, 16, 31, 0
};

static const char _smalltalk_trans_targs[] = {
	7, 1, 7, 10, 2, 2, 3, 10, 
	4, 2, 2, 3, 10, 4, 5, 10, 
	10, 0, 7, 8, 9, 7, 7, 10, 
	11, 12, 13, 6, 14, 10, 10, 10
};

static const char _smalltalk_trans_actions[] = {
	33, 9, 44, 25, 1, 0, 0, 15, 
	0, 50, 35, 35, 54, 35, 0, 17, 
	38, 0, 27, 7, 47, 29, 31, 41, 
	3, 62, 58, 5, 5, 19, 23, 21
};

static const char _smalltalk_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 11, 
	0, 0, 11, 0, 0, 0, 0
};

static const char _smalltalk_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 13, 
	0, 0, 13, 0, 0, 0, 0
};

static const char _smalltalk_eof_trans[] = {
	0, 1, 4, 4, 4, 4, 0, 0, 
	22, 23, 0, 30, 31, 31, 32
};

static const int smalltalk_start = 7;
static const int smalltalk_first_final = 7;
static const int smalltalk_error = 0;

static const int smalltalk_en_smalltalk_line = 10;
static const int smalltalk_en_smalltalk_entity = 7;


#line 81 "smalltalk.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Smalltalk code.
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
void parse_smalltalk(char *buffer, int length, int count,
                     void (*callback) (const char *lang, const char *entity,
                                       int s, int e, void *udata),
                     void *userdata
  ) {
  init

  
#line 165 "smalltalk.h"
	{
	cs = smalltalk_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 104 "smalltalk.rl"
  cs = (count) ? smalltalk_en_smalltalk_line : smalltalk_en_smalltalk_entity;
  
#line 176 "smalltalk.h"
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
	_acts = _smalltalk_actions + _smalltalk_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = p;}
	break;
#line 198 "smalltalk.h"
		}
	}

	_widec = (*p);
	_klen = _smalltalk_cond_lengths[cs];
	_keys = _smalltalk_cond_keys + (_smalltalk_cond_offsets[cs]*2);
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
				switch ( _smalltalk_cond_spaces[_smalltalk_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _smalltalk_trans_keys + _smalltalk_key_offsets[cs];
	_trans = _smalltalk_index_offsets[cs];

	_klen = _smalltalk_single_lengths[cs];
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

	_klen = _smalltalk_range_lengths[cs];
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
	_trans = _smalltalk_indicies[_trans];
_eof_trans:
	cs = _smalltalk_trans_targs[_trans];

	if ( _smalltalk_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _smalltalk_actions + _smalltalk_trans_actions[_trans];
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
#line 31 "smalltalk.rl"
	{
    switch(entity) {
    case SMALLTALK_SPACE:
      ls
      break;
    case SMALLTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SMALLTALK_LANG)
      break;
    case NEWLINE:
      std_newline(SMALLTALK_LANG)
    }
  }
	break;
	case 3:
#line 49 "smalltalk.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 59 "smalltalk.rl"
	{ entity = SMALLTALK_SPACE; }
	break;
	case 5:
#line 62 "smalltalk.rl"
	{ entity = NEWLINE;         }
	break;
	case 6:
#line 63 "smalltalk.rl"
	{ entity = SMALLTALK_ANY;   }
	break;
	case 7:
#line 76 "smalltalk.rl"
	{ entity = SMALLTALK_SPACE;   }
	break;
	case 8:
#line 77 "smalltalk.rl"
	{ entity = SMALLTALK_COMMENT; }
	break;
	case 11:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 12:
#line 60 "smalltalk.rl"
	{te = p+1;}
	break;
	case 13:
#line 61 "smalltalk.rl"
	{te = p+1;}
	break;
	case 14:
#line 31 "smalltalk.rl"
	{te = p+1;{
    switch(entity) {
    case SMALLTALK_SPACE:
      ls
      break;
    case SMALLTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SMALLTALK_LANG)
      break;
    case NEWLINE:
      std_newline(SMALLTALK_LANG)
    }
  }}
	break;
	case 15:
#line 31 "smalltalk.rl"
	{te = p+1;{
    switch(entity) {
    case SMALLTALK_SPACE:
      ls
      break;
    case SMALLTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SMALLTALK_LANG)
      break;
    case NEWLINE:
      std_newline(SMALLTALK_LANG)
    }
  }}
	break;
	case 16:
#line 31 "smalltalk.rl"
	{te = p;p--;{
    switch(entity) {
    case SMALLTALK_SPACE:
      ls
      break;
    case SMALLTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SMALLTALK_LANG)
      break;
    case NEWLINE:
      std_newline(SMALLTALK_LANG)
    }
  }}
	break;
	case 17:
#line 31 "smalltalk.rl"
	{te = p;p--;{
    switch(entity) {
    case SMALLTALK_SPACE:
      ls
      break;
    case SMALLTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SMALLTALK_LANG)
      break;
    case NEWLINE:
      std_newline(SMALLTALK_LANG)
    }
  }}
	break;
	case 18:
#line 31 "smalltalk.rl"
	{te = p;p--;{
    switch(entity) {
    case SMALLTALK_SPACE:
      ls
      break;
    case SMALLTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SMALLTALK_LANG)
      break;
    case NEWLINE:
      std_newline(SMALLTALK_LANG)
    }
  }}
	break;
	case 19:
#line 31 "smalltalk.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case SMALLTALK_SPACE:
      ls
      break;
    case SMALLTALK_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SMALLTALK_LANG)
      break;
    case NEWLINE:
      std_newline(SMALLTALK_LANG)
    }
  }}
	break;
	case 20:
#line 68 "smalltalk.rl"
	{te = p+1;{
    callback(SMALLTALK_LANG, smalltalk_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 21:
#line 79 "smalltalk.rl"
	{te = p+1;}
	break;
	case 22:
#line 68 "smalltalk.rl"
	{te = p;p--;{
    callback(SMALLTALK_LANG, smalltalk_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 23:
#line 79 "smalltalk.rl"
	{te = p;p--;}
	break;
	case 24:
#line 79 "smalltalk.rl"
	{{p = ((te))-1;}}
	break;
#line 499 "smalltalk.h"
		}
	}

_again:
	_acts = _smalltalk_actions + _smalltalk_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 9:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 512 "smalltalk.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _smalltalk_eof_trans[cs] > 0 ) {
		_trans = _smalltalk_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 106 "smalltalk.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(SMALLTALK_LANG) }
}

#endif

/*****************************************************************************/
