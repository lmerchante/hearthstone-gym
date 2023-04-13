def _take_action(self, action):
    possible_actions = self.__getMoves()  # get valid moves

    # Map the possible actions to the action_space and check if the agent's action is 'legal'
    action_keys = map_actions(possible_actions)
    if action_keys[action] == 1:
        # then the action is possible
        # if it is not possible (bad reward)?
        do_action()


    ## Define the logic for mapping acions Ids an actual actions

    # Action End turn 1 
    if action == 1:
        # Maybe We will need to check if the player must choose smthg (i.e. when discovering a card)
        # Do End Turn
        do_smthg_def()

        
    elif action < 16:
        map_action_heropower(action)
        # check if heropower has been used


    elif action < 79:
        map_action_attack(action)

    elif action < 866:
        map_action_cards(action)

    elif action < 869:
        map_action_mulligan(action)

    counter = 0
    for a in self.alreadySelectedActions:
        possible_actions.remove(a)

    # fill the entire action space by repeating some valid moves
    while len(possible_actions) < 869:
        possible_actions.append(possible_actions[counter])
        counter = counter+1

    # if AI is ending turn - we need to register a random move for the other/random player
    if possible_actions[action] == Move.end_turn:
        print("doing end turn for AI")
        # do the AI Turn to swap game to the random player's turn
        self.__doMove(possible_actions[action])
        self.alreadySelectedActions = []
        possible_actions = self.__getMoves()  # get the random player's actions
        action = random.choice(possible_actions)  # pick a random one
        while action != Move.end_turn:  # if it's not end turn
            print("doing single turn for rando")
            self.alreadySelectedActions.append(action)
            self.__doMove(action)  # do it
            possible_actions = self.__getMoves()  # and get the new set of actions
            for a in self.alreadySelectedActions:
                possible_actions.remove(a)
            # and pick a random one
            action = random.choice(possible_actions)
        print("doing end turn for rando")
        self.__doMove(action)  # end random player's turn
        self.alreadySelectedActions = []
    else:  # otherwise we just do the single AI action and keep track so its not used again
        print("doing single action for AI"+str(possible_actions[action]))
        self.__doMove(possible_actions[action])
        self.alreadySelectedActions.append(possible_actions[action])

# If I understand how the actions are mapped in fireplace I might not need to do all this checking
# I think fireplace checks that internally
def map_action_heropower():
    do_smthg()

    # check if heropower has been used ( or if it is available)

    # check if there is mana to use it 


    # if heropower needs target
        # if targeting a minion check len of field

def map_actions(actions):
    possible_actions_keys = np.zeros(0, 869)
    counter = 0
    for a in actions:
        # Action 0 
        if a[0] == Move.end_mulligan or a[0] == Move.end_turn:
            possible_actions_keys[0] = 1

        # Actions 1 - 4
        if a[0] == Move.mulligan:
            possible_actions_keys[counter+1] = 1

    ## I think we don't have a move.choice --

    ## Move.play_card -- (index, target, i -> choose_cards ?)


    return possible_actions_keys

