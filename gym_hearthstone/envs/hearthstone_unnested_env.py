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
from stable_baselines3 import DQN
from gym_hearthstone.envs.decks.classic import classic_druid, classic_hunter, classic_mage, classic_paladin, classic_priest, classic_rogue, classic_shaman, classic_warlock, classic_warrior

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



class HearthstoneUnnestedEnv(gym.Env):
    """
    Define a Hearthstone environment.
    The environment defines which actions can be taken at which point and
    when the agent receives which reward.
    """

    def __init__(
            self,
            action_type = "random",
            reward_mode = "simple",
            seed = None,
            decks = "random",
            opponent_model ="random"
                 ):
        self.__version__ = "0.2.0"
        print("HearthstoneEnv - Version {}".format(self.__version__))

        ## Arguments
        self.seed = seed
        if self.seed != None:
            print(">>> Set seed to: ", self.seed)
            random.seed(self.seed)
            
        if (action_type != "type" and action_type != "type_rd"):
            self.action_type = "random"
        else:
            self.action_type = action_type

        if (reward_mode != "penalize" and reward_mode != "incentive" and reward_mode != "complex"):
            self.reward_mode = "simple"
        else:
            self.reward_mode = reward_mode
        
        self.legal_action = 0
            
        if action_type == "random":
            self.action_space = spaces.Discrete(1)
        elif (action_type == "type" or action_type == "type_rd"):
            self.action_space = spaces.Discrete(6)

        if(decks == "classic"):
            self.decks = "classic"
        else:
            self.decks = "random"

        if opponent_model != "random":
            try:
                self.opp_model = DQN.load(opponent_model)
                self.opponent = "model"
            except FileNotFoundError:
                self.opponent = "random"
        else:
            self.opponent = "random"
        
        # store training data
        self.reward_dict = {}
        self.games_outcome = []
        self.observation_space = env_setup.get_obs_space()
        
        # Define stats
        self.tot_step = 0
        self.curr_step = -1
        self.curr_episode=0
        self.max_steps = 1000
        self.wins = 0
        self.ties = 0
        self.losses = 0
        self.total_reward = 0
        self.errors = 0
        self.action_episode_memory=[]
        self.alreadySelectedActions=[]
        self.bot_rnd_loop = False
        self.attribute_error = False
        self.setup_game()

    def reset(self):
        print("------------------------")
        print(">>> Episode {}".format(self.curr_episode))
        print("------------------------")
        # Just discovered that the variables are not reset in fireplace when you create a new game
        # We will have to reset hand, field, secrets for both players

        self.setup_game()
        return self._get_obs()

    def reset_stats(self):
        self.tot_step = 0
        self.curr_episode = 0
        self.curr_step = 0
        self.wins = 0
        self.ties = 0
        self.losses = 0
        self.total_reward = 0
        self.errors = 0

    def display_stats(self):
        print("-----------STATS------------")
        print("Number of Steps: " + str(self.tot_step))
        print("Number of Games: " + str(self.curr_episode))
        print("Number of Wins: " + str(self.wins))
        print("Number of Losses: " + str(self.losses))
        print("Number of Ties: " + str(self.ties))
        print("Number of Errors: " + str(self.errors))
        if(self.wins + self.losses > 0):
            print("Number of Win Rate: " + str(self.wins / (self.wins + self.losses)))
        print("Total reward is: " + str(self.total_reward))
        print("----------------------------")
        return self.tot_step, self.curr_episode, self.wins, self.losses, self.ties, self.errors, self.total_reward
    

    def get_classic_decks(self):
        if(self.hero1 == CardClass.MAGE):
            self.deck1 = classic_mage.get_classic_mage()
        elif self.hero1 == CardClass.HUNTER:
            self.deck1 = classic_hunter.get_classic_hunter()
        elif self.hero1 == CardClass.PALADIN:
            self.deck1 = classic_paladin.get_classic_paladin()
        elif self.hero1 == CardClass.PRIEST:
            self.deck1 = classic_priest.get_classic_priest()
        elif self.hero1 == CardClass.WARLOCK:
            self.deck1 = classic_warlock.get_classic_warlock()
        elif self.hero1 == CardClass.WARRIOR:
            self.deck1 = classic_warrior.get_classic_warrior()
        elif self.hero1 == CardClass.DRUID:
            self.deck1 = classic_druid.get_classic_druid()
        elif self.hero1 == CardClass.ROGUE:
            self.deck1 = classic_rogue.get_classic_rogue()
        elif self.hero1 == CardClass.SHAMAN:
            self.deck1 = classic_shaman.get_classic_shaman()

        if(self.hero2 == CardClass.MAGE):
            self.deck2 = classic_mage.get_classic_mage()
        elif self.hero2 == CardClass.HUNTER:
            self.deck2 = classic_hunter.get_classic_hunter()
        elif self.hero2 == CardClass.PALADIN:
            self.deck2 = classic_paladin.get_classic_paladin()
        elif self.hero2 == CardClass.PRIEST:
            self.deck2 = classic_priest.get_classic_priest()
        elif self.hero2 == CardClass.WARLOCK:
            self.deck2 = classic_warlock.get_classic_warlock()
        elif self.hero2 == CardClass.WARRIOR:
            self.deck2 = classic_warrior.get_classic_warrior()
        elif self.hero2 == CardClass.DRUID:
            self.deck2 = classic_druid.get_classic_druid()
        elif self.hero2 == CardClass.ROGUE:
            self.deck2 = classic_rogue.get_classic_rogue()
        elif self.hero2 == CardClass.SHAMAN:
            self.deck2 = classic_shaman.get_classic_shaman()

    def get_random_decks(self):

        while len(self.deck1) < Deck.MAX_CARDS:
            if random.random() > 0.5:
                # Add card class
                card = random.choice(setup_dict[self.hero1])
            else:
                # Add neutral card
                card = random.choice(setup_dict[CardClass.NEUTRAL])
            if self.deck1.count(card.id) < card.max_count_in_deck:
                self.deck1.append(card.id)

        while len(self.deck2) < Deck.MAX_CARDS:
            if random.random() > 0.5:
                # Add card class
                card = random.choice(setup_dict[self.hero2])
            else:
                # Add neutral card
                card = random.choice(setup_dict[CardClass.NEUTRAL])

            if self.deck2.count(card.id) < card.max_count_in_deck:
                self.deck2.append(card.id)


    def setup_game(self):
        """
        Set up a new Fireplace game.
        The function sets the heroes, creates the deck and starts the game in fireplace.
        At the end, it also implements essential logic for the first step of the game (Mulligan).
        """
        heroes=list(CardClass)
        heroes.remove(CardClass.INVALID)
        heroes.remove(CardClass.DREAM)
        heroes.remove(CardClass.NEUTRAL)
        heroes.remove(CardClass.WHIZBANG)
        heroes.remove(CardClass.DEATHKNIGHT)
        heroes.remove(CardClass.DEMONHUNTER)
        self.curr_step = 0
        self.bot_rnd_loop = False
        self.attribute_error = False
        self.reward_dict[self.curr_episode] = 0
        while True:
            try:

                # To test the app we will set the Heroes p1 - Hunter, p2 - Warrior 
                self.hero1=random.choice(heroes)
                self.deck1=None
                self.hero2=random.choice(heroes)
                self.deck2=None
                self.game=None
                self.alreadySelectedActions = []

                self.deck1=[]
                self.deck2=[]

                if self.decks == "classic":
                    self.get_classic_decks()
                elif self.decks == "random":
                    self.get_random_decks()

                self.player1=Player("Player1", self.deck1, self.hero1.default_hero)
                self.player2=Player("Player2", self.deck2, self.hero2.default_hero)
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
        self.tot_step += 1
        print("------------------------------------------")
        print(">>> Current Step {}, Global {}, Average {}".format(self.curr_step, self.tot_step, round(self.tot_step/(self.curr_episode+1))))
        print("------------------------------------------")

        ## If there is an error during the step logic we will reset the env.
        # Take the action of the RL agent
        try:
            self._take_action(action)
        except AttributeError as e:
            self.attribute_error = True
            data_file = open('AttributeError.txt', 'a')
            data_file.write("New Error \n")
            data_file.write("--------------------------------------------")
            data_file.write(str(e))
            data_file.write("\n")
            data_file.write("\n")
            data_file.write("\n")

        terminated = False
        reward=self._get_reward()
        self.total_reward += reward
        self.reward_dict[self.curr_episode] += reward

        ## Get new observation
        try:
            ob = self._get_obs()
        except AttributeError as e:
            self.attribute_error = True
            data_file = open('AttributeError.txt', 'a')
            data_file.write("New Error \n")
            data_file.write("--------------------------------------------")
            data_file.write(str(e))
            data_file.write("\n")
            data_file.write("\n")
            data_file.write("\n")
            # Get a random observation not to trigger an error
            ob = self.observation_space.sample()


        ## change episode count each time the game finishes
        if (self.game.player1.hero.health < 1 and self.game.player2.hero.health < 1):
            self.curr_episode += 1
            self.ties += 1
            self.games_outcome.append(0)
            terminated = True
        elif self.game.player1.hero.health < 1:
            self.curr_episode += 1
            self.losses += 1
            self.games_outcome.append(-1)
            terminated = True
        elif self.game.player2.hero.health < 1:
            self.curr_episode += 1
            self.wins += 1
            self.games_outcome.append(1)
            terminated = True

        ## Game is set to Terminated when Loops are found
        if self.curr_step > self.max_steps or self.bot_rnd_loop == True or self.attribute_error == True:
            self.curr_episode += 1
            self.errors += 1
            self.games_outcome.append(-999)
            terminated = True


        return ob, reward, terminated, {}


    def _take_action(self, action):
        """
        Define the logic to execute in fireplace the action chosen by the agent.
            * First it defines the possible actions at the current moment
            * Second maps the agent action with the fireplace action
            * Third Executes the desired action in fireplace 
        """
        possible_actions, dict_moves = self.__getMoves(); #get valid moves
        print("")
        print(">>> Before possible_actions RL agent {}:{}".format(len(possible_actions),possible_actions))
        print(">>> Already Selected Actions RL agent {}:{}".format(len(self.alreadySelectedActions),self.alreadySelectedActions))
        for a in self.alreadySelectedActions:
            try:
                possible_actions.remove(a)
            except:
                print(">>> The action in the selected actions is not in possible actions!!!")        
        print(">>> After possible_actions RL agent {}:{}".format(len(possible_actions),possible_actions))



        if self.action_type == "random":
            agent_action = random.choice(possible_actions)
            print(">>> PLAYER: RL MODE: random. SELECTED ACTION {}".format(agent_action))

        # If the action is not legal:
        # 'type' will retrieve None
        # 'type-rd' will choose a random action from possible actions
        elif (self.action_type == "type" or self.action_type == "type_rd"):
            agent_action, self.legal_action = self._map_type_action(action, dict_moves, possible_actions)
            print(">>> PLAYER: RL MODE: type or type_rd. SELECTED ACTION {} LEGAL: {}".format(agent_action, self.legal_action))
            
        # This
        if agent_action:  
            print(">>> PLAYER: RL ACTION SELECTED")
            if agent_action[0] == Move.end_turn:
                steps_rnd = 0
                print(">>> Doing end turn for RL Agent")
                self.__doMove(agent_action)
                self.alreadySelectedActions=[]

                ## There was an error when the hero (Random Agent) died at the begining of its turn (Fatigue)
                # We need to take this case into consideration
                # This implementation also takes into account any card that kills the oponent at the end of the turn
                if self.game.player2.hero.health > 0 and self.game.player1.hero.health > 0:
                    if self.opponent == "random":
                        self.random_agent_turn(steps_rnd)
                    else:
                        self.model_agent_turn()
                ##
                if (steps_rnd < 400):
                    print("")
                    print(">>> Doing end turn for random Opponent")
                    print(">>> Doing action: {}".format(action))
                    # Game is not over
                    if(self.game.player1.hero.health > 0 or self.game.player2.hero.health > 0):
                        self.__doMove(action) #end random player's turn
                    self.alreadySelectedActions=[]
                else:
                    self.bot_rnd_loop = True
            else: #otherwise we just do the single AI action and keep track so its not used again
                print(">>> Doing single action for RL Agent"+str(agent_action))
                self.__doMove(agent_action)
                self.alreadySelectedActions.append(agent_action)


    def __doMove(self, move, exceptionTester=[]):
        """
        Defines the logic to execute a possible action in fireplace.
        This function checks which type of action was selected and 
        uses fireplace to execute the actions
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
                print("PLAYER :" + str(current_player) + " HAS CHOSEN OPTION: " +str(current_player.choice.cards[move[1]]))
                current_player.choice.choose(current_player.choice.cards[move[1]])
        except exceptions.GameOver:
            return True
        except Exception as e:
            print("Ran into exception: {} While executing move {}. Game State:".format(str(e), move))
            # self.render()
            exceptionTester.append(1) # array will eval to True

    def __getMoves(self):
        """ 
        Get all possible moves from this state.
        It creates a list (valid_moves) & a dictionary (dict_moves)
            Valid Moves contains all possible actions at a given moment
            Dict Moves helps to separate this moves into different types of actions
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

        
        if current_player.choice is not None:
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
        print(">>> Moves Dictionary: ",dict_moves)
        return valid_moves, dict_moves
    
    def random_agent_turn(self, steps_rnd):
        # get the random player's actions
        possible_actions, dict_moves = self.__getMoves()
        print(">>> Possible_actions random Opponent {}:{}".format(len(possible_actions),possible_actions))
        action = random.choice(possible_actions)  # pick a random one
        print(">>> PLAYER: RandomOpponent  SELECTED ACTION {}".format(action))

        # Random agent Loop
        # Doesn't stop until it chooses end_turn action
        # OR if it gets in an infinite loop (steps > 400)
        while action[0] != Move.end_turn and steps_rnd < 200:  # if it's not end turn
            steps_rnd += 1
            print(">>> Doing single turn for random Opponent")
            print(">>> Doing action: {}".format(action))
            self.alreadySelectedActions.append(action)
            self.__doMove(action)  # do it
            possible_actions, dict_moves = self.__getMoves()  # and get the new set of actions

            # When rando wins or losses the while breaks
            if (self.game.player1.hero.health <= 0 or self.game.player2.hero.health <= 0):
                break
            print(">>> Before Possible_actions for random Opponent {}:{}".format(
                len(possible_actions), possible_actions))
            print(">>> Already Selected Actions for random Opponent {}:{}".format(
                len(self.alreadySelectedActions), self.alreadySelectedActions))
            for a in self.alreadySelectedActions:
                try:
                    possible_actions.remove(a)
                except:
                    print(
                        "The action in the selected actions is not in possible actions!!!")
            print(">>> After Possible_actions for random Opponent {}:{}".format(
                len(possible_actions), possible_actions))
            # and pick a random one
            action = random.choice(possible_actions)
            print(
                ">>> PLAYER: RandomOpponent  SELECTED ACTION {}".format(action))
        return action
    
    def model_agent_turn(self):
        # get the random player's actions
        possible_actions, dict_moves = self.__getMoves()
        print(">>> Possible_actions Agent Opponent {}:{}".format(len(possible_actions),possible_actions))
        opp_obs = self._get_opp_obs()
        action = self.opp_model.predict(opp_obs)[0]
        print(
            ">>> PLAYER: AgentOpponent  SELECTED ACTION {}".format(action))
        opp_agent_action = self._map_type_action(action, dict_moves, possible_actions)[0]
        print(
            ">>> PLAYER: AgentOpponent  MAPPED ACTION {}".format(opp_agent_action))

        while opp_agent_action == None or opp_agent_action[0] != Move.end_turn:
            
            if opp_agent_action:
                print(
                ">>> PLAYER: AgentOpponent  DOING ACTION {}".format(opp_agent_action))
                self.__doMove(opp_agent_action)

            # When the opp agent wins or losses the while breaks
            if (self.game.player1.hero.health <= 0 or self.game.player2.hero.health <= 0):
                break

            opp_obs = self._get_opp_obs()
            action = self.opp_model.predict(opp_obs)[0]
            print(
                ">>> PLAYER: AgentOpponent  SELECTED ACTION {}".format(action))
            possible_actions, dict_moves = self.__getMoves()
            
            print(">>> Possible_actions Agent Opponent {}:{}".format(len(possible_actions),possible_actions))
            opp_agent_action = self._map_type_action(action, dict_moves, possible_actions)[0]
            print(
                ">>> PLAYER: AgentOpponent  MAPPED ACTION {}".format(opp_agent_action))
        return opp_agent_action



    def _map_type_action(self, action, dict_moves, possible_actions):
        """
        Maps action with a type when the action space is set to action types.

        This function checks if the action-type that was chosen by the agent is possible
        If possible   -> Does a random action of that action type
        If not        -> Does a random action of all possible actions

        action 0 -> choice
        action 1 -> play card
        cation 2 -> heropower
        action 3 -> minion attack
        action 4 -> hero attack
        action 5 -> end turn
        """
        agent_action = None


        if (action == 0 and dict_moves["choice"]):
            agent_action = random.choice(dict_moves["choice"])
        elif (action == 1 and dict_moves["play_card"]):
            agent_action = random.choice(dict_moves["play_card"])
        elif (action == 2 and dict_moves["heropower"]):
            agent_action = random.choice(dict_moves["heropower"])
        elif (action == 3 and dict_moves["minion_attack"]):
            agent_action = random.choice(dict_moves["minion_attack"])
        elif (action == 4 and dict_moves["hero_attack"]):
            agent_action = random.choice(dict_moves["hero_attack"])
        elif (action == 5 and dict_moves["end_turn"]):
            agent_action = random.choice(dict_moves["end_turn"])
       
    
        if(agent_action):
            return agent_action, 1
        else:
            if(self.action_type == "type_rd"):
                agent_action = random.choice(possible_actions)
                return agent_action, -1
            else:
                return agent_action, -1


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
            if self.reward_mode == "complex" :
                return 0.01 * self.legal_action
            elif (self.reward_mode == "penalize" and self.legal_action == -1):
                return -0.01
            elif (self.reward_mode == "incentive" and self.legal_action == 1):
                return 0.01
            else:
                return 0

    def _get_obs(self):
        player = self.game.player1
        opponent = player.opponent
        return self._get_state(p1 = player, p2 = opponent)
    
    def _get_opp_obs(self):
        player = self.game.player1
        opponent = player.opponent
        return self._get_state(p1=opponent, p2=player)

    def _get_state(self, p1,p2):
        """ 
        This function handles unimplemented cards and retrieves a new observation
            First it checks that all cards in both hands and fields are implemented
            Second if a card is not implemented it 'deletes' the card from the game
            Third uses env_setup to get a new observation
        """

        ## When a card is deleted from the the hand or field lists, the indexes change
        # I needed to save the indexes or iterate the list from end to begining

        
        l = len(p1.hand)
        counter = 0
        for i in range(l):

            try:
                print(">>> HANDP1: ",implemented_cards.index(p1.hand[counter]),p1.hand[counter])
            except Exception as CardNotImplemented:
                print(">>> HANDP1 NOT IMPLEMENTED: ",  p1.hand[counter])
                p1.hand[counter].zone = Zone.GRAVEYARD  
                continue

            ## check if something is an enchantment
            if(p1.hand[counter].type == 6): 
                print(">>> HANDP1 DISCARDING ENCHANTMENT: ",  p1.hand[counter])
                p1.hand[counter].zone = Zone.GRAVEYARD
                continue

            counter += 1


        l = len(p1.field)
        counter = 0
        for i in range(l):

            try:
                print(">>> FIELDP1: ",implemented_cards.index(p1.field[counter]),p1.field[counter])
            except Exception as CardNotImplemented:
                print(">>> FIELDP1 NOT IMPLEMENTED: ",  p1.field[counter])
                p1.field[counter].zone = Zone.GRAVEYARD
                continue

            
            if (p1.field[counter].type == 6):
                print(">>> FIELDP1 DISCARDING ENCHANTMENT: ",  p1.field[counter])
                p1.field[counter].zone = Zone.GRAVEYARD
                continue

            counter += 1


        ## Repeat the process for the opponent
        l = len(p2.hand)
        counter = 0
        for i in range(l):

            try:
                print(">>> HANDP2: ",implemented_cards.index(p2.hand[counter]), p2.hand[counter])
            except Exception as CardNotImplemented:
                print(">>> HANDP2 NOT IMPLEMENTED: ",  p2.hand[counter])
                p2.hand[counter].zone = Zone.GRAVEYARD
                continue
            
            if (p2.hand[counter].type == 6):
                print(">>> HANDP2 DISCARDING ENCHANTMENT: ",  p2.hand[counter])
                p2.hand[counter].zone = Zone.GRAVEYARD
                continue

            counter += 1

        l = len(p2.field)
        counter = 0
        for i in range(l):

            try:
                print(">>> FIELDP2: ",implemented_cards.index(p2.field[counter]),p2.field[counter])
            except Exception as CardNotImplemented:
                print(">>> FIELDP2 NOT IMPLEMENTED: ",  p2.field[counter])
                p2.field[counter].zone = Zone.GRAVEYARD
                continue
            
            if (p2.field[counter].type == 6):
                print(">>> FIELDP2 DISCARDING ENCHANTMENT: ",  p2.field[counter])
                p2.field[counter].zone = Zone.GRAVEYARD
                continue

            counter += 1
            
        return env_setup.get_observations(p1,p2)
        