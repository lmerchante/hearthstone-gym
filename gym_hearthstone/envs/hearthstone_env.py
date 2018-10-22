from enum import Enum
from fireplace import cards, exceptions, utils
from fireplace.utils import get_script_definition
from hearthstone.enums import PlayState, Step, Mulligan, State, CardClass, Race
from gym import spaces
import gym

GREEN = "\033[92m"
RED = "\033[91m"
ENDC = "\033[0m"
PREFIXES = {
	GREEN: "Implemented",
	RED: "Not implemented",
}

implemented_cards=[]

SOLVED_KEYWORDS = [
	"Windfury", "Charge", "Divine Shield", "Taunt", "Stealth", "Poisonous",
	r"Can't be targeted by spells or Hero Powers\.",
	r"Can't attack\.",
	"Destroy any minion damaged by this minion.",
	r"Your Hero Power deals \d+ extra damage.",
	r"Spell Damage \+\d+",
	r"Overload: \(\d+\)",
]

DUMMY_CARDS = (
	"PlaceholderCard",  # Placeholder Card
	"CS2_022e",  # Polymorph
	"EX1_246e",  # Hexxed
	"EX1_345t",  # Shadow of Nothing
	"GAME_006",  # NOOOOOOOOOOOO
	"LOEA04_27",  # Animated Statue
	"Mekka4e",  # Transformed
	"NEW1_025e",  # Bolstered (Unused)
	"TU4c_005",  # Hidden Gnome
	"TU4c_007",  # Mukla's Big Brother

	# Dynamic buffs set by their parent
	"CS2_236e",  # Divine Spirit
	"EX1_304e",  # Consume (Void Terror)
	"LOE_030e",  # Hollow (Unused)
	"NEW1_018e",  # Treasure Crazed (Bloodsail Raider)
)

cards.db.initialize()
for id in sorted(cards.db):
	card = cards.db[id]
	description = cleanup_description(card.description)
	implemented = False

	if not description:
		# Minions without card text or with basic abilities are implemented
		implemented = True
	elif card.card_set == CardSet.CREDITS:
		implemented = True

	if id in DUMMY_CARDS:
		implemented = True

	carddef = get_script_definition(id)
	if carddef:
		implemented = True

	color = GREEN if implemented else RED
	name = color + "%s: %s" % (PREFIXES[color], card.name) + ENDC

	if implemented:
		implemented_cards.append(card)


def cleanup_description(description):
	ret = description
	ret = re.sub("<i>.+</i>", "", ret)
	ret = re.sub("(<b>|</b>)", "", ret)
	ret = re.sub("(" + "|".join(SOLVED_KEYWORDS) + ")", "", ret)
	ret = re.sub("<[^>]*>", "", ret)
	exclude_chars = string.punctuation + string.whitespace
	ret = "".join([ch for ch in ret if ch not in exclude_chars])
	return ret


IMPLEMENTED_CARDS=len(implemented_cards)

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
# MyHand0Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1] 	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyHand1Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyHand2Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyHand3Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyHand4Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyHand5Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyHand6Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyHand7Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyHand8Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyHand9Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyField0Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyField1Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyField2Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyField3Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyField4Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyField5Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# MyField6Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# OppField0Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# OppField1Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# OppField2Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# OppField3Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# OppField4Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# OppField5Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
# OppField6Effects							[0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1,0/1]	One hot [Windfury, Charge, Divine Shield, Taunt, Stealth, Poisonous, Cant be targeted, aura, deathrattle, frozen, silenced]
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
			{"myhand0effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand1effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand2effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand3effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand4effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand5effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand6effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand7effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand8effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand9effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield0effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield1effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield2effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield3effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield4effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield5effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield6effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield0effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield1effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield2effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield3effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield4effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield5effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield6effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
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

		self.curr_episode = -1
		self.action_episode_memory = []
		self.playerJustMoved = 2 # At the root pretend the player just moved is p2 - p1 has the first move
		self.playerToMove = 1
		self.players_ordered = None
		self.hero1 = random.choice(list(CardClass))
		self.deck1 = None
		self.hero2 = random.choice(list(CardClass))
		self.deck2 = None
		self.game = None
		self.setup_game()
		self.lastMovePlayed = None
	
	def setup_game(self):
		if self.hero1 is None or self.hero2 is None or self.deck1 is None or self.deck2 is None:
			deck1 = random_draft(self.hero1)
			deck2 = random_draft(self.hero2)
			player1 = Player("Player1", deck1, self.hero1.default_hero)
			player2 = Player("Player2", deck2, self.hero2.default_hero)

			self.game = Game(players=(player1, player2))
			self.game.start()
			self.players_ordered = [self.game.player1, self.game.player2]
			self.playerJustMoved = 2  # At the root pretend the player just moved is p2 - p1 has the first move
			self.playerToMove = 1
			self.lastMovePlayed = None
	
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
        self._take_action(action)
        reward = self._get_reward()
        ob = self._get_state()
        return ob, reward, reward!=0, {}
	
	def _get_reward(self):
		""" Get the current reward, from the perspective of the player who just moved
			1 for win, -1 for loss
			0 if game is not over
		"""
		player = self.playerJustMoved
		if self.players_ordered[0].hero.health <= 0 and self.players_ordered[1].hero.health <= 0: # tie
			return 0.1
		elif self.players_ordered[player - 1].hero.health <= 0:  # loss
			return -1
		elif self.players_ordered[2 - player].hero.health <= 0:  # win
			return 1
		else:
			return 0
	
	def _get_state(self):
		game = self.game
		player = self.players_ordered[self.playerToMove - 1]
		p1 = player
		p2 = player.opponent
		s = {
			"myhero":p1.hero.card_class-1,
			"opphero":p2.hero.card_class-1,
			"myhealth":p1.hero.health,
			"opphealth":p2.hero.health,
			"myarmor":p1.hero.armor,
			"opparmor":p2.hero.armor,
			"myweaponatt":p1.weapon.damage,
			"oppweaponatt":p2.weapon.damage,
			"myweapondur":p1.weapon.durability,
			"oppweapondur":p2.weapon.durability,
			"myheropoweravail":p1.hero.power.is_usable() * 1,
			"myunusedmanacrystals":p1.mana,
			"myusedmanacrystals":p1.max_mana-p1.mana,
			"oppcrystals":p2.max_mana,
			"mynumcardsinhand":len(p1.hand),
			"oppnumcardsinhand":len(p2.hand),
			"mynumminions":len(p1.field),
			"oppnumminions":len(p2.field),
			"mynumsecrets":len(p1.secrets),
			"oppnumsecrets":len(p2.secrets),
			"myhand0":implemented_cards.index(p1.hand[0]),
			"myhand1":implemented_cards.index(p1.hand[1]),
			"myhand2":implemented_cards.index(p1.hand[2]),
			"myhand3":implemented_cards.index(p1.hand[3]),
			"myhand4":implemented_cards.index(p1.hand[4]),
			"myhand5":implemented_cards.index(p1.hand[5]),
			"myhand6":implemented_cards.index(p1.hand[6]),
			"myhand7":implemented_cards.index(p1.hand[7]),
			"myhand8":implemented_cards.index(p1.hand[8]),
			"myhand9":implemented_cards.index(p1.hand[9]),
			"myfield0":implemented_cards.index(p1.field[0]),
			"myfield1":implemented_cards.index(p1.field[1]),
			"myfield2":implemented_cards.index(p1.field[2]),
			"myfield3":implemented_cards.index(p1.field[3]),
			"myfield4":implemented_cards.index(p1.field[4]),
			"myfield5":implemented_cards.index(p1.field[5]),
			"myfield6":implemented_cards.index(p1.field[6]),
			"oppfield0":implemented_cards.index(p2.field[0]),
			"oppfield1":implemented_cards.index(p2.field[1]),
			"oppfield2":implemented_cards.index(p2.field[2]),
			"oppfield3":implemented_cards.index(p2.field[3]),
			"oppfield4":implemented_cards.index(p2.field[4]),
			"oppfield5":implemented_cards.index(p2.field[5]),
			"oppfield6":implemented_cards.index(p2.field[6]),
			"myhand0att":p1.hand[0].atk if 0<len(p1.hand) else 0,
			"myhand1att":p1.hand[1].atk if 1<len(p1.hand) else 0,
			"myhand2att":p1.hand[2].atk if 2<len(p1.hand) else 0,
			"myhand3att":p1.hand[3].atk if 3<len(p1.hand) else 0,
			"myhand4att":p1.hand[4].atk if 4<len(p1.hand) else 0,
			"myhand5att":p1.hand[5].atk if 5<len(p1.hand) else 0,
			"myhand6att":p1.hand[6].atk if 6<len(p1.hand) else 0,
			"myhand7att":p1.hand[7].atk if 7<len(p1.hand) else 0,
			"myhand8att":p1.hand[8].atk if 8<len(p1.hand) else 0,
			"myhand9att":p1.hand[9].atk if 9<len(p1.hand) else 0,
			"myfield0att":p1.field[0].atk if 0<len(p1.field) else 0,
			"myfield1att":p1.field[1].atk if 1<len(p1.field) else 0,
			"myfield2att":p1.field[2].atk if 2<len(p1.field) else 0,
			"myfield3att":p1.field[3].atk if 3<len(p1.field) else 0,
			"myfield4att":p1.field[4].atk if 4<len(p1.field) else 0,
			"myfield5att":p1.field[5].atk if 5<len(p1.field) else 0,
			"myfield6att":p1.field[6].atk if 6<len(p1.field) else 0,
			"oppfield0att":p2.field[0].atk if 0<len(p2.field) else 0,
			"oppfield1att":p2.field[0].atk if 0<len(p2.field) else 0,
			"oppfield2att":p2.field[0].atk if 0<len(p2.field) else 0,
			"oppfield3att":p2.field[0].atk if 0<len(p2.field) else 0,
			"oppfield4att":p2.field[0].atk if 0<len(p2.field) else 0,
			"oppfield5att":p2.field[0].atk if 0<len(p2.field) else 0,
			"oppfield6att":p2.field[0].atk if 0<len(p2.field) else 0,
			"myhand0def":p1.hand[0].health if 0<len(p1.hand) else 0,
			"myhand1def":p1.hand[1].health if 1<len(p1.hand) else 0,
			"myhand2def":p1.hand[2].health if 2<len(p1.hand) else 0,
			"myhand3def":p1.hand[3].health if 3<len(p1.hand) else 0,
			"myhand4def":p1.hand[4].health if 4<len(p1.hand) else 0,
			"myhand5def":p1.hand[5].health if 5<len(p1.hand) else 0,
			"myhand6def":p1.hand[6].health if 6<len(p1.hand) else 0,
			"myhand7def":p1.hand[7].health if 7<len(p1.hand) else 0,
			"myhand8def":p1.hand[8].health if 8<len(p1.hand) else 0,
			"myhand9def":p1.hand[9].health if 9<len(p1.hand) else 0,
			"myfield0def":p1.field[0].health if 0<len(p1.field) else 0,
			"myfield1def":p1.field[1].health if 1<len(p1.field) else 0,
			"myfield2def":p1.field[2].health if 2<len(p1.field) else 0,
			"myfield3def":p1.field[3].health if 3<len(p1.field) else 0,
			"myfield4def":p1.field[4].health if 4<len(p1.field) else 0,
			"myfield5def":p1.field[5].health if 5<len(p1.field) else 0,
			"myfield6def":p1.field[6].health if 6<len(p1.field) else 0,
			"oppfield0def":p2.field[0].health if 0<len(p2.field) else 0,
			"oppfield1def":p2.field[0].health if 0<len(p2.field) else 0,
			"oppfield2def":p2.field[0].health if 0<len(p2.field) else 0,
			"oppfield3def":p2.field[0].health if 0<len(p2.field) else 0,
			"oppfield4def":p2.field[0].health if 0<len(p2.field) else 0,
			"oppfield5def":p2.field[0].health if 0<len(p2.field) else 0,
			"oppfield6def":p2.field[0].health if 0<len(p2.field) else 0,
			"myhand0effects": {
				"windfury", 1 if p1.hand[0].windfury else 0,
				"divineshield", 1 if p1.hand[0].divine_shield else 0,
				"charge", 1 if p1.hand[0].charge else 0,
				"taunt", 1 if p1.hand[0].taunt else 0,
				"stealth", 1 if p1.hand[0].stealthed else 0,
				"poisonous", 1 if p1.hand[0].poisonous else 0,
				"cantbetargeted", 1 if (p1.hand[0].cant_be_targeted_by_abilities || p1.hand[0].cant_be_targeted_by_hero_powers) else 0,
				"aura", 1 if p1.hand[0].aura else 0,
				"deathrattle", 1 if p1.hand[0].has_deathrattle else 0,
				"frozen", 1 if p1.hand[0].frozen else 0,
				"silenced", 1 if p1.hand[0].silenced else 0
				}
			)},
			"myhand1effects": {
				"windfury", 1 if p1.hand[1].windfury else 0,
				"divineshield", 1 if p1.hand[1].divine_shield else 0,
				"charge", 1 if p1.hand[1].charge else 0,
				"taunt", 1 if p1.hand[1].taunt else 0,
				"stealth", 1 if p1.hand[1].stealthed else 0,
				"poisonous", 1 if p1.hand[1].poisonous else 0,
				"cantbetargeted", 1 if (p1.hand[1].cant_be_targeted_by_abilities || p1.hand[1].cant_be_targeted_by_hero_powers) else 0,
				"aura", 1 if p1.hand[1].aura else 0,
				"deathrattle", 1 if p1.hand[1].has_deathrattle else 0,
				"frozen", 1 if p1.hand[1].frozen else 0,
				"silenced", 1 if p1.hand[1].silenced else 0
				}
			)},
			{"myhand2effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand3effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand4effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand5effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand6effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand7effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand8effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myhand9effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield0effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield1effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield2effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield3effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield4effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield5effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"myfield6effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield0effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield1effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield2effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield3effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield4effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield5effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
			)},
			{"oppfield6effects":spaces.Dict(
				{"windfury",spaces.Discrete(2)},
				{"divineshield",spaces.Discrete(2)},
				{"charge",spaces.Discrete(2)},
				{"taunt",spaces.Discrete(2)},
				{"stealth",spaces.Discrete(2)},
				{"poisonous",spaces.Discrete(2)},
				{"cantbetargeted",spaces.Discrete(2)},
				{"aura",spaces.Discrete(2)},
				{"deathrattle",spaces.Discrete(2)},
				{"frozen",spaces.Discrete(2)},
				{"silenced",spaces.Discrete(2)}
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
