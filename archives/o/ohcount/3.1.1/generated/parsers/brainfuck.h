
#line 1 "brainfuck.rl"
// brainfuck.rl written by Boris 'billiob' Faure billiob<att>gmail<dott>com

/************************* Required for every parser *************************/
#ifndef OHCOUNT_BRAINFUCK_PARSER_H
#define OHCOUNT_BRAINFUCK_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *BRAINFUCK_LANG = LANG_BRAINFUCK;

// the languages entities
const char *brainfuck_entities[] = {
  "space", "comment", "operator"
};

// constants associated with the entities
enum {
  BRAINFUCK_SPACE = 0, BRAINFUCK_COMMENT, BRAINFUCK_OPERATOR
};

/*****************************************************************************/


#line 28 "brainfuck.h"
static const char _brainfuck_actions[] = {
	0, 1, 1, 1, 2, 1, 8, 1, 
	9, 1, 14, 1, 15, 1, 18, 1, 
	19, 2, 2, 11, 2, 4, 13, 2, 
	5, 7, 3, 10, 7, 17, 4, 0, 
	3, 12, 4, 4, 10, 6, 16, 7
	
};

static const char _brainfuck_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 1, 1
};

static const char _brainfuck_cond_lengths[] = {
	0, 0, 0, 0, 0, 1, 0, 0
};

static const short _brainfuck_cond_keys[] = {
	13, 13, 0
};

static const char _brainfuck_cond_spaces[] = {
	0, 0
};

static const char _brainfuck_key_offsets[] = {
	0, 0, 1, 10, 10, 13, 31, 33
};

static const short _brainfuck_trans_keys[] = {
	10, 32, 60, 62, 91, 93, 9, 13, 
	43, 46, 32, 9, 13, 9, 10, 12, 
	32, 60, 62, 91, 93, 269, 525, 0, 
	8, 14, 42, 43, 46, 47, 255, 9, 
	32, 10, 0
};

static const char _brainfuck_single_lengths[] = {
	0, 1, 5, 0, 1, 10, 2, 1
};

static const char _brainfuck_range_lengths[] = {
	0, 0, 2, 0, 1, 4, 0, 0
};

static const char _brainfuck_index_offsets[] = {
	0, 0, 2, 10, 11, 14, 29, 32
};

static const char _brainfuck_indicies[] = {
	0, 1, 3, 4, 4, 4, 4, 3, 
	4, 2, 2, 3, 3, 2, 8, 0, 
	0, 8, 9, 9, 9, 9, 10, 11, 
	7, 7, 9, 7, 1, 8, 8, 12, 
	0, 13, 0
};

static const char _brainfuck_trans_targs[] = {
	5, 0, 3, 4, 3, 2, 2, 5, 
	6, 5, 1, 7, 5, 5
};

static const char _brainfuck_trans_actions[] = {
	17, 0, 26, 23, 35, 15, 13, 20, 
	1, 30, 3, 3, 9, 11
};

static const char _brainfuck_to_state_actions[] = {
	0, 0, 5, 0, 0, 5, 0, 0
};

static const char _brainfuck_from_state_actions[] = {
	0, 0, 7, 0, 0, 7, 0, 0
};

static const char _brainfuck_eof_trans[] = {
	0, 0, 0, 6, 7, 0, 13, 14
};

static const int brainfuck_start = 2;
static const int brainfuck_first_final = 2;
static const int brainfuck_error = 0;

static const int brainfuck_en_brainfuck_line = 5;
static const int brainfuck_en_brainfuck_entity = 2;


#line 74 "brainfuck.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Brainfuck code.
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
void parse_brainfuck(char *buffer, int length, int count,
             void (*callback) (const char *lang, const char *entity, int s,
                               int e, void *udata),
             void *userdata
  ) {
  init

  
#line 140 "brainfuck.h"
	{
	cs = brainfuck_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 97 "brainfuck.rl"
  cs = (count) ? brainfuck_en_brainfuck_line : brainfuck_en_brainfuck_entity;
  
#line 151 "brainfuck.h"
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
	_acts = _brainfuck_actions + _brainfuck_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 9:
#line 1 "NONE"
	{ts = p;}
	break;
#line 173 "brainfuck.h"
		}
	}

	_widec = (*p);
	_klen = _brainfuck_cond_lengths[cs];
	_keys = _brainfuck_cond_keys + (_brainfuck_cond_offsets[cs]*2);
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
				switch ( _brainfuck_cond_spaces[_brainfuck_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _brainfuck_trans_keys + _brainfuck_key_offsets[cs];
	_trans = _brainfuck_index_offsets[cs];

	_klen = _brainfuck_single_lengths[cs];
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

	_klen = _brainfuck_range_lengths[cs];
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
	_trans = _brainfuck_indicies[_trans];
_eof_trans:
	cs = _brainfuck_trans_targs[_trans];

	if ( _brainfuck_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _brainfuck_actions + _brainfuck_trans_actions[_trans];
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
#line 53 "brainfuck.rl"
	{ entity = BRAINFUCK_SPACE;    }
	break;
	case 2:
#line 54 "brainfuck.rl"
	{ entity = NEWLINE;            }
	break;
	case 3:
#line 55 "brainfuck.rl"
	{ entity = BRAINFUCK_OPERATOR; }
	break;
	case 4:
#line 56 "brainfuck.rl"
	{ entity = BRAINFUCK_COMMENT;  }
	break;
	case 5:
#line 70 "brainfuck.rl"
	{ entity = BRAINFUCK_SPACE;    }
	break;
	case 6:
#line 71 "brainfuck.rl"
	{ entity = BRAINFUCK_OPERATOR; }
	break;
	case 7:
#line 72 "brainfuck.rl"
	{ entity = BRAINFUCK_COMMENT;  }
	break;
	case 10:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 11:
#line 31 "brainfuck.rl"
	{te = p+1;{
    switch(entity) {
    case BRAINFUCK_SPACE:
      ls
      break;
    case BRAINFUCK_OPERATOR:
      code
      break;
    case BRAINFUCK_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BRAINFUCK_LANG)
      break;
    case NEWLINE:
      std_newline(BRAINFUCK_LANG)
    }
  }}
	break;
	case 12:
#line 31 "brainfuck.rl"
	{te = p+1;{
    switch(entity) {
    case BRAINFUCK_SPACE:
      ls
      break;
    case BRAINFUCK_OPERATOR:
      code
      break;
    case BRAINFUCK_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BRAINFUCK_LANG)
      break;
    case NEWLINE:
      std_newline(BRAINFUCK_LANG)
    }
  }}
	break;
	case 13:
#line 31 "brainfuck.rl"
	{te = p+1;{
    switch(entity) {
    case BRAINFUCK_SPACE:
      ls
      break;
    case BRAINFUCK_OPERATOR:
      code
      break;
    case BRAINFUCK_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BRAINFUCK_LANG)
      break;
    case NEWLINE:
      std_newline(BRAINFUCK_LANG)
    }
  }}
	break;
	case 14:
#line 31 "brainfuck.rl"
	{te = p;p--;{
    switch(entity) {
    case BRAINFUCK_SPACE:
      ls
      break;
    case BRAINFUCK_OPERATOR:
      code
      break;
    case BRAINFUCK_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BRAINFUCK_LANG)
      break;
    case NEWLINE:
      std_newline(BRAINFUCK_LANG)
    }
  }}
	break;
	case 15:
#line 31 "brainfuck.rl"
	{te = p;p--;{
    switch(entity) {
    case BRAINFUCK_SPACE:
      ls
      break;
    case BRAINFUCK_OPERATOR:
      code
      break;
    case BRAINFUCK_COMMENT:
      comment
      break;
    case INTERNAL_NL:
      std_internal_newline(BRAINFUCK_LANG)
      break;
    case NEWLINE:
      std_newline(BRAINFUCK_LANG)
    }
  }}
	break;
	case 16:
#line 61 "brainfuck.rl"
	{act = 6;}
	break;
	case 17:
#line 61 "brainfuck.rl"
	{act = 7;}
	break;
	case 18:
#line 61 "brainfuck.rl"
	{te = p;p--;{
    callback(BRAINFUCK_LANG, brainfuck_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 19:
#line 1 "NONE"
	{	switch( act ) {
	case 6:
	{{p = ((te))-1;}
    callback(BRAINFUCK_LANG, brainfuck_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	case 7:
	{{p = ((te))-1;}
    callback(BRAINFUCK_LANG, brainfuck_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	}
	}
	break;
#line 444 "brainfuck.h"
		}
	}

_again:
	_acts = _brainfuck_actions + _brainfuck_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 457 "brainfuck.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _brainfuck_eof_trans[cs] > 0 ) {
		_trans = _brainfuck_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 99 "brainfuck.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(BRAINFUCK_LANG) }
}

#endif

/*****************************************************************************/

