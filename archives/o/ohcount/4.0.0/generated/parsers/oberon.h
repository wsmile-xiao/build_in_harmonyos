
#line 1 "oberon.rl"
// oberon.rl, 
// derived from code written by Mitchell Foral. mitchell<att>caladbolg<dott>net


/************************* Required for every parser *************************/
#ifndef OHCOUNT_OBERON_PARSER_H
#define OHCOUNT_OBERON_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *OBERON_LANG = LANG_OBERON;

// the languages entities
const char *oberon_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  OBERON_SPACE = 0, OBERON_COMMENT, OBERON_STRING, OBERON_ANY
};

/*****************************************************************************/


#line 30 "oberon.h"
static const char _oberon_actions[] = {
	0, 1, 1, 1, 7, 1, 8, 1, 
	10, 1, 11, 1, 12, 1, 13, 1, 
	14, 1, 19, 1, 22, 1, 23, 1, 
	24, 1, 25, 1, 26, 1, 29, 1, 
	30, 1, 31, 1, 32, 2, 1, 18, 
	2, 4, 1, 2, 4, 11, 2, 5, 
	1, 2, 5, 11, 2, 6, 2, 2, 
	8, 20, 2, 9, 21, 2, 11, 27, 
	2, 12, 28, 2, 15, 12, 2, 15, 
	16, 3, 6, 2, 1, 3, 15, 0, 
	9, 3, 15, 3, 9, 3, 15, 3, 
	11, 4, 15, 0, 9, 17
};

static const char _oberon_cond_offsets[] = {
	0, 0, 0, 0, 1, 2, 3, 5, 
	5, 5, 7, 9, 11, 11, 13, 16, 
	16, 16, 16, 16, 16, 16, 17, 17, 
	17, 17, 17
};

static const char _oberon_cond_lengths[] = {
	0, 0, 0, 1, 1, 1, 2, 0, 
	0, 2, 2, 2, 0, 2, 3, 0, 
	0, 0, 0, 0, 0, 1, 0, 0, 
	0, 0, 0
};

static const short _oberon_cond_keys[] = {
	42, 42, 42, 42, 42, 42, 41, 41, 
	42, 42, 13, 13, 42, 42, 13, 13, 
	42, 42, 13, 13, 42, 42, 13, 13, 
	42, 42, 13, 13, 41, 41, 42, 42, 
	13, 13, 0
};

static const char _oberon_cond_spaces[] = {
	2, 2, 2, 2, 2, 0, 1, 0, 
	1, 0, 1, 0, 1, 0, 1, 1, 
	0, 0
};

static const char _oberon_key_offsets[] = {
	0, 0, 1, 2, 9, 16, 24, 33, 
	37, 42, 57, 72, 87, 88, 104, 121, 
	122, 128, 131, 132, 133, 134, 147, 149, 
	153, 158, 159
};

static const short _oberon_trans_keys[] = {
	34, 39, 40, 1322, 1578, 0, 41, 43, 
	255, 40, 1322, 1578, 0, 41, 43, 255, 
	40, 41, 1322, 1578, 0, 39, 43, 255, 
	40, 1321, 1322, 1577, 1578, 0, 39, 43, 
	255, 10, 34, 12, 13, 10, 34, 39, 
	12, 13, 9, 10, 12, 32, 40, 269, 
	525, 810, 1066, 0, 8, 14, 41, 43, 
	255, 9, 10, 12, 32, 40, 269, 525, 
	810, 1066, 0, 8, 14, 41, 43, 255, 
	9, 10, 12, 32, 40, 269, 525, 810, 
	1066, 0, 8, 14, 41, 43, 255, 10, 
	9, 10, 12, 32, 40, 41, 269, 525, 
	810, 1066, 0, 8, 14, 39, 43, 255, 
	9, 10, 12, 32, 40, 269, 525, 809, 
	810, 1065, 1066, 0, 8, 14, 39, 43, 
	255, 10, 32, 34, 39, 40, 9, 13, 
	32, 9, 13, 34, 39, 42, 9, 10, 
	12, 32, 34, 39, 40, 269, 525, 0, 
	8, 14, 255, 9, 32, 10, 34, 12, 
	13, 10, 34, 39, 12, 13, 42, 10, 
	0
};

static const char _oberon_single_lengths[] = {
	0, 1, 1, 3, 3, 4, 5, 2, 
	3, 9, 9, 9, 1, 10, 11, 1, 
	4, 1, 1, 1, 1, 9, 2, 2, 
	3, 1, 1
};

static const char _oberon_range_lengths[] = {
	0, 0, 0, 2, 2, 2, 2, 1, 
	1, 3, 3, 3, 0, 3, 3, 0, 
	1, 1, 0, 0, 0, 2, 0, 1, 
	1, 0, 0
};

static const char _oberon_index_offsets[] = {
	0, 0, 2, 4, 10, 16, 23, 31, 
	35, 40, 53, 66, 79, 81, 95, 110, 
	112, 118, 121, 123, 125, 127, 139, 142, 
	146, 151, 153
};

static const char _oberon_indicies[] = {
	2, 1, 2, 3, 5, 6, 7, 4, 
	4, 0, 5, 8, 9, 4, 4, 0, 
	5, 10, 6, 7, 4, 4, 0, 5, 
	10, 6, 11, 7, 4, 4, 0, 12, 
	14, 12, 13, 15, 15, 17, 15, 16, 
	19, 20, 20, 19, 21, 22, 20, 23, 
	24, 18, 18, 18, 12, 26, 27, 27, 
	26, 28, 29, 27, 30, 31, 25, 25, 
	25, 12, 19, 20, 20, 19, 21, 22, 
	20, 32, 33, 18, 18, 18, 12, 20, 
	12, 19, 20, 20, 19, 21, 34, 22, 
	20, 23, 24, 18, 18, 18, 12, 19, 
	20, 20, 19, 21, 22, 20, 34, 23, 
	35, 24, 18, 18, 18, 12, 36, 37, 
	39, 40, 41, 42, 39, 38, 39, 39, 
	43, 2, 1, 2, 3, 4, 44, 46, 
	36, 36, 46, 47, 48, 49, 50, 51, 
	45, 45, 37, 46, 46, 52, 53, 14, 
	53, 13, 15, 15, 17, 15, 16, 18, 
	53, 36, 54, 0
};

static const char _oberon_trans_targs[] = {
	16, 1, 16, 2, 3, 4, 5, 6, 
	5, 6, 3, 16, 21, 7, 21, 21, 
	8, 24, 9, 9, 10, 11, 12, 13, 
	14, 9, 9, 10, 11, 12, 13, 14, 
	13, 14, 9, 21, 21, 0, 16, 17, 
	18, 19, 20, 16, 16, 21, 22, 23, 
	24, 25, 15, 26, 21, 21, 21
};

static const char _oberon_trans_actions[] = {
	35, 11, 64, 11, 9, 9, 9, 9, 
	43, 43, 49, 61, 25, 0, 17, 27, 
	0, 70, 1, 0, 0, 1, 0, 1, 
	1, 73, 52, 52, 73, 52, 73, 73, 
	40, 40, 46, 37, 55, 0, 29, 7, 
	67, 67, 85, 31, 33, 58, 3, 77, 
	89, 81, 5, 5, 19, 23, 21
};

static const char _oberon_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	13, 0, 0, 0, 0, 13, 0, 0, 
	0, 0, 0
};

static const char _oberon_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 0, 0, 15, 0, 0, 
	0, 0, 0
};

static const char _oberon_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 13, 
	16, 13, 13, 13, 13, 13, 13, 0, 
	0, 44, 45, 45, 45, 0, 53, 54, 
	16, 54, 55
};

static const int oberon_start = 16;
static const int oberon_first_final = 16;
static const int oberon_error = 0;

static const int oberon_en_oberon_line = 21;
static const int oberon_en_oberon_entity = 16;


#line 113 "oberon.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Oberon code.
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
void parse_oberon(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  int nest_count = 0;

  
#line 224 "oberon.h"
	{
	cs = oberon_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 138 "oberon.rl"
  cs = (count) ? oberon_en_oberon_line : oberon_en_oberon_entity;
  
#line 235 "oberon.h"
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
	_acts = _oberon_actions + _oberon_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 14:
#line 1 "NONE"
	{ts = p;}
	break;
#line 257 "oberon.h"
		}
	}

	_widec = (*p);
	_klen = _oberon_cond_lengths[cs];
	_keys = _oberon_cond_keys + (_oberon_cond_offsets[cs]*2);
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
				switch ( _oberon_cond_spaces[_oberon_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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
#line 67 "oberon.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
	case 2: {
		_widec = (short)(1280 + ((*p) - 0));
		if ( 
#line 102 "oberon.rl"
 nest_count == 0  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _oberon_trans_keys + _oberon_key_offsets[cs];
	_trans = _oberon_index_offsets[cs];

	_klen = _oberon_single_lengths[cs];
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

	_klen = _oberon_range_lengths[cs];
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
	_trans = _oberon_indicies[_trans];
_eof_trans:
	cs = _oberon_trans_targs[_trans];

	if ( _oberon_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _oberon_actions + _oberon_trans_actions[_trans];
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
#line 33 "oberon.rl"
	{
    switch(entity) {
    case OBERON_SPACE:
      ls
      break;
    case OBERON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBERON_LANG)
      break;
    case NEWLINE:
      std_newline(OBERON_LANG)
    }
  }
	break;
	case 3:
#line 52 "oberon.rl"
	{ nest_count = 0; }
	break;
	case 4:
#line 53 "oberon.rl"
	{ nest_count++; }
	break;
	case 5:
#line 54 "oberon.rl"
	{ nest_count--; }
	break;
	case 6:
#line 58 "oberon.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 81 "oberon.rl"
	{ entity = OBERON_SPACE; }
	break;
	case 8:
#line 84 "oberon.rl"
	{ entity = NEWLINE;      }
	break;
	case 9:
#line 85 "oberon.rl"
	{ entity = OBERON_ANY;   }
	break;
	case 10:
#line 107 "oberon.rl"
	{ entity = OBERON_SPACE;   }
	break;
	case 11:
#line 108 "oberon.rl"
	{ entity = OBERON_COMMENT; }
	break;
	case 12:
#line 109 "oberon.rl"
	{ entity = OBERON_STRING;  }
	break;
	case 15:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 16:
#line 83 "oberon.rl"
	{act = 3;}
	break;
	case 17:
#line 33 "oberon.rl"
	{act = 5;}
	break;
	case 18:
#line 82 "oberon.rl"
	{te = p+1;}
	break;
	case 19:
#line 83 "oberon.rl"
	{te = p+1;}
	break;
	case 20:
#line 33 "oberon.rl"
	{te = p+1;{
    switch(entity) {
    case OBERON_SPACE:
      ls
      break;
    case OBERON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBERON_LANG)
      break;
    case NEWLINE:
      std_newline(OBERON_LANG)
    }
  }}
	break;
	case 21:
#line 33 "oberon.rl"
	{te = p+1;{
    switch(entity) {
    case OBERON_SPACE:
      ls
      break;
    case OBERON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBERON_LANG)
      break;
    case NEWLINE:
      std_newline(OBERON_LANG)
    }
  }}
	break;
	case 22:
#line 33 "oberon.rl"
	{te = p;p--;{
    switch(entity) {
    case OBERON_SPACE:
      ls
      break;
    case OBERON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBERON_LANG)
      break;
    case NEWLINE:
      std_newline(OBERON_LANG)
    }
  }}
	break;
	case 23:
#line 33 "oberon.rl"
	{te = p;p--;{
    switch(entity) {
    case OBERON_SPACE:
      ls
      break;
    case OBERON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBERON_LANG)
      break;
    case NEWLINE:
      std_newline(OBERON_LANG)
    }
  }}
	break;
	case 24:
#line 33 "oberon.rl"
	{te = p;p--;{
    switch(entity) {
    case OBERON_SPACE:
      ls
      break;
    case OBERON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBERON_LANG)
      break;
    case NEWLINE:
      std_newline(OBERON_LANG)
    }
  }}
	break;
	case 25:
#line 33 "oberon.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case OBERON_SPACE:
      ls
      break;
    case OBERON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBERON_LANG)
      break;
    case NEWLINE:
      std_newline(OBERON_LANG)
    }
  }}
	break;
	case 26:
#line 1 "NONE"
	{	switch( act ) {
	case 5:
	{{p = ((te))-1;}
    switch(entity) {
    case OBERON_SPACE:
      ls
      break;
    case OBERON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OBERON_LANG)
      break;
    case NEWLINE:
      std_newline(OBERON_LANG)
    }
  }
	break;
	default:
	{{p = ((te))-1;}}
	break;
	}
	}
	break;
	case 27:
#line 91 "oberon.rl"
	{te = p+1;{
    callback(OBERON_LANG, oberon_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 28:
#line 91 "oberon.rl"
	{te = p+1;{
    callback(OBERON_LANG, oberon_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 29:
#line 111 "oberon.rl"
	{te = p+1;}
	break;
	case 30:
#line 91 "oberon.rl"
	{te = p;p--;{
    callback(OBERON_LANG, oberon_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 31:
#line 111 "oberon.rl"
	{te = p;p--;}
	break;
	case 32:
#line 111 "oberon.rl"
	{{p = ((te))-1;}}
	break;
#line 629 "oberon.h"
		}
	}

_again:
	_acts = _oberon_actions + _oberon_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 13:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 642 "oberon.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _oberon_eof_trans[cs] > 0 ) {
		_trans = _oberon_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 140 "oberon.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(OBERON_LANG) }
}

#endif

/*****************************************************************************/
