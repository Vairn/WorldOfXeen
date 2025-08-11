#include <ace/managers/log.h>
#include <ace/generic/main.h>
#include <ace/managers/key.h>
#include <ace/managers/state.h>
#include "game.h"

// The game-wide state manager is defined in game.c
tStateManager *g_pStateMachineGame;

void genericCreate() {
  keyCreate();

  g_pStateMachineGame = stateManagerCreate();
  // Start with the logo (or directly with gameplay for now)
  //statePush(g_pStateMachineGame, &g_sStateGame);
}

void genericDestroy() {
  stateManagerDestroy(g_pStateMachineGame);
  keyDestroy();
}

void genericProcess() {
  keyProcess();

  stateProcess(g_pStateMachineGame);
}
