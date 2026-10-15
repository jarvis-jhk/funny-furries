#include "input.h"
#include <string.h>
static void add_pad(FF_Input *in,int device) {
    if(!SDL_IsGameController(device)) return;
    SDL_JoystickID id=SDL_JoystickGetDeviceInstanceID(device);
    for(int i=0;i<2;++i) if(in->pads[i]&&SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(in->pads[i]))==id) return;
    for(int i=0;i<2;++i) if(!in->pads[i]) {in->pads[i]=SDL_GameControllerOpen(device);return;}
}
void ff_input_init(FF_Input *in) {
    memset(in,0,sizeof(*in));in->focused=true;
    for(int i=0;i<SDL_NumJoysticks();++i) add_pad(in,i);
}
void ff_input_close(FF_Input *in) {
    for(int i=0;i<2;++i) if(in->pads[i]) SDL_GameControllerClose(in->pads[i]);
    memset(in,0,sizeof(*in));
}
static uint8_t key_binding(SDL_Scancode key,int *player) {
    *player=0;
    switch(key) {
    case SDL_SCANCODE_F:return FF_LEFT;case SDL_SCANCODE_H:return FF_RIGHT;
    case SDL_SCANCODE_T:return FF_JUMP;case SDL_SCANCODE_Z:return FF_PUNCH;
    case SDL_SCANCODE_A:return FF_FIRE;case SDL_SCANCODE_Q:return FF_FLY;
    default:break;
    }
    *player=1;
    switch(key) {
    case SDL_SCANCODE_LEFT:return FF_LEFT;case SDL_SCANCODE_RIGHT:return FF_RIGHT;
    case SDL_SCANCODE_UP:return FF_JUMP;case SDL_SCANCODE_RCTRL:case SDL_SCANCODE_LCTRL:return FF_PUNCH;
    case SDL_SCANCODE_RSHIFT:case SDL_SCANCODE_LSHIFT:return FF_FIRE;case SDL_SCANCODE_SLASH:return FF_FLY;
    default:return 0;
    }
}
void ff_input_event(FF_Input *in,const SDL_Event *e) {
    if(e->type==SDL_CONTROLLERDEVICEADDED) add_pad(in,e->cdevice.which);
    if(e->type==SDL_CONTROLLERDEVICEREMOVED) {
        for(int i=0;i<2;++i) if(in->pads[i]&&SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(in->pads[i]))==e->cdevice.which) {
            SDL_GameControllerClose(in->pads[i]);in->pads[i]=NULL;
        }
        /* A third connected pad can now take the free seat. */
        for(int i=0;i<SDL_NumJoysticks();++i) add_pad(in,i);
    }
    if(e->type==SDL_WINDOWEVENT) {
        if(e->window.event==SDL_WINDOWEVENT_FOCUS_LOST) {in->focused=false;memset(in->keys,0,sizeof(in->keys));}
        if(e->window.event==SDL_WINDOWEVENT_FOCUS_GAINED) in->focused=true;
    }
    if(e->type==SDL_KEYDOWN||e->type==SDL_KEYUP) {
        if(e->key.repeat||!in->focused) return;
        int player;uint8_t bit=key_binding(e->key.keysym.scancode,&player);
        if(e->type==SDL_KEYDOWN) in->keys[player]|=bit;
        else in->keys[player]&=(uint8_t)~bit;
    }
}
void ff_input_read(FF_Input *in,uint8_t keys[2]) {
    memset(keys,0,2);
    if(!in->focused) return;
    for(int i=0;i<2;++i) {
        keys[i]=in->keys[i];SDL_GameController *pad=in->pads[i];
        if(!pad||!SDL_GameControllerGetAttached(pad)) continue;
        int axis=SDL_GameControllerGetAxis(pad,SDL_CONTROLLER_AXIS_LEFTX);
        if(axis< -10000||SDL_GameControllerGetButton(pad,SDL_CONTROLLER_BUTTON_DPAD_LEFT)) keys[i]|=FF_LEFT;
        if(axis>10000||SDL_GameControllerGetButton(pad,SDL_CONTROLLER_BUTTON_DPAD_RIGHT)) keys[i]|=FF_RIGHT;
        if(SDL_GameControllerGetButton(pad,SDL_CONTROLLER_BUTTON_A)) keys[i]|=FF_JUMP;
        if(SDL_GameControllerGetButton(pad,SDL_CONTROLLER_BUTTON_X)) keys[i]|=FF_PUNCH;
        if(SDL_GameControllerGetButton(pad,SDL_CONTROLLER_BUTTON_B)||SDL_GameControllerGetAxis(pad,SDL_CONTROLLER_AXIS_TRIGGERRIGHT)>10000) keys[i]|=FF_FIRE;
        if(SDL_GameControllerGetButton(pad,SDL_CONTROLLER_BUTTON_Y)||SDL_GameControllerGetAxis(pad,SDL_CONTROLLER_AXIS_TRIGGERLEFT)>10000) keys[i]|=FF_FLY;
    }
}
