#include "input.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(c) do {if(!(c)) {fprintf(stderr,"line %d: %s (%s)\n",__LINE__,#c,SDL_GetError());exit(1);} ++checks;} while(0)
static unsigned checks;
static void pump(FF_Input *input) {SDL_Event e;SDL_PumpEvents();SDL_GameControllerUpdate();while(SDL_PollEvent(&e)) ff_input_event(input,&e);}
int main(void) {
    CHECK(SDL_Init(SDL_INIT_GAMECONTROLLER|SDL_INIT_EVENTS)==0);
    FF_Input input;ff_input_init(&input);uint8_t keys[2];SDL_Event e;
    SDL_zero(e);e.type=SDL_KEYDOWN;e.key.keysym.scancode=SDL_SCANCODE_F;ff_input_event(&input,&e);
    e.key.keysym.scancode=SDL_SCANCODE_UP;ff_input_event(&input,&e);ff_input_read(&input,keys);
    CHECK(keys[0]==FF_JUMP);CHECK(keys[1]==FF_LEFT);
    SDL_zero(e);e.type=SDL_WINDOWEVENT;e.window.event=SDL_WINDOWEVENT_FOCUS_LOST;ff_input_event(&input,&e);ff_input_read(&input,keys);CHECK(!keys[0]&&!keys[1]);
    e.window.event=SDL_WINDOWEVENT_FOCUS_GAINED;ff_input_event(&input,&e);ff_input_read(&input,keys);CHECK(!keys[0]&&!keys[1]);
    SDL_VirtualJoystickDesc desc;SDL_zero(desc);desc.version=SDL_VIRTUAL_JOYSTICK_DESC_VERSION;
    desc.type=SDL_JOYSTICK_TYPE_GAMECONTROLLER;desc.naxes=SDL_CONTROLLER_AXIS_MAX;desc.nbuttons=SDL_CONTROLLER_BUTTON_MAX;
    desc.axis_mask=(1u<<SDL_CONTROLLER_AXIS_MAX)-1;desc.button_mask=(1u<<SDL_CONTROLLER_BUTTON_MAX)-1;
    int first=SDL_JoystickAttachVirtualEx(&desc);CHECK(first>=0);
    int second=SDL_JoystickAttachVirtualEx(&desc);CHECK(second>=0);pump(&input);
    CHECK(input.pads[0]&&input.pads[1]);
    SDL_Joystick *a=SDL_GameControllerGetJoystick(input.pads[0]),*b=SDL_GameControllerGetJoystick(input.pads[1]);
    CHECK(SDL_JoystickSetVirtualAxis(a,SDL_CONTROLLER_AXIS_LEFTX,-20000)==0);
    CHECK(SDL_JoystickSetVirtualButton(a,SDL_CONTROLLER_BUTTON_X,1)==0);
    CHECK(SDL_JoystickSetVirtualAxis(b,SDL_CONTROLLER_AXIS_LEFTX,20000)==0);
    CHECK(SDL_JoystickSetVirtualButton(b,SDL_CONTROLLER_BUTTON_A,1)==0);pump(&input);ff_input_read(&input,keys);
    CHECK(keys[0]==(FF_LEFT|FF_PUNCH));CHECK(keys[1]==(FF_RIGHT|FF_JUMP));
    SDL_JoystickID remaining=SDL_JoystickInstanceID(b);
    CHECK(SDL_JoystickDetachVirtual(first)==0);pump(&input);ff_input_read(&input,keys);
    CHECK(!input.pads[0]);CHECK(!keys[0]);CHECK(SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(input.pads[1]))==remaining);
    int replacement=SDL_JoystickAttachVirtualEx(&desc);CHECK(replacement>=0);pump(&input);CHECK(input.pads[0]&&input.pads[1]);
    CHECK(SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(input.pads[1]))==remaining);
    ff_input_close(&input);SDL_Quit();printf("%u input checks passed\n",checks);return 0;
}
