#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simulate the Hearthstone environment.

Each episode is playing a whole game
"""

# core modules
import logging.config
import math
import pkg_resources
import random

# 3rd party modules
from gym import spaces
import cfg_load
import gym
import numpy as np


path = 'config.yaml'  # always use slash in packages
filepath = pkg_resources.resource_filename('gym_hearthstone', path)
config = cfg_load.load(filepath)
logging.config.dictConfig(config['LOGGING'])

class HearthstoneEnv(gym.Env):
    """
    Define a Hearthstone environment.

    The environment defines which actions can be taken at which point and
    when the agent receives which reward.
    """

    def __init__(self):
        self.__version__ = "0.1.0"
        logging.info("HearthstoneEnv - Version {}".format(self.__version__))

        # General variables defining the environment
        self.curr_step = -1
        self.is_banana_sold = False

        # Define what the agent can do
        
        ############################ BATTLEFIELD ######################################################################
        #                                           | OppHero  |
        # OppHand0  | OppHand1  | OppHand2  | OppHand3  | OppHand4  | OppHand5  | OppHand6  | OppHand7  | OppHand8 | OppHand9 |
        #           | OppField0 | OppField1 | OppField2 | OppField3 | OppField4 | OppField5 | OppField6 |
        #           | MyField0  | MyField1  | MyField2  | MyField3  | MyField4  | MyField5  | MyField6  |
        # MyHand0   | MyHand1   | MyHand2   | MyHand3   | MyHand4   | MyHand5   | MyHand6   | MyHand7   | MyHand8  | MyHand9  |
        #                                           | MyHero   |
        ###############################################################################################################
        # Action                                                        Relative Action Number          Cumulative Action Number
        ###############################################################################################################
        # Hero Power OppHero                                            1-1                                         1-1
        # Hero Power OppField0-6                                        1-7                                         2-8
        # Hero Power MyField0-6                                         1-7                                         9-15
        # Hero Power MyHero                                             1-1                                         16-16
        # Play MyHand0 on MyField0 and Use Action on OppHero            1-1                                         17-17
        # Play MyHand0 on MyField0 and Use Action on OppField0-6        1-7                                         18-24 
        # Play MyHand0 on MyField0 and Use Action on MyField0-6         1-7                                         25-31
        # Play MyHand0 on MyField0 and Use Action on MyHero             1-1                                         32-32
        # Play MyHand0 on MyField1 and Use Action ''                    1-16                                        33-48
        # Play MyHand0 on MyField2-6 ''                                 1-16,1-16,1-16,1-16,1-16                    49-64,65-80,81-96,97-112,113-128
        # Play MyHand1-6 on ''                                          1-112, 1-112, 1-112, 1-112, 1-112, 1-112    129-240, 241-352, 353-464, 465-576, 577-688, 689-800
        self.action_space = spaces.Discrete(800)

        # Observation is the remaining time
        low = np.array([0.0,  # remaining_tries
                        ])
        high = np.array([self.TOTAL_TIME_STEPS,  # remaining_tries
                         ])
        self.observation_space = spaces.Box(low, high, dtype=np.float32)

        # Store what the agent tried
        self.curr_episode = -1
        self.action_episode_memory = []

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
        if self.is_banana_sold:
            raise RuntimeError("Episode is done")
        self.curr_step += 1
        self._take_action(action)
        reward = self._get_reward()
        ob = self._get_state()
        return ob, reward, self.is_banana_sold, {}

    def _take_action(self, action):
        self.action_episode_memory[self.curr_episode].append(action)
        self.price = ((float(self.MAX_PRICE) /
                      (self.action_space.n - 1)) * action)

        chance_to_take = get_chance(self.price)
        banana_is_sold = (random.random() < chance_to_take)

        if banana_is_sold:
            self.is_banana_sold = True

        remaining_steps = self.TOTAL_TIME_STEPS - self.curr_step
        time_is_over = (remaining_steps <= 0)
        throw_away = time_is_over and not self.is_banana_sold
        if throw_away:
            self.is_banana_sold = True  # abuse this a bit
            self.price = 0.0

    def _get_reward(self):
        """Reward is given for a sold banana."""
        if self.is_banana_sold:
            return self.price - 1
        else:
            return 0.0

    def reset(self):
        """
        Reset the state of the environment and returns an initial observation.

        Returns
        -------
        observation (object): the initial observation of the space.
        """
        self.curr_episode += 1
        self.action_episode_memory.append([])
        self.is_banana_sold = False
        self.price = 1.00
        return self._get_state()

    def _render(self, mode='human', close=False):
        return

    def _get_state(self):
        """Get the observation."""
        ob = [self.TOTAL_TIME_STEPS - self.curr_step]
        return ob

    def seed(self, seed):
        random.seed(seed)
        np.random.seed
