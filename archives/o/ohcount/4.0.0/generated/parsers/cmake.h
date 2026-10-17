
#line 1 "cmake.rl"
// cmake.rl written by James Webber, bunkerprivate@googlemail.com, based on
// shell.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net
//
// From shell, I remove single quote strings and added an @code to the end
// of a double quote string in case the terminating double string is on a line
// of its own.

/************************* Required for every parser *************************/
#ifndef RAGEL_CMAKE_PARSER
#define RAGEL_CMAKE_PARSER

#include "../parser_macros.h"

// the name of the language
const char *CMAKE_LANG = "cmake";

// the languages entities
const char *cmake_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  CMAKE_SPACE = 0, CMAKE_COMMENT, CMAKE_STRING, CMAKE_ANY
};

/*****************************************************************************/


#line 33 "cmake.h"
static const char _cmake_actions[] = {
	0, 1, 2, 1, 6, 1, 7, 1, 
	9, 1, 10, 1, 11, 1, 12, 1, 
	17, 1, 18, 1, 19, 1, 20, 1, 
	21, 1, 22, 1, 23, 1, 24, 2, 
	3, 8, 2, 5, 4, 2, 7, 15, 
	2, 8, 16, 3, 2, 1, 14, 3, 
	5, 4, 2, 4, 13, 0, 2, 8, 
	5, 5, 4, 2, 1, 14
};

static const char _cmake_cond_offsets[] = {
	0, 0, 1, 2, 2, 2, 2, 2, 
	2, 2, 3, 3, 4, 4
};

static const char _cmake_cond_lengths[] = {
	0, 1, 1, 0, 0, 0, 0, 0, 
	0, 1, 0, 1, 0, 0
};

static const short _cmake_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _cmake_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _cmake_key_offsets[] = {
	0, 0, 12, 24, 27, 28, 29, 33, 
	36, 39, 51, 53, 65, 68
};

static const short _cmake_trans_keys[] = {
	9, 10, 12, 32, 34, 92, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	34, 92, 269, 525, 0, 11, 14, 255, 
	10, 12, 13, 10, 10, 32, 35, 9, 
	13, 32, 9, 13, 10, 12, 13, 9, 
	10, 12, 32, 34, 35, 269, 525, 0, 
	8, 14, 255, 9, 32, 9, 10, 12, 
	32, 34, 92, 269, 525, 0, 11, 14, 
	255, 10, 12, 13, 10, 0
};

static const char _cmake_single_lengths[] = {
	0, 8, 8, 1, 1, 1, 2, 1, 
	1, 8, 2, 8, 1, 1
};

static const char _cmake_range_lengths[] = {
	0, 2, 2, 1, 0, 0, 1, 1, 
	1, 2, 0, 2, 1, 0
};

static const char _cmake_index_offsets[] = {
	0, 0, 11, 22, 25, 27, 29, 33, 
	36, 39, 50, 53, 64, 67
};

static const char _cmake_indicies[] = {
	2, 3, 3, 2, 4, 5, 6, 3, 
	1, 1, 0, 8, 9, 9, 8, 10, 
	11, 12, 9, 7, 7, 0, 0, 0, 
	1, 3, 0, 13, 14, 16, 17, 16, 
	15, 16, 16, 18, 19, 19, 17, 21, 
	13, 13, 21, 22, 23, 24, 25, 20, 
	20, 14, 21, 21, 26, 2, 3, 3, 
	2, 4, 5, 6, 3, 1, 1, 27, 
	28, 28, 29, 13, 30, 0
};

static const char _cmake_trans_targs[] = {
	9, 1, 1, 2, 9, 3, 4, 1, 
	1, 2, 9, 3, 4, 9, 0, 6, 
	7, 8, 6, 6, 9, 10, 11, 12, 
	5, 13, 9, 9, 9, 12, 9
};

static const char _cmake_trans_actions[] = {
	23, 1, 0, 0, 43, 0, 0, 47, 
	34, 34, 56, 34, 34, 37, 0, 25, 
	7, 9, 27, 29, 40, 3, 51, 31, 
	5, 5, 15, 21, 17, 0, 19
};

static const char _cmake_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 11, 0, 
	0, 11, 0, 0, 0, 0
};

static const char _cmake_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 13, 0, 
	0, 13, 0, 0, 0, 0
};

static const char _cmake_eof_trans[] = {
	0, 1, 1, 1, 1, 0, 0, 19, 
	20, 0, 27, 28, 29, 31
};

static const int cmake_start = 6;
static const int cmake_first_final = 6;
static const int cmake_error = 0;

static const int cmake_en_cmake_line = 9;
static const int cmake_en_cmake_entity = 6;


#line 93 "cmake.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with cmake script code.
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
void parse_cmake(char *buffer, int length, int count,
                 void (*callback) (const char *lang, const char *entity, int s,
                                   int e, void *udata),
                 void *userdata
  ) {
  init

  
#line 169 "cmake.h"
	{
	cs = cmake_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 116 "cmake.rl"
  cs = (count) ? cmake_en_cmake_line : cmake_en_cmake_entity;
  
#line 180 "cmake.h"
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
	_acts = _cmake_actions + _cmake_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = p;}
	break;
#line 202 "cmake.h"
		}
	}

	_widec = (*p);
	_klen = _cmake_cond_lengths[cs];
	_keys = _cmake_cond_keys + (_cmake_cond_offsets[cs]*2);
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
				switch ( _cmake_cond_spaces[_cmake_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _cmake_trans_keys + _cmake_key_offsets[cs];
	_trans = _cmake_index_offsets[cs];

	_klen = _cmake_single_lengths[cs];
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

	_klen = _cmake_range_lengths[cs];
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
	_trans = _cmake_indicies[_trans];
_eof_trans:
	cs = _cmake_trans_targs[_trans];

	if ( _cmake_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _cmake_actions + _cmake_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 30 "common.rl"
	{
  inqueue = 1;
  if (callback_list_head) free_queue(); // free the current queue
  callback_list_head = NULL;
  callback_list_tail = NULL;
  // set backup variables
  last_line_start = line_start;
  last_line_contains_code = line_contains_code;
  last_whole_line_comment = whole_line_comment;
}
	break;
	case 1:
#line 41 "common.rl"
	{
  if (inqueue) {
    Callback *item;
    for (item = callback_list_head; item != NULL; item = item->next)
      callback(item->lang, item->entity, item->s, item->e, item->udata);
    free_queue();
    inqueue = 0;
  }
}
	break;
	case 2:
#line 53 "common.rl"
	{
  if (!line_contains_code && !line_start) line_start = ts;
  line_contains_code = 1;
}
	break;
	case 3:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 4:
#line 36 "cmake.rl"
	{
    switch(entity) {
    case CMAKE_SPACE:
      ls
      break;
    case CMAKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CMAKE_LANG)
      break;
    case NEWLINE:
      std_newline(CMAKE_LANG)
    }
  }
	break;
	case 5:
#line 60 "cmake.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 72 "cmake.rl"
	{ entity = CMAKE_SPACE; }
	break;
	case 7:
#line 75 "cmake.rl"
	{ entity = NEWLINE;     }
	break;
	case 8:
#line 76 "cmake.rl"
	{ entity = CMAKE_ANY;   }
	break;
	case 9:
#line 88 "cmake.rl"
	{ entity = CMAKE_SPACE;   }
	break;
	case 10:
#line 89 "cmake.rl"
	{ entity = CMAKE_COMMENT; }
	break;
	case 13:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 14:
#line 74 "cmake.rl"
	{te = p+1;}
	break;
	case 15:
#line 36 "cmake.rl"
	{te = p+1;{
    switch(entity) {
    case CMAKE_SPACE:
      ls
      break;
    case CMAKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CMAKE_LANG)
      break;
    case NEWLINE:
      std_newline(CMAKE_LANG)
    }
  }}
	break;
	case 16:
#line 36 "cmake.rl"
	{te = p+1;{
    switch(entity) {
    case CMAKE_SPACE:
      ls
      break;
    case CMAKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CMAKE_LANG)
      break;
    case NEWLINE:
      std_newline(CMAKE_LANG)
    }
  }}
	break;
	case 17:
#line 36 "cmake.rl"
	{te = p;p--;{
    switch(entity) {
    case CMAKE_SPACE:
      ls
      break;
    case CMAKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CMAKE_LANG)
      break;
    case NEWLINE:
      std_newline(CMAKE_LANG)
    }
  }}
	break;
	case 18:
#line 73 "cmake.rl"
	{te = p;p--;}
	break;
	case 19:
#line 36 "cmake.rl"
	{te = p;p--;{
    switch(entity) {
    case CMAKE_SPACE:
      ls
      break;
    case CMAKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CMAKE_LANG)
      break;
    case NEWLINE:
      std_newline(CMAKE_LANG)
    }
  }}
	break;
	case 20:
#line 36 "cmake.rl"
	{te = p;p--;{
    switch(entity) {
    case CMAKE_SPACE:
      ls
      break;
    case CMAKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CMAKE_LANG)
      break;
    case NEWLINE:
      std_newline(CMAKE_LANG)
    }
  }}
	break;
	case 21:
#line 36 "cmake.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case CMAKE_SPACE:
      ls
      break;
    case CMAKE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(CMAKE_LANG)
      break;
    case NEWLINE:
      std_newline(CMAKE_LANG)
    }
  }}
	break;
	case 22:
#line 91 "cmake.rl"
	{te = p+1;}
	break;
	case 23:
#line 81 "cmake.rl"
	{te = p;p--;{
    callback(CMAKE_LANG, cmake_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 81 "cmake.rl"
	{te = p;p--;{
    callback(CMAKE_LANG, cmake_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
#line 518 "cmake.h"
		}
	}

_again:
	_acts = _cmake_actions + _cmake_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 531 "cmake.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _cmake_eof_trans[cs] > 0 ) {
		_trans = _cmake_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 118 "cmake.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(CMAKE_LANG) }
}

#endif

/*****************************************************************************/
