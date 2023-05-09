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

   # This function is in development stage
    # This action breaks down the mapping of all action into mapping actions for each type

    def _map_action(self, action, possible_actions):
        # range of action from 0 to 868
        # print("")
        #print("using map Action function")
        agent_action = random.choice(possible_actions)
        action = int(action)
        # print(action)
        # print(type(action))

        if action == 0:
            #print(">>> Action end turn was choosen by the Agent")

            if possible_actions[-1][0] == Move.end_turn:
               # print("End turn action is possible ")
                agent_action = possible_actions[-1]
        elif action < 18:
            heropower_actions = []
            for a in possible_actions:
                if (a[0] == Move.hero_power):
                    heropower_actions.append(a)
            if (heropower_actions):
                # If it is not empty then map heropower_actions
                #print("--->>> Some heroPower actions are possible")
                if (action == 1):
                    # if the heropower does not require targets the list length must be 1
                    # so we just have to check if the target value is None
                    if (heropower_actions[0][2] == None):
                        #print("--->>> Choosing no targets forheropower")
                        agent_action = heropower_actions[0]

            else:
                print("No heroPower options are possible :(")

        elif action < 88:
            #print(" The agent choose 'Attack group of actions'")
            agent_action = self._map_attack_minion(
                action, possible_actions, agent_action)

        elif action < 200:
            #print("The agent choose 'Play group of actions'")
            agent_action = self._map_play_action(
                action, possible_actions, agent_action)

        else:
            print(">>> Action is not implemented yet :(")

        return agent_action
    
# This action is in development stage
    # This action maps all possible attack minion actions
    def _map_attack_minion(self, action, possible_actions, agent_action):
        # Minion 0 Attacks
        if action < 26:
            if (len(self.game.current_player.field) > 0):
                minion0_attack_actions = []
                for a in possible_actions:
                    if (a[0] == Move.minion_attack and a[1] == 0):
                        minion0_attack_actions.append(a)
                if (minion0_attack_actions):
                    # If it is not empty then map heropower_actions
                    print("--->>> Some Minion Attack actions are possible")
                    print(minion0_attack_actions)
                    if (action == 18):
                        print("--->>> Choosing to attack Opp hero")
                        # If the opp hero can be target then it should be the first
                        # Not sure how can we handle this for other less common situations
                        agent_action = minion0_attack_actions[0]
                        print(agent_action)
                    elif (action == 19 and len(minion0_attack_actions) > 1):
                        print("Attacking oppField0")
                        if (minion0_attack_actions[0][2] == 0):
                            agent_action = minion0_attack_actions[1]
                        else:
                            agent_action = minion0_attack_actions[0]
        # Minion 1 Attacks
        elif action < 35:
            if (len(self.game.current_player.field) > 1):
                minion1_attack_actions = []
                for a in possible_actions:
                    if (a[0] == Move.minion_attack and a[1] == 1):
                        minion1_attack_actions.append(a)
                if (minion1_attack_actions):
                    # If it is not empty then map heropower_actions
                    print("--->>> Some Minion Attack actions are possible")
                    if (action == 26):
                        print("--->>> Choosing to attack Opp hero")
                        # If the opp hero can be target then it should be the first
                        # Not sure how can we handle this for other less common situations
                        agent_action = minion1_attack_actions[0]

        # Minion 2 Attacks
        elif action < 44:
            if (len(self.game.current_player.field) > 2):
                minion2_attack_actions = []
                for a in possible_actions:
                    if (a[0] == Move.minion_attack and a[1] == 2):
                        minion2_attack_actions.append(a)
                if (minion2_attack_actions):
                    # If it is not empty then map heropower_actions
                    print("--->>> Some Minion Attack actions are possible")
                    if (action == 35):
                        print("--->>> Choosing to attack Opp hero")
                        # If the opp hero can be target then it should be the first
                        # Not sure how can we handle this for other less common situations
                        agent_action = minion2_attack_actions[0]

        # Minion 3 Attacks
        elif action < 53:
            if (len(self.game.current_player.field) > 3):
                minion3_attack_actions = []
                for a in possible_actions:
                    if (a[0] == Move.minion_attack and a[1] == 3):
                        minion3_attack_actions.append(a)
                if (minion3_attack_actions):
                    # If it is not empty then map heropower_actions
                    print("--->>> Some Minion Attack actions are possible")
                    if (action == 44):
                        print("--->>> Choosing to attack Opp hero")
                        # If the opp hero can be target then it should be the first
                        # Not sure how can we handle this for other less common situations
                        agent_action = minion3_attack_actions[0]

                # Minion 4 Attacks
        elif action < 62:
            if (len(self.game.current_player.field) > 4):
                minion4_attack_actions = []
                for a in possible_actions:
                    if (a[0] == Move.minion_attack and a[1] == 4):
                        minion4_attack_actions.append(a)
                if (minion4_attack_actions):
                    # If it is not empty then map heropower_actions
                    print("--->>> Some Minion Attack actions are possible")
                    if (action == 53):
                        print("--->>> Choosing to attack Opp hero")
                        # If the opp hero can be target then it should be the first
                        # Not sure how can we handle this for other less common situations
                        agent_action = minion4_attack_actions[0]

        # Minion 5 Attacks
        elif action < 71:
            if (len(self.game.current_player.field) > 5):
                minion5_attack_actions = []
                for a in possible_actions:
                    if (a[0] == Move.minion_attack and a[1] == 5):
                        minion5_attack_actions.append(a)
                if (minion5_attack_actions):
                    # If it is not empty then map heropower_actions
                    print("--->>> Some Minion Attack actions are possible")
                    if (action == 62):
                        print("--->>> Choosing to attack Opp hero")
                        # If the opp hero can be target then it should be the first
                        # Not sure how can we handle this for other less common situations
                        agent_action = minion5_attack_actions[0]

        # Minion 5 Attacks
        elif action < 89:
            if (len(self.game.current_player.hero.can_attack())):
                hero_attack_actions = []
                for a in possible_actions:
                    if (a[0] == Move.hero_attack and a[1] == 0):
                        hero_attack_actions.append(a)
                if (hero_attack_actions):
                    # If it is not empty then map heropower_actions
                    print("--->>> Some Minion Attack actions are possible")
                    if (action == 71):
                        print("--->>> Choosing to attack Opp hero")
                        # If the opp hero can be target then it should be the first
                        # Not sure how can we handle this for other less common situations
                        agent_action = hero_attack_actions[0]

        return agent_action

    # This action is in development stage
    # This action maps all possible play card actions
    def _map_play_action(self, action, possible_actions, agent_action):
        print("Mapping play card actions")
        # To start I will implement 10 actions where the card can be plaid with no targets
        play_none_actions = []
        for a in possible_actions:
            if (a[0] == Move.play_card and a[2] == None and a[3] == None):
                play_none_actions.append(a)
        # play card 0
        if (action == 100):
            if (len(self.game.current_player.hand > 0) and play_none_actions[0][1] == 1):
                agent_action = play_none_actions[0]
        # play card 1
        elif (action == 101 and len(self.game.current_player.hand > 1)):
            for a in play_none_actions:
                if (a[1] == 1):
                    agent_action = a

        # play card 2
        elif (action == 102 and len(self.game.current_player.hand > 2)):
            for a in play_none_actions:
                if (a[1] == 2):
                    agent_action = a

        # play card 3
        elif (action == 103 and len(self.game.current_player.hand > 3)):
            for a in play_none_actions:
                if (a[1] == 3):
                    agent_action = a

        # play card 4
        elif (action == 104 and len(self.game.current_player.hand > 4)):
            for a in play_none_actions:
                if (a[1] == 4):
                    agent_action = a

        # play card 5
        elif (action == 105 and len(self.game.current_player.hand > 5)):
            for a in play_none_actions:
                if (a[1] == 5):
                    agent_action = a

        # play card 6
        elif (action == 106 and len(self.game.current_player.hand > 6)):
            for a in play_none_actions:
                if (a[1] == 6):
                    agent_action = a

        return agent_action



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

