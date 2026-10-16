#ifndef FF_INPUT_H
#define FF_INPUT_H
#include <SDL.h>
#include "game.h"
/* Seat i is pad i plus, for seats 0 and 1, one of the two keyboard layouts. */
typedef struct { SDL_GameController *pads[FF_PLAYERS]; bool focused; uint8_t keys[2]; } FF_Input;
void ff_input_init(FF_Input *in);
void ff_input_close(FF_Input *in);
void ff_input_event(FF_Input *in,const SDL_Event *e);
void ff_input_read(FF_Input *in,uint8_t keys[FF_PLAYERS]);
bool ff_input_has_pad(const FF_Input *in,int seat);
int ff_input_seat_of(const FF_Input *in,SDL_JoystickID id);
#endif
