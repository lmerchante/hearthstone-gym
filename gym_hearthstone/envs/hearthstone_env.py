from enum import Enum
from fireplace import cards, exceptions, utils
from hearthstone.enums import PlayState, Step, Mulligan, State, CardClass, Race
from gym import spaces
import gym

IMPLEMENTED_CARDS=2795

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
# Hero Power OppHero                                            10                                          1-1
# Hero Power OppField0-6                                        1-7                                         2-8
# Hero Power MyField0-6                                         1-7                                         9-15
# Hero Power MyHero                                             10                                          16-16
# Play MyHand0 on MyField0 and Use Action on OppHero            10                                          17-17
# Play MyHand0 on MyField0 and Use Action on OppField0-6        1-7                                         18-24 
# Play MyHand0 on MyField0 and Use Action on MyField0-6         1-7                                         25-31
# Play MyHand0 on MyField0 and Use Action on MyHero             10                                          32-32
# Play MyHand0 on MyField1 and Use Action ''                    1-16                                        33-48
# Play MyHand0 on MyField2-6 ''                                 1-16,1-16,1-16,1-16,1-16                    49-64,65-80,81-96,97-112,113-128
# Play MyHand1-6 on ''                                          1-112, 1-112, 1-112, 1-112, 1-112, 1-112    129-240, 241-352, 353-464, 465-576, 577-688, 689-800
# Attack with MyField0 on OppHero								1-1											801-801
# Attack with MyField0 on OppField0-6							1-7											802-808
# Attack with MyField1 ''										1-8											809-816
# Attack with MyField2-6 ''										1-8, 1-8, 1-8, 1-8, 1-8						817-824, 825-832, 833-840, 841-848, 849-856
# Attack with MyHero ''											1-8											857-864
# Mulligan MyHand0-3											1-4											865-868
# End Turn														1-1											869-869
###############################################################################################################
# Observation                                                   Observation Space			Meaning
###############################################################################################################
# MyHero 														1-9							Druid, Hunter, Mage, Warlock, Warrior, Paladin, Shaman, Priest, Rogue
# OppHero 														1-9 						Druid, Hunter, Mage, Warlock, Warrior, Paladin, Shaman, Priest, Rogue
# MyHealth														0-30						Health Value
# OppHealth														0-30						Health Value
# MyArmor														0-500						Armor Value
# OppArmor														0-500						Armor Value
# MyWeaponAttack												0-500						How much damage weapon does
# OppWeaponAttack												0-500						How much damage weapon does
# MyWeaponDurability											0-500						How many turns I can use weapon for
# OppWeaponDurability											0-500						How many turns Opponent can use weapon for
# MyHeroPowerAvailable											0-1							Yes Available or Not Available
# MyUnusedManaCrystals											0-10						How much ''money'' I can spend still
# MyUsedManaCrystals											0-10						How much ''money'' I have already spent
# OpponentCrystals												0-10						How many crystals opponent will have next turn
# MyNumberOfCardsInHand											0-10						Number of Cards in My hand
# OppNumberOfCardsInHand										0-10						Number of Cards in Opp Hand
# MyNumberOfMinions												0-7							Number of my cards on my battlefield
# OppNumberOfMinions											0-7							Number of cards on opponent battlefield
# MyNumberOfSecrets												0-5							Trap cards basically
# OppNumberOfSecrets											0-5							Trap cards basically
# MyHand0														0-2000ish					CardId on MyHand0, 0 if empty
# MyHand1														0-2000ish					CardId on MyHand1, 0 if empty
# MyHand2														0-2000ish					CardId on MyHand2, 0 if empty
# MyHand3														0-2000ish					CardId on MyHand3, 0 if empty
# MyHand4														0-2000ish					CardId on MyHand4, 0 if empty
# MyHand5														0-2000ish					CardId on MyHand5, 0 if empty
# MyHand6														0-2000ish					CardId on MyHand6, 0 if empty
# MyHand7														0-2000ish					CardId on MyHand7, 0 if empty
# MyHand8														0-2000ish					CardId on MyHand8, 0 if empty
# MyHand9														0-2000ish					CardId on MyHand9, 0 if empty
# MyField0														0-2000ish					CardId on MyField0, 0 if empty
# MyField1														0-2000ish					CardId on MyField1, 0 if empty
# MyField2														0-2000ish					CardId on MyField2, 0 if empty
# MyField3														0-2000ish					CardId on MyField3, 0 if empty
# MyField4														0-2000ish					CardId on MyField4, 0 if empty
# MyField5														0-2000ish					CardId on MyField5, 0 if empty
# MyField6														0-2000ish					CardId on MyField6, 0 if empty
# OppField0														0-2000ish					CardId on OppField0, 0 if empty
# OppField1														0-2000ish					CardId on OppField1, 0 if empty
# OppField2														0-2000ish					CardId on OppField2, 0 if empty
# OppField3														0-2000ish					CardId on OppField3, 0 if empty
# OppField4														0-2000ish					CardId on OppField4, 0 if empty
# OppField5														0-2000ish					CardId on OppField5, 0 if empty
# OppField6														0-2000ish					CardId on OppField6, 0 if empty
# MyHand0Att													0-500  					    Attack Value on MyHand0, 0 if empty
# MyHand1Att													0-500						Attack Value on MyHand1, 0 if empty
# MyHand2Att													0-500						Attack Value on MyHand2, 0 if empty
# MyHand3Att													0-500						Attack Value on MyHand3, 0 if empty
# MyHand4Att													0-500						Attack Value on MyHand4, 0 if empty
# MyHand5Att													0-500	      				Attack Value on MyHand5, 0 if empty
# MyHand6Att													0-500						Attack Value on MyHand6, 0 if empty
# MyHand7Att													0-500						Attack Value on MyHand7, 0 if empty
# MyHand8Att													0-500						Attack Value on MyHand8, 0 if empty
# MyHand9Att													0-500						Attack Value on MyHand9, 0 if empty
# MyField0Att													0-500						Attack Value on MyField0, 0 if empty
# MyField1Att													0-500						Attack Value on MyField1, 0 if empty
# MyField2Att													0-500						Attack Value on MyField2, 0 if empty
# MyField3Att													0-500						Attack Value on MyField3, 0 if empty
# MyField4Att													0-500						Attack Value on MyField4, 0 if empty
# MyField5Att													0-500						Attack Value on MyField5, 0 if empty
# MyField6Att													0-500						Attack Value on MyField6, 0 if empty
# OppField0Att													0-500						Attack Value on OppField0, 0 if empty
# OppField1Att													0-500						Attack Value on OppField1, 0 if empty
# OppField2Att													0-500						Attack Value on OppField2, 0 if empty
# OppField3Att													0-500						Attack Value on OppField3, 0 if empty
# OppField4Att													0-500						Attack Value on OppField4, 0 if empty
# OppField5Att													0-500						Attack Value on OppField5, 0 if empty
# OppField6Att													0-500						Attack Value on OppField6, 0 if empty
# MyHand0Def													0-500  					    Defence Value on MyHand0, 0 if empty
# MyHand1Def													0-500						Defence Value on MyHand1, 0 if empty
# MyHand2Def													0-500						Defence Value on MyHand2, 0 if empty
# MyHand3Def													0-500						Defence Value on MyHand3, 0 if empty
# MyHand4Def													0-500						Defence Value on MyHand4, 0 if empty
# MyHand5Def													0-500	      				Defence Value on MyHand5, 0 if empty
# MyHand6Def													0-500						Defence Value on MyHand6, 0 if empty
# MyHand7Def													0-500						Defence Value on MyHand7, 0 if empty
# MyHand8Def													0-500						Defence Value on MyHand8, 0 if empty
# MyHand9Def													0-500						Defence Value on MyHand9, 0 if empty
# MyField0Def													0-500						Defence Value on MyField0, 0 if empty
# MyField1Def													0-500						Defence Value on MyField1, 0 if empty
# MyField2Def													0-500						Defence Value on MyField2, 0 if empty
# MyField3Def													0-500						Defence Value on MyField3, 0 if empty
# MyField4Def													0-500						Defence Value on MyField4, 0 if empty
# MyField5Def													0-500						Defence Value on MyField5, 0 if empty
# MyField6Def													0-500						Defence Value on MyField6, 0 if empty
# OppField0Def													0-500						Defence Value on OppField0, 0 if empty
# OppField1Def													0-500						Defence Value on OppField1, 0 if empty
# OppField2Def													0-500						Defence Value on OppField2, 0 if empty
# OppField3Def													0-500						Defence Value on OppField3, 0 if empty
# OppField4Def													0-500						Defence Value on OppField4, 0 if empty
# OppField5Def													0-500						Defence Value on OppField5, 0 if empty
# OppField6Def													0-500						Defence Value on OppField6, 0 if empty
# MyHand0Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1] 	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyHand1Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyHand2Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyHand3Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyHand4Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyHand5Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyHand6Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyHand7Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyHand8Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyHand9Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyField0Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyField1Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyField2Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyField3Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyField4Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyField5Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyField6Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# OppField0Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# OppField1Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# OppField2Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# OppField3Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# OppField4Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# OppField5Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# OppField6Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, destroy, your hero power deals, spell damage, overload]
# MyField0CanAttack												0-500						Has not yet attacked or has windfury and can attack
# MyField1CanAttack												0-500						Has not yet attacked or has windfury and can attack
# MyField2CanAttack												0-500						Has not yet attacked or has windfury and can attack
# MyField3CanAttack												0-500						Has not yet attacked or has windfury and can attack
# MyField4CanAttack												0-500						Has not yet attacked or has windfury and can attack
# MyField5CanAttack												0-500						Has not yet attacked or has windfury and can attack
# MyField6CanAttack												0-500						Has not yet attacked or has windfury and can attack
# MyHeroCanAttack												0-500						Hero can attack

class HearthstoneEnv(gym.Env):
    """
    Define a simple Banana environment.
    The environment defines which actions can be taken at which point and
    when the agent receives which reward.
    """

    def __init__(self):
        self.__version__ = "0.1.0"
        logging.info("HearthstoneEnv - Version {}".format(self.__version__))

        # General variables defining the environment
		self.curr_step = -1
		self.action_space = spaces.Discrete(869)
		self.observation_space = spaces.Dict(
			{"myhero":spaces.Discrete(9)},
			{"opphero":spaces.Discrete(9)},
			{"myhealth":spaces.Discrete(31)},
			{"opphealth":spaces.Discrete(31)},
			{"myarmor":spaces.Discrete(501)},
			{"opparmor":spaces.Discrete(501)},
			{"myweaponatt":spaces.Discrete(501)},
			{"oppweaponatt":spaces.Discrete(501)},
			{"myweapondur":spaces.Discrete(501)},
			{"oppweapondur":spaces.Discrete(501)},
			{"myheropoweravail":spaces.Discrete(2)},
			{"myunusedmanacrystals":spaces.Discrete(11)}
			{"myusedmanacrystals":spaces.Discrete(11)},
			{"oppcrystals":spaces.Discrete(11)},
			{"mynumcardsinhand":spaces.Discrete(11)},
			{"oppnumcardsinhand":spaces.Discrete(11)},
			{"mynumminions":spaces.Discrete(8)},
			{"oppnumminions":spaces.Discrete(8)},
			{"mynumsecrets":spaces.Discrete(6)},
			{"oppnumsecrets":spaces.Discrete(6)},
			{"myhand0":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myhand1":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myhand2":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myhand3":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myhand4":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myhand5":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myhand6":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myhand7":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myhand8":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myhand9":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myfield0":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myfield1":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myfield2":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myfield3":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myfield4":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myfield5":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myfield6":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"oppfield0":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"oppfield1":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"oppfield2":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"oppfield3":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"oppfield4":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"oppfield5":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"oppfield6":spaces.Discrete(IMPLEMENTED_CARDS+1)},
			{"myhand0att":spaces.Discrete(501)},
			{"myhand1att":spaces.Discrete(501)},
			{"myhand2att":spaces.Discrete(501)},
			{"myhand3att":spaces.Discrete(501)},
			{"myhand4att":spaces.Discrete(501)},
			{"myhand5att":spaces.Discrete(501)},
			{"myhand6att":spaces.Discrete(501)},
			{"myhand7att":spaces.Discrete(501)},
			{"myhand8att":spaces.Discrete(501)},
			{"myhand9att":spaces.Discrete(501)},
			{"myfield0att":spaces.Discrete(501)},
			{"myfield1att":spaces.Discrete(501)},
			{"myfield2att":spaces.Discrete(501)},
			{"myfield3att":spaces.Discrete(501)},
			{"myfield4att":spaces.Discrete(501)},
			{"myfield5att":spaces.Discrete(501)},
			{"myfield6att":spaces.Discrete(501)},
			{"oppfield0att":spaces.Discrete(501)},
			{"oppfield1att":spaces.Discrete(501)},
			{"oppfield2att":spaces.Discrete(501)},
			{"oppfield3att":spaces.Discrete(501)},
			{"oppfield4att":spaces.Discrete(501)},
			{"oppfield5att":spaces.Discrete(501)},
			{"oppfield6att":spaces.Discrete(501)},
			{"oppfield1att":spaces.Discrete(501)},
			{"oppfield2att":spaces.Discrete(501)},
			{"myhand0def":spaces.Discrete(501)},
			{"myhand1def":spaces.Discrete(501)},
			{"myhand2def":spaces.Discrete(501)},
			{"myhand3def":spaces.Discrete(501)},
			{"myhand4def":spaces.Discrete(501)},
			{"myhand5def":spaces.Discrete(501)},
			{"myhand6def":spaces.Discrete(501)},
			{"myhand7def":spaces.Discrete(501)},
			{"myhand8def":spaces.Discrete(501)},
			{"myhand9def":spaces.Discrete(501)},
			{"myfield0def":spaces.Discrete(501)},
			{"myfield1def":spaces.Discrete(501)},
			{"myfield2def":spaces.Discrete(501)},
			{"myfield3def":spaces.Discrete(501)},
			{"myfield4def":spaces.Discrete(501)},
			{"myfield5def":spaces.Discrete(501)},
			{"myfield6def":spaces.Discrete(501)},
			{"oppfield0def":spaces.Discrete(501)},
			{"oppfield1def":spaces.Discrete(501)},
			{"oppfield2def":spaces.Discrete(501)},
			{"oppfield3def":spaces.Discrete(501)},
			{"oppfield4def":spaces.Discrete(501)},
			{"oppfield5def":spaces.Discrete(501)},
			{"oppfield6def":spaces.Discrete(501)},
			{"oppfield1def":spaces.Discrete(501)},
			{"oppfield2def":spaces.Discrete(501)},
			{"myhand0effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myhand1effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myhand2effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myhand3effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myhand4effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myhand5effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myhand6effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myhand7effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myhand8effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myhand9effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myfield0effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myfield1effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myfield2effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myfield3effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myfield4effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myfield5effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myfield6effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"oppfield0effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"oppfield1effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"oppfield2effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"oppfield3effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"oppfield4effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"oppfield5effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"oppfield6effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"destroyanyminion",spaces.Discrete(2)},
				{"yourheropowerdeals",spaces.Discrete(2)},
				{"spelldamage",spaces.Discrete(2)},
				{"overload",spaces.Discrete(2)}
			)},
			{"myfield0canattack":spaces.Discrete(2},
			{"myfield1canattack":spaces.Discrete(2},
			{"myfield2canattack":spaces.Discrete(2},
			{"myfield3canattack":spaces.Discrete(2},
			{"myfield4canattack":spaces.Discrete(2},
			{"myfield5canattack":spaces.Discrete(2},
			{"myfield6canattack":spaces.Discrete(2},
			{"myherocanattack":spaces.Discrete(2},
		)