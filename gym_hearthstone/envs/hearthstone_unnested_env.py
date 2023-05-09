from enum import Enum
from fireplace import cards, exceptions, utils
from fireplace.player import Player
from fireplace.game import Game
from fireplace.deck import Deck
from fireplace.utils import random_draft
from hearthstone.enums import PlayState, Step, Mulligan, State, CardClass, Race, CardSet, CardType, Zone
from gymnasium import spaces
import gymnasium as gym
import gym_hearthstone.envs.env_setup as env_setup
import random

implemented_cards = env_setup.get_implemented_cards()
setup_dict = env_setup.get_setup_dict()


class AutoNumber(Enum):
	def __new__(cls):
		value = len(cls.__members__)  # note no + 1
		obj = object.__new__(cls)
		obj._value_ = value
		return obj

class Move(AutoNumber):
    end_turn = ()
    hero_power = ()
    minion_attack = ()
    hero_attack = ()
    play_card = ()
    choice = ()

file_rewards = open('reward_step.csv', 'w')
file_rewards.write("Game" + ',' + "Step" + ',' + "Reward" + '\n')
file_rewards.close()


class HearthstoneUnnestedEnv(gym.Env):
    """
    Define a Hearthstone environment.
    The environment defines which actions can be taken at which point and
    when the agent receives which reward.
    """

    def __init__(self):
        self.__version__ = "0.2.0"
        print("HearthstoneEnv - Version {}".format(self.__version__))

        # General variables defining the environment
        self.curr_step = -1
        # We will start with an action space of types of actions
        #self.action_space = spaces.Box(0,1, (6,))
        self.action_space = spaces.Discrete(6)
        #self.action_space = spaces.Discrete(869)

        self.observation_space = env_setup.get_obs_space()
        
        # Define stats
        self.curr_episode=0
        self.wins = 0
        self.ties = 0
        self.losses = 0
        self.total_reward = 0
        self.action_episode_memory=[]
        self.alreadySelectedActions=[]
        self.setup_game()

    def reset(self):
        self.setup_game()
        return self._get_state()

    def reset_stats(self):
        self.curr_episode = 0
        self.curr_step = 0
        self.wins = 0
        self.ties = 0
        self.losses = 0
        self.total_reward = 0

    def display_stats(self):
        print("-----------STATS------------")
        print("Number of Games: " + str(self.curr_episode))
        print("Number of Wins: " + str(self.wins))
        print("Number of Losses: " + str(self.losses))
        print("Number of Ties: " + str(self.ties))
        if(self.wins + self.losses > 0):
            print("Number of Win Rate: " + str(self.wins / (self.wins + self.losses)))
        print("Total reward is: " + str(self.total_reward))
        print("----------------------------")
    
    def setup_game(self):
        heroes=list(CardClass)
        heroes.remove(CardClass.INVALID)
        heroes.remove(CardClass.DREAM)
        heroes.remove(CardClass.NEUTRAL)
        heroes.remove(CardClass.WHIZBANG)
        self.curr_step = 0
        while True:
            try:

                # To test the app we will set the Heroes p1 - Hunter, p2 - Warrior 
                #self.hero1=random.choice(heroes)
                self.hero1 = CardClass.HUNTER
                self.deck1=None
                #self.hero2=random.choice(heroes)
                self.hero2 = CardClass.WARRIOR
                self.deck2=None
                self.game=None
                self.alreadySelectedActions = []
                # se meterá por aquí siempre porque deck1 y deck2 son None, diría que el IF no tiene sentido
                if self.hero1 is None or self.hero2 is None or self.deck1 is None or self.deck2 is None: 
                    self.deck1=[]
                    self.deck2=[]

                    while len(self.deck1) < Deck.MAX_CARDS:
                        if random.random() > 0.5:
                            # Add card class
                            card = random.choice(setup_dict[self.hero1])
                        else:
                            # Add neutral card
                            card = random.choice(setup_dict[CardClass.NEUTRAL])
                        #card = random.choice(collection1)
                        if self.deck1.count(card.id) < card.max_count_in_deck:
                            self.deck1.append(card.id)

                    while len(self.deck2) < Deck.MAX_CARDS:
                        if random.random() > 0.5:
                            # Add card class
                            card = random.choice(setup_dict[self.hero2])
                        else:
                            # Add neutral card
                            card = random.choice(setup_dict[CardClass.NEUTRAL])
                        #card = random.choice(collection2)
                        if self.deck2.count(card.id) < card.max_count_in_deck:
                            self.deck2.append(card.id)


                    print(">>> Initialize PLAYER1")
                    self.player1=Player("Player1", self.deck1, self.hero1.default_hero)
                    print(">>> Initialize PLAYER2")
                    self.player2=Player("Player2", self.deck2, self.hero2.default_hero)
                    print(">>> Initialize GAME")
                    self.game=Game(players=(self.player1, self.player2))
                    self.game.start()

                    # start mulligan and set mulligan of rando bot
                    print(self.game.step)
                    self.game.mulligan_done()
                    print(self.game.step)
                    self.game.player2.choice.choose(
                        random.choice(self.game.player2.choice.cards))
                    return
            except Exception as ex:
                print("exception making decks--trying again"+str(ex))

    def step(self, action):
        """
        The agent takes a step in the environment.
        Parameters
        ----------
        action : int
        Returns
        -------
        ob, reward, episode_over, info : tuple
            ob (object) :
                an environment-specific object representing your observation of
                the environment.
            reward (float) :
                amount of reward achieved by the previous action. The scale
                varies between environments, but the goal is always to increase
                your total reward.
            episode_over (bool) :
                whether it's time to reset the environment again. Most (but not
                all) tasks are divided up into well-defined episodes, and done
                being True indicates the episode has terminated. (For example,
                perhaps the pole tipped too far, or you lost your last life.)
            info (dict) :
                 diagnostic information useful for debugging. It can sometimes
                 be useful for learning (for example, it might contain the raw
                 probabilities behind the environment's last state change).
                 However, official evaluations of your agent are not allowed to
                 use this for learning.
        """
        self.curr_step += 1
        print("------------------------")
        print(">>> Current Step {}".format(self.curr_step))
        print("------------------------")
        self._take_action(action)

        ## change episode count each time the game finishes
        if (self.game.player1.hero.health < 1 and self.game.player2.hero.health < 1):
            self.curr_episode += 1
            self.ties += 1
        elif self.game.player1.hero.health < 1:
            self.curr_episode += 1
            self.losses += 1
        elif self.game.player2.hero.health < 1:
            self.curr_episode += 1
            self.wins += 1

        reward=self._get_reward()
        self.total_reward += reward

        ## Create csv to store the reward per step
        ## Here we write the game number, the step of the game and the reward
        file_rewards = open('reward_step.csv', 'a')
        file_rewards.write(str(self.curr_episode) + ',' + str(self.curr_step) + ',' + str(reward) + '\n')
        file_rewards.close()

        ob=self._get_state()
        return ob, reward, reward != 0, {}

    def _take_action(self, action):
        possible_actions, dict_moves = self.__getMoves(); #get valid moves
        print("")
        print(">>> possible_actions {}:{}".format(len(possible_actions),possible_actions))
        print(">>> alreadySelectedActions {}:{}".format(len(self.alreadySelectedActions),self.alreadySelectedActions))
        counter=0
        for a in self.alreadySelectedActions:
            try:
                possible_actions.remove(a)
            except:
                print("The action in the selected actions is not in possible actions!!!")        
        print(">>> possible_actions {}:{}".format(len(possible_actions),possible_actions))

        # Okey tenemos que mappear la acción que llega del dqn con las acciones del env
        # Para ello, voy a ir escalando la solución 
        # Primero empezamos eligiendo una acción aleatoria
        # Después implementamos un tipo de acción y si se elige una acción no implementada elegimos una aleatoria
        agent_action = self._map_type_action(action, dict_moves, possible_actions)
        #agent_action = self._map_action(action, possible_actions)
            
        if agent_action[0] == Move.end_turn:
            print("doing end turn for AI")
            self.__doMove(agent_action)
            self.alreadySelectedActions=[]

            ## There was an error when the hero died at the begining of its turn (Fatigue)
            # We need to take this case into consideration
            # This implementation also takes into account any card that kills the oponent at the end of the turn
            if self.game.player2.hero.health > 0:
                possible_actions, dict_moves =self.__getMoves() #get the random player's actions
                print(possible_actions)
                action = random.choice(possible_actions) #pick a random one
                while action[0] != Move.end_turn: #if it's not end turn
                    print("doing single turn for rando")
                    print("Doing action: {}".format(action))
                    self.alreadySelectedActions.append(action)
                    self.__doMove(action) #do it
                    possible_actions, dict_moves =self.__getMoves() #and get the new set of actions

                    ## When rando wins or losses the while breaks
                    if(self.game.player1.hero.health <=0 or self.game.player2.hero.health <= 0):
                        break
                    print(">>> possible_actions {}:{}".format(len(possible_actions),possible_actions))
                    print(">>> alreadySelectedActions {}:{}".format(len(self.alreadySelectedActions),self.alreadySelectedActions))
                    for a in self.alreadySelectedActions:
                        try:
                            possible_actions.remove(a)
                        except:
                            print("The action in the selected actions is not in possible actions!!!")
                    action=random.choice(possible_actions) #and pick a random one
            print("")
            print("doing end turn for rando")
            print("Doing action: {}".format(action))
            # Game is not over
            if(self.game.player1.hero.health > 0 or self.game.player2.hero.health > 0):
                self.__doMove(action) #end random player's turn
            self.alreadySelectedActions=[]
        else: #otherwise we just do the single AI action and keep track so its not used again
            print("doing single action for AI"+str(agent_action))
            self.__doMove(agent_action)
            self.alreadySelectedActions.append(agent_action)

    def __doMove(self, move, exceptionTester=[]):
        """ Update a state by carrying out the given move.
            Move format is [enum, index of selected card, target index, choice]
            Returns True if game is over
            Modified version of function from Ragowit's Fireplace fork
        """
        self.lastMovePlayed = move

        current_player = self.game.current_player

        try:
            if move[0] == Move.end_turn:
                self.game.end_turn()
            elif move[0] == Move.hero_power:
                heropower = current_player.hero.power
                if move[2] is None:
                    heropower.use()
                else:
                    heropower.use(target=heropower.targets[move[2]])
            elif move[0] == Move.play_card:
                card = current_player.hand[move[1]]
                args = {'target': None, 'choose': None}
                for i, k in enumerate(args.keys()):
                    if len(move) > i + 2 and move[i+2] is not None:
                        if k == 'target':
                            args[k] = card.targets[move[i+2]]
                        elif k == 'choose':
                            args[k] = card.choose_cards[move[i+2]]
                card.play(**args)
            elif move[0] == Move.minion_attack:
                minion = current_player.field[move[1]]
                minion.attack(minion.targets[move[2]])
            elif move[0] == Move.hero_attack:
                hero = current_player.hero
                hero.attack(hero.targets[move[2]])
            elif move[0] == Move.choice:
                current_player.choice.choose(current_player.choice.cards[move[1]])
                # print("Doing Move Choice")
                # print(move[1])
                # print(current_player.choice.cards[move[1]])
        except exceptions.GameOver:
            return True
        except Exception as e:
            # print("Ran into exception: {} While executing move {} for player {}. Game State:".format(str(e), move, self.playerJustMoved))
            # self.render()
            exceptionTester.append(1) # array will eval to True

    def __getMoves(self):
        """ Get all possible moves from this state.
            Modified version of function from Ragowit's Fireplace fork
        """

        valid_moves = []
        dict_moves = {
            "choice" : [],
            "play_card" : [],
            "heropower" : [],
            "minion_attack" : [],
            "hero_attack" : [],
            "end_turn" : []
        }

        if (self.game.step == Step.MAIN_ACTION):
            self.alreadySelectedActions = []


        current_player = self.game.current_player
        if current_player.playstate != PlayState.PLAYING:
            return [], dict_moves

        # Choose card 
        ## What does this code do ?
        
        if current_player.choice is not None:
            # print(current_player.choice)
            # print(current_player.choice.cards)
            for i in range(len(current_player.choice.cards)):
                valid_moves.append([Move.choice, i])
                dict_moves["choice"].append([Move.choice, i])
            return valid_moves, dict_moves

        else:
            # Play card
            for card in current_player.hand:
                dupe = False
                for i in range(len(valid_moves)):
                    if current_player.hand[valid_moves[i][1]].id == card.id:
                        dupe = True
                        break
                if not dupe:
                    if card.is_playable():
                        if card.must_choose_one:
                            for i in range(len(card.choose_cards)):
                                if len(card.targets) > 0:
                                    for t in range(len(card.targets)):
                                        valid_moves.append(
                                            [Move.play_card, current_player.hand.index(card), t, i])
                                        dict_moves["play_card"].append(
                                            [Move.play_card, current_player.hand.index(card), t, i])
                                else:
                                    valid_moves.append(
                                        [Move.play_card, current_player.hand.index(card), None, i])
                                    dict_moves["play_card"].append(
                                        [Move.play_card, current_player.hand.index(card), None, i])
                        elif len(card.targets) > 0:
                            for t in range(len(card.targets)):
                                valid_moves.append(
                                    [Move.play_card, current_player.hand.index(card), t, None])
                                dict_moves["play_card"].append(
                                    [Move.play_card, current_player.hand.index(card), t, None])
                        else:
                            valid_moves.append(
                                [Move.play_card, current_player.hand.index(card), None, None])
                            dict_moves["play_card"].append(
                                [Move.play_card, current_player.hand.index(card), None, None])

            # Hero Power
            heropower = current_player.hero.power
            if heropower.is_usable():
                if len(heropower.targets) > 0:
                    for t in range(len(heropower.targets)):
                        valid_moves.append([Move.hero_power, None, t])
                        dict_moves["heropower"].append(
                            [Move.hero_power, None, t])
                else:
                    valid_moves.append([Move.hero_power, None, None])
                    dict_moves["heropower"].append([Move.hero_power, None, None])
            # Minion Attack
            for minion in current_player.field:
                if minion.can_attack():
                    for t in range(len(minion.targets)):
                        valid_moves.append(
                            [Move.minion_attack, current_player.field.index(minion), t])
                        dict_moves["minion_attack"].append(
                            [Move.minion_attack, current_player.field.index(minion), t])

            # Hero Attack
            hero = current_player.hero
            if hero.can_attack():
                for t in range(len(hero.targets)):
                    valid_moves.append([Move.hero_attack, None, t])
                    dict_moves["hero_attack"].append([Move.hero_attack, None, t])

            valid_moves.append([Move.end_turn])
            dict_moves["end_turn"].append([Move.end_turn])
        #print("Moves Dictionary")
        print(dict_moves)
        return valid_moves, dict_moves
    
    ## This function checks if the action-type that was chosen by the agent is possible
    # If possible   -> Does a random action of that action type
    # If not        -> Does a random action of all possible actions
    def _map_type_action(self, action, dict_moves, possible_actions):
        #print("")
        #print("using map type action fucntion")
        # action 0 -> choice
        # action 1 -> play card
        # cation 2 -> heropower
        # action 3 -> minion attack
        # action 4 -> hero attack
        # action 5 -> end turn

        if (action == 0 and dict_moves["choice"]):
            #print(">>> Trying to do choice action")
            agent_action = random.choice(dict_moves["choice"])
        elif (action == 1 and dict_moves["play_card"]):
            #print(">>> Trying to do play card action")
            agent_action = random.choice(dict_moves["play_card"])
        elif (action == 2 and dict_moves["heropower"]):
            #print(">>> Trying to do heropower action")
            agent_action = random.choice(dict_moves["heropower"])
        elif (action == 3 and dict_moves["minion_attack"]):
            #print(">>> Trying to do attack with minion action")
            agent_action = random.choice(dict_moves["minion_attack"])
        elif (action == 4 and dict_moves["hero_attack"]):
            #print(">>> Trying to do attack with hero action")
            agent_action = random.choice(dict_moves["hero_attack"])
        elif (action == 5 and dict_moves["end_turn"]):
            #print(">>> Trying to do end turn action")
            agent_action = random.choice(dict_moves["end_turn"])
        try:
            #print(agent_action)
            #print(">>> The action is possible, doing action ^^^")
            return agent_action
        except:
            #print("!!! This type of action is not possible")
            agent_action = random.choice(possible_actions)
            return agent_action
       
    

    def _get_reward(self):
        """ Get the current reward, from the perspective of the player who just moved
            1 for win, -1 for loss
            0 if game is not over
        """
        #player=self.playerJustMoved
        if self.game.player1.hero.health <= 0 and self.game.player2.hero.health <= 0:  # tie
            return 0.1
        elif self.game.player1.hero.health <= 0:  # loss
            return -1
        elif self.game.player2.hero.health <= 0:  # win
            return 1
        else:
            return 0

    def _get_state(self):
        game=self.game
        #print("")
        player=self.game.player1
        p1=player
        p2=player.opponent


        ## When a card is deleted from the the hand or field lists, the indexes change
        # I needed to save the indexes or iterate the list from end to begining
        for i in range(10):

            if( 9-i < len(p1.hand)):
                try:
                    print(implemented_cards.index(p1.hand[9-i]))
                except:
                    p1.hand[9-i].zone = Zone.GRAVEYARD
                    #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            
            # try:
            #     print(">>>>",type(p1.hand[9-i]),p1.hand[9-i], p1.hand[9-i].id)
            # except:
            #     print(">>>> Hand no ",9-i)
        for i in range(10):
            if( 9-i < len(p1.field)):
                try:
                    print(implemented_cards.index(p1.field[9-i]))
                except:
                    p1.field[9-i].zone = Zone.GRAVEYARD
                    #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            
            # try:
            #     print(">>>>", type(p1.field[9-i]), p1.field[9-i], p1.field[9-i].id)
            # except:
            #     print(">>>> Field no ", 9-i)

        ## Repeat the process for the opponent
        for i in range(10):

            if( 9-i < len(p2.hand)):
                try:
                    print(implemented_cards.index(p2.hand[9-i]))
                except:
                    p2.hand[9-i].zone = Zone.GRAVEYARD
                    #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        for i in range(10):
            if( 9-i < len(p2.field)):
                try:
                    print(implemented_cards.index(p2.field[9-i]))
                except:
                    p2.field[9-i].zone = Zone.GRAVEYARD
                    #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            
        return env_setup.get_observations(p1,p2)
        