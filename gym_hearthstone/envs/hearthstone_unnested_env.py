from enum import Enum
from fireplace import cards, exceptions, utils
from fireplace.player import Player
from fireplace.game import Game
from fireplace.deck import Deck
from fireplace.utils import get_script_definition, random_draft
from hearthstone.enums import PlayState, Step, Mulligan, State, CardClass, Race, CardSet, CardType
from gymnasium import spaces
import gymnasium as gym
import re
import string
import random

GREEN = "\033[92m"
RED = "\033[91m"
ENDC = "\033[0m"
PREFIXES = {
    GREEN: "Implemented",
    RED: "Not implemented",
}

implemented_cards = []
unimplemented_cards = []

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

# ============================================
# Limpieza de la descripción de algunas cartas
# ============================================
cards.db.initialize()
for id in sorted(cards.db):
    card = cards.db[id]
    ret = card.description
    # ret = re.sub("<i>.+</i>", "", ret)  # elimina texto en cursiva había algunas etiquetas con </I>
    ret = re.sub("<i>.+</i>", "", ret,flags=re.IGNORECASE)
    # ret = re.sub("(<b>|</b>)", "", ret) #elimina texto en negrita, cuando aparecían 2 secuencias en negrita no eliminaba todas
    ret = re.sub(r"<\/?b[^>]*>", "", ret)
    ret = re.sub("(" + "|".join(SOLVED_KEYWORDS) + ")", "", ret)  #elimina todas las palabras de SOLVED_KEYWORDS
    ret = re.sub("<[^>]*>", "", ret) #elimina otras etiquetas HTML, pero despues de corregir lo anterior, no aparecen más

    """
    La mayoría de las cartas no traen una descripción, pero hay algunas que sí. Este código
    Eliminar algunas etiquetas HTML de la descripción como:
       - <b>Secret:</b> When a friendly minion dies, summon a random minion with the same Cost.
       - Secret: When a friendly minion dies, summon a random minion with the same Cost.
    Elimina las cursivas:
       - Add 2 random cards to your hand <i>(from your opponent's class)</i>.
       - Add 2 random cards to your hand .
    Algunas keywords:
        - Transform a minion into a 4/2 Boar with <b>Charge</b>.
        - Transform a minion into a 4/2 Boar with .
        - <b>Inspire:</b> Gain <b>Spell Damage +1</b>.
        - Inspire: Gain .
    Algunas el resto de etiquetas HTML:
        - Start of Game: Give your party +4 Nature and Shadow Damage<b/>. Give your Horde characters +8/+8.
        - Start of Game: Give your party +4 Nature and Shadow Damage. Give your Horde characters +8/+8.
    
    """
    exclude_chars = string.punctuation + string.whitespace
    ret = "".join([ch for ch in ret if ch not in exclude_chars])
    description = ret
    implemented = False

    if not description:
        # Minions without card text or with basic abilities are implemented
        implemented = True
    elif card.card_set == CardSet.CREDITS:
        implemented = True

    if id in DUMMY_CARDS:
        implemented = True

    carddef = get_script_definition(id) # Mira si la carta tiene un script definition
                                        # https://github.com/jleclanche/fireplace/blob/58c5c60dc4502956d1a7a12c616c9b6201598edb/fireplace/utils.py#L103

    if carddef:
        implemented = True

    color = GREEN if implemented else RED
    name = color + "%s: %s" % (PREFIXES[color], card.name) + ENDC

    if implemented:
        implemented_cards.append(card.id)
    else:
        unimplemented_cards.append(card.id)

IMPLEMENTED_CARDS = len(implemented_cards)
UNIMPLEMENTED_CARDS = len(unimplemented_cards)

print("IMPLEMENTED CARDS: "+str(IMPLEMENTED_CARDS))
print("UNIMPLEMENTED CARDS: "+str(UNIMPLEMENTED_CARDS))


class AutoNumber(Enum):
	def __new__(cls):
		value = len(cls.__members__)  # note no + 1
		obj = object.__new__(cls)
		obj._value_ = value
		return obj

class Move(AutoNumber):
    end_turn = ()
    end_mulligan = ()
    hero_power = ()
    minion_attack = ()
    hero_attack = ()
    play_card = ()
    mulligan = ()
    choice = ()

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
        self.action_space = spaces.Discrete(869)
        self.observation_space = spaces.Dict({
            "myhero": spaces.Discrete(9),
            "opphero": spaces.Discrete(9),
            "myhealth": spaces.Discrete(31),
            "opphealth": spaces.Discrete(31),
            "myarmor": spaces.Discrete(501),
            "opparmor": spaces.Discrete(501),
            "myweaponatt": spaces.Discrete(501),
            "oppweaponatt": spaces.Discrete(501),
            "myweapondur": spaces.Discrete(501),
            "oppweapondur": spaces.Discrete(501),
            "myheropoweravail": spaces.Discrete(2),
            "myunusedmanacrystals": spaces.Discrete(11),
            "myusedmanacrystals": spaces.Discrete(11),
            "oppcrystals": spaces.Discrete(11),
            "mynumcardsinhand": spaces.Discrete(11),
            "oppnumcardsinhand": spaces.Discrete(11),
            "mynumminions": spaces.Discrete(8),
            "oppnumminions": spaces.Discrete(8),
            "mynumsecrets": spaces.Discrete(6),
            "oppnumsecrets": spaces.Discrete(6),
            "myhand0": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myhand1": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myhand2": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myhand3": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myhand4": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myhand5": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myhand6": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myhand7": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myhand8": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myhand9": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myfield0": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myfield1": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myfield2": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myfield3": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myfield4": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myfield5": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myfield6": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "oppfield0": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "oppfield1": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "oppfield2": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "oppfield3": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "oppfield4": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "oppfield5": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "oppfield6": spaces.Discrete(IMPLEMENTED_CARDS+1),
            "myhand0att": spaces.Discrete(501),
            "myhand1att": spaces.Discrete(501),
            "myhand2att": spaces.Discrete(501),
            "myhand3att": spaces.Discrete(501),
            "myhand4att": spaces.Discrete(501),
            "myhand5att": spaces.Discrete(501),
            "myhand6att": spaces.Discrete(501),
            "myhand7att": spaces.Discrete(501),
            "myhand8att": spaces.Discrete(501),
            "myhand9att": spaces.Discrete(501),
            "myfield0att": spaces.Discrete(501),
            "myfield1att": spaces.Discrete(501),
            "myfield2att": spaces.Discrete(501),
            "myfield3att": spaces.Discrete(501),
            "myfield4att": spaces.Discrete(501),
            "myfield5att": spaces.Discrete(501),
            "myfield6att": spaces.Discrete(501),
            "oppfield0att": spaces.Discrete(501),
            "oppfield1att": spaces.Discrete(501),
            "oppfield2att": spaces.Discrete(501),
            "oppfield3att": spaces.Discrete(501),
            "oppfield4att": spaces.Discrete(501),
            "oppfield5att": spaces.Discrete(501),
            "oppfield6att": spaces.Discrete(501),
            "myhand0def": spaces.Discrete(501),
            "myhand1def": spaces.Discrete(501),
            "myhand2def": spaces.Discrete(501),
            "myhand3def": spaces.Discrete(501),
            "myhand4def": spaces.Discrete(501),
            "myhand5def": spaces.Discrete(501),
            "myhand6def": spaces.Discrete(501),
            "myhand7def": spaces.Discrete(501),
            "myhand8def": spaces.Discrete(501),
            "myhand9def": spaces.Discrete(501),
            "myfield0def": spaces.Discrete(501),
            "myfield1def": spaces.Discrete(501),
            "myfield2def": spaces.Discrete(501),
            "myfield3def": spaces.Discrete(501),
            "myfield4def": spaces.Discrete(501),
            "myfield5def": spaces.Discrete(501),
            "myfield6def": spaces.Discrete(501),
            "oppfield0def": spaces.Discrete(501),
            "oppfield1def": spaces.Discrete(501),
            "oppfield2def": spaces.Discrete(501),
            "oppfield3def": spaces.Discrete(501),
            "oppfield4def": spaces.Discrete(501),
            "oppfield5def": spaces.Discrete(501),
            "oppfield6def": spaces.Discrete(501),
            "myhand0effects_aura": spaces.Discrete(2),
            "myhand0effects_cantbetargeted": spaces.Discrete(2),
            "myhand0effects_charge": spaces.Discrete(2),
            "myhand0effects_deathrattle": spaces.Discrete(2),
            "myhand0effects_divineshield": spaces.Discrete(2),
            "myhand0effects_frozen": spaces.Discrete(2),
            "myhand0effects_poisonous": spaces.Discrete(2),
            "myhand0effects_silenced": spaces.Discrete(2),
            "myhand0effects_stealth": spaces.Discrete(2),
            "myhand0effects_taunt": spaces.Discrete(2),
            "myhand0effects_windfury": spaces.Discrete(2),
            "myhand1effects_aura": spaces.Discrete(2),
            "myhand1effects_cantbetargeted": spaces.Discrete(2),
            "myhand1effects_charge": spaces.Discrete(2),
            "myhand1effects_deathrattle": spaces.Discrete(2),
            "myhand1effects_divineshield": spaces.Discrete(2),
            "myhand1effects_frozen": spaces.Discrete(2),
            "myhand1effects_poisonous": spaces.Discrete(2),
            "myhand1effects_silenced": spaces.Discrete(2),
            "myhand1effects_stealth": spaces.Discrete(2),
            "myhand1effects_taunt": spaces.Discrete(2),
            "myhand1effects_windfury": spaces.Discrete(2),
            "myhand2effects_aura": spaces.Discrete(2),
            "myhand2effects_cantbetargeted": spaces.Discrete(2),
            "myhand2effects_charge": spaces.Discrete(2),
            "myhand2effects_deathrattle": spaces.Discrete(2),
            "myhand2effects_divineshield": spaces.Discrete(2),
            "myhand2effects_frozen": spaces.Discrete(2),
            "myhand2effects_poisonous": spaces.Discrete(2),
            "myhand2effects_silenced": spaces.Discrete(2),
            "myhand2effects_stealth": spaces.Discrete(2),
            "myhand2effects_taunt": spaces.Discrete(2),
            "myhand2effects_windfury": spaces.Discrete(2),
            "myhand3effects_aura": spaces.Discrete(2),
            "myhand3effects_cantbetargeted": spaces.Discrete(2),
            "myhand3effects_charge": spaces.Discrete(2),
            "myhand3effects_deathrattle": spaces.Discrete(2),
            "myhand3effects_divineshield": spaces.Discrete(2),
            "myhand3effects_frozen": spaces.Discrete(2),
            "myhand3effects_poisonous": spaces.Discrete(2),
            "myhand3effects_silenced": spaces.Discrete(2),
            "myhand3effects_stealth": spaces.Discrete(2),
            "myhand3effects_taunt": spaces.Discrete(2),
            "myhand3effects_windfury": spaces.Discrete(2),
            "myhand4effects_aura": spaces.Discrete(2),
            "myhand4effects_cantbetargeted": spaces.Discrete(2),
            "myhand4effects_charge": spaces.Discrete(2),
            "myhand4effects_deathrattle": spaces.Discrete(2),
            "myhand4effects_divineshield": spaces.Discrete(2),
            "myhand4effects_frozen": spaces.Discrete(2),
            "myhand4effects_poisonous": spaces.Discrete(2),
            "myhand4effects_silenced": spaces.Discrete(2),
            "myhand4effects_stealth": spaces.Discrete(2),
            "myhand4effects_taunt": spaces.Discrete(2),
            "myhand4effects_windfury": spaces.Discrete(2),
            "myhand5effects_aura": spaces.Discrete(2),
            "myhand5effects_cantbetargeted": spaces.Discrete(2),
            "myhand5effects_charge": spaces.Discrete(2),
            "myhand5effects_deathrattle": spaces.Discrete(2),
            "myhand5effects_divineshield": spaces.Discrete(2),
            "myhand5effects_frozen": spaces.Discrete(2),
            "myhand5effects_poisonous": spaces.Discrete(2),
            "myhand5effects_silenced": spaces.Discrete(2),
            "myhand5effects_stealth": spaces.Discrete(2),
            "myhand5effects_taunt": spaces.Discrete(2),
            "myhand5effects_windfury": spaces.Discrete(2),
            "myhand6effects_aura": spaces.Discrete(2),
            "myhand6effects_cantbetargeted": spaces.Discrete(2),
            "myhand6effects_charge": spaces.Discrete(2),
            "myhand6effects_deathrattle": spaces.Discrete(2),
            "myhand6effects_divineshield": spaces.Discrete(2),
            "myhand6effects_frozen": spaces.Discrete(2),
            "myhand6effects_poisonous": spaces.Discrete(2),
            "myhand6effects_silenced": spaces.Discrete(2),
            "myhand6effects_stealth": spaces.Discrete(2),
            "myhand6effects_taunt": spaces.Discrete(2),
            "myhand6effects_windfury": spaces.Discrete(2),
            "myhand7effects_aura": spaces.Discrete(2),
            "myhand7effects_cantbetargeted": spaces.Discrete(2),
            "myhand7effects_charge": spaces.Discrete(2),
            "myhand7effects_deathrattle": spaces.Discrete(2),
            "myhand7effects_divineshield": spaces.Discrete(2),
            "myhand7effects_frozen": spaces.Discrete(2),
            "myhand7effects_poisonous": spaces.Discrete(2),
            "myhand7effects_silenced": spaces.Discrete(2),
            "myhand7effects_stealth": spaces.Discrete(2),
            "myhand7effects_taunt": spaces.Discrete(2),
            "myhand7effects_windfury": spaces.Discrete(2),
            "myhand8effects_aura": spaces.Discrete(2),
            "myhand8effects_cantbetargeted": spaces.Discrete(2),
            "myhand8effects_charge": spaces.Discrete(2),
            "myhand8effects_deathrattle": spaces.Discrete(2),
            "myhand8effects_divineshield": spaces.Discrete(2),
            "myhand8effects_frozen": spaces.Discrete(2),
            "myhand8effects_poisonous": spaces.Discrete(2),
            "myhand8effects_silenced": spaces.Discrete(2),
            "myhand8effects_stealth": spaces.Discrete(2),
            "myhand8effects_taunt": spaces.Discrete(2),
            "myhand8effects_windfury": spaces.Discrete(2),
            "myhand9effects_aura": spaces.Discrete(2),
            "myhand9effects_cantbetargeted": spaces.Discrete(2),
            "myhand9effects_charge": spaces.Discrete(2),
            "myhand9effects_deathrattle": spaces.Discrete(2),
            "myhand9effects_divineshield": spaces.Discrete(2),
            "myhand9effects_frozen": spaces.Discrete(2),
            "myhand9effects_poisonous": spaces.Discrete(2),
            "myhand9effects_silenced": spaces.Discrete(2),
            "myhand9effects_stealth": spaces.Discrete(2),
            "myhand9effects_taunt": spaces.Discrete(2),
            "myhand9effects_windfury": spaces.Discrete(2),
            "myfield0effects_aura": spaces.Discrete(2),
            "myfield0effects_cantbetargeted": spaces.Discrete(2),
            "myfield0effects_charge": spaces.Discrete(2),
            "myfield0effects_deathrattle": spaces.Discrete(2),
            "myfield0effects_divineshield": spaces.Discrete(2),
            "myfield0effects_frozen": spaces.Discrete(2),
            "myfield0effects_poisonous": spaces.Discrete(2),
            "myfield0effects_silenced": spaces.Discrete(2),
            "myfield0effects_stealth": spaces.Discrete(2),
            "myfield0effects_taunt": spaces.Discrete(2),
            "myfield0effects_windfury": spaces.Discrete(2),
            "myfield1effects_aura": spaces.Discrete(2),
            "myfield1effects_cantbetargeted": spaces.Discrete(2),
            "myfield1effects_charge": spaces.Discrete(2),
            "myfield1effects_deathrattle": spaces.Discrete(2),
            "myfield1effects_divineshield": spaces.Discrete(2),
            "myfield1effects_frozen": spaces.Discrete(2),
            "myfield1effects_poisonous": spaces.Discrete(2),
            "myfield1effects_silenced": spaces.Discrete(2),
            "myfield1effects_stealth": spaces.Discrete(2),
            "myfield1effects_taunt": spaces.Discrete(2),
            "myfield1effects_windfury": spaces.Discrete(2),
            "myfield2effects_aura": spaces.Discrete(2),
            "myfield2effects_cantbetargeted": spaces.Discrete(2),
            "myfield2effects_charge": spaces.Discrete(2),
            "myfield2effects_deathrattle": spaces.Discrete(2),
            "myfield2effects_divineshield": spaces.Discrete(2),
            "myfield2effects_frozen": spaces.Discrete(2),
            "myfield2effects_poisonous": spaces.Discrete(2),
            "myfield2effects_silenced": spaces.Discrete(2),
            "myfield2effects_stealth": spaces.Discrete(2),
            "myfield2effects_taunt": spaces.Discrete(2),
            "myfield2effects_windfury": spaces.Discrete(2),
            "myfield3effects_aura": spaces.Discrete(2),
            "myfield3effects_cantbetargeted": spaces.Discrete(2),
            "myfield3effects_charge": spaces.Discrete(2),
            "myfield3effects_deathrattle": spaces.Discrete(2),
            "myfield3effects_divineshield": spaces.Discrete(2),
            "myfield3effects_frozen": spaces.Discrete(2),
            "myfield3effects_poisonous": spaces.Discrete(2),
            "myfield3effects_silenced": spaces.Discrete(2),
            "myfield3effects_stealth": spaces.Discrete(2),
            "myfield3effects_taunt": spaces.Discrete(2),
            "myfield3effects_windfury": spaces.Discrete(2),
            "myfield4effects_aura": spaces.Discrete(2),
            "myfield4effects_cantbetargeted": spaces.Discrete(2),
            "myfield4effects_charge": spaces.Discrete(2),
            "myfield4effects_deathrattle": spaces.Discrete(2),
            "myfield4effects_divineshield": spaces.Discrete(2),
            "myfield4effects_frozen": spaces.Discrete(2),
            "myfield4effects_poisonous": spaces.Discrete(2),
            "myfield4effects_silenced": spaces.Discrete(2),
            "myfield4effects_stealth": spaces.Discrete(2),
            "myfield4effects_taunt": spaces.Discrete(2),
            "myfield4effects_windfury": spaces.Discrete(2),
            "myfield5effects_aura": spaces.Discrete(2),
            "myfield5effects_cantbetargeted": spaces.Discrete(2),
            "myfield5effects_charge": spaces.Discrete(2),
            "myfield5effects_deathrattle": spaces.Discrete(2),
            "myfield5effects_divineshield": spaces.Discrete(2),
            "myfield5effects_frozen": spaces.Discrete(2),
            "myfield5effects_poisonous": spaces.Discrete(2),
            "myfield5effects_silenced": spaces.Discrete(2),
            "myfield5effects_stealth": spaces.Discrete(2),
            "myfield5effects_taunt": spaces.Discrete(2),
            "myfield5effects_windfury": spaces.Discrete(2),
            "myfield6effects_aura": spaces.Discrete(2),
            "myfield6effects_cantbetargeted": spaces.Discrete(2),
            "myfield6effects_charge": spaces.Discrete(2),
            "myfield6effects_deathrattle": spaces.Discrete(2),
            "myfield6effects_divineshield": spaces.Discrete(2),
            "myfield6effects_frozen": spaces.Discrete(2),
            "myfield6effects_poisonous": spaces.Discrete(2),
            "myfield6effects_silenced": spaces.Discrete(2),
            "myfield6effects_stealth": spaces.Discrete(2),
            "myfield6effects_taunt": spaces.Discrete(2),
            "myfield6effects_windfury": spaces.Discrete(2),
            "oppfield0effects_aura": spaces.Discrete(2),
            "oppfield0effects_cantbetargeted": spaces.Discrete(2),
            "oppfield0effects_charge": spaces.Discrete(2),
            "oppfield0effects_deathrattle": spaces.Discrete(2),
            "oppfield0effects_divineshield": spaces.Discrete(2),
            "oppfield0effects_frozen": spaces.Discrete(2),
            "oppfield0effects_poisonous": spaces.Discrete(2),
            "oppfield0effects_silenced": spaces.Discrete(2),
            "oppfield0effects_stealth": spaces.Discrete(2),
            "oppfield0effects_taunt": spaces.Discrete(2),
            "oppfield0effects_windfury": spaces.Discrete(2),
            "oppfield1effects_aura": spaces.Discrete(2),
            "oppfield1effects_cantbetargeted": spaces.Discrete(2),
            "oppfield1effects_charge": spaces.Discrete(2),
            "oppfield1effects_deathrattle": spaces.Discrete(2),
            "oppfield1effects_divineshield": spaces.Discrete(2),
            "oppfield1effects_frozen": spaces.Discrete(2),
            "oppfield1effects_poisonous": spaces.Discrete(2),
            "oppfield1effects_silenced": spaces.Discrete(2),
            "oppfield1effects_stealth": spaces.Discrete(2),
            "oppfield1effects_taunt": spaces.Discrete(2),
            "oppfield1effects_windfury": spaces.Discrete(2),
            "oppfield2effects_aura": spaces.Discrete(2),
            "oppfield2effects_cantbetargeted": spaces.Discrete(2),
            "oppfield2effects_charge": spaces.Discrete(2),
            "oppfield2effects_deathrattle": spaces.Discrete(2),
            "oppfield2effects_divineshield": spaces.Discrete(2),
            "oppfield2effects_frozen": spaces.Discrete(2),
            "oppfield2effects_poisonous": spaces.Discrete(2),
            "oppfield2effects_silenced": spaces.Discrete(2),
            "oppfield2effects_stealth": spaces.Discrete(2),
            "oppfield2effects_taunt": spaces.Discrete(2),
            "oppfield2effects_windfury": spaces.Discrete(2),
            "oppfield3effects_aura": spaces.Discrete(2),
            "oppfield3effects_cantbetargeted": spaces.Discrete(2),
            "oppfield3effects_charge": spaces.Discrete(2),
            "oppfield3effects_deathrattle": spaces.Discrete(2),
            "oppfield3effects_divineshield": spaces.Discrete(2),
            "oppfield3effects_frozen": spaces.Discrete(2),
            "oppfield3effects_poisonous": spaces.Discrete(2),
            "oppfield3effects_silenced": spaces.Discrete(2),
            "oppfield3effects_stealth": spaces.Discrete(2),
            "oppfield3effects_taunt": spaces.Discrete(2),
            "oppfield3effects_windfury": spaces.Discrete(2),
            "oppfield4effects_aura": spaces.Discrete(2),
            "oppfield4effects_cantbetargeted": spaces.Discrete(2),
            "oppfield4effects_charge": spaces.Discrete(2),
            "oppfield4effects_deathrattle": spaces.Discrete(2),
            "oppfield4effects_divineshield": spaces.Discrete(2),
            "oppfield4effects_frozen": spaces.Discrete(2),
            "oppfield4effects_poisonous": spaces.Discrete(2),
            "oppfield4effects_silenced": spaces.Discrete(2),
            "oppfield4effects_stealth": spaces.Discrete(2),
            "oppfield4effects_taunt": spaces.Discrete(2),
            "oppfield4effects_windfury": spaces.Discrete(2),
            "oppfield5effects_aura": spaces.Discrete(2),
            "oppfield5effects_cantbetargeted": spaces.Discrete(2),
            "oppfield5effects_charge": spaces.Discrete(2),
            "oppfield5effects_deathrattle": spaces.Discrete(2),
            "oppfield5effects_divineshield": spaces.Discrete(2),
            "oppfield5effects_frozen": spaces.Discrete(2),
            "oppfield5effects_poisonous": spaces.Discrete(2),
            "oppfield5effects_silenced": spaces.Discrete(2),
            "oppfield5effects_stealth": spaces.Discrete(2),
            "oppfield5effects_taunt": spaces.Discrete(2),
            "oppfield5effects_windfury": spaces.Discrete(2),
            "oppfield6effects_aura": spaces.Discrete(2),
            "oppfield6effects_cantbetargeted": spaces.Discrete(2),
            "oppfield6effects_charge": spaces.Discrete(2),
            "oppfield6effects_deathrattle": spaces.Discrete(2),
            "oppfield6effects_divineshield": spaces.Discrete(2),
            "oppfield6effects_frozen": spaces.Discrete(2),
            "oppfield6effects_poisonous": spaces.Discrete(2),
            "oppfield6effects_silenced": spaces.Discrete(2),
            "oppfield6effects_stealth": spaces.Discrete(2),
            "oppfield6effects_taunt": spaces.Discrete(2),
            "oppfield6effects_windfury": spaces.Discrete(2),
            "myfield0canattack": spaces.Discrete(2),
            "myfield1canattack": spaces.Discrete(2),
            "myfield2canattack": spaces.Discrete(2),
            "myfield3canattack": spaces.Discrete(2),
            "myfield4canattack": spaces.Discrete(2),
            "myfield5canattack": spaces.Discrete(2),
            "myfield6canattack": spaces.Discrete(2),
            "myherocanattack": spaces.Discrete(2)
        })
        self.curr_episode=-1
        self.action_episode_memory=[]
        self.alreadySelectedActions=[]
        self.setup_game()

    def reset(self):
        self.setup_game()
        return self._get_state()
    
    def setup_game(self):
        heroes=list(CardClass)
        heroes.remove(CardClass.INVALID)
        heroes.remove(CardClass.DREAM)
        heroes.remove(CardClass.NEUTRAL)
        heroes.remove(CardClass.WHIZBANG)
        while True:
            try:
                # At the root pretend the player just moved is p2 - p1 has the first move
                self.playerJustMoved=2
                self.playerToMove=1
                self.players_ordered=None
                self.hero1=random.choice(heroes)
                self.deck1=None
                self.hero2=random.choice(heroes)
                self.deck2=None
                self.game=None
                self.lastMovePlayed=None
                self.alreadySelectedActions = []
                # se meterá por aquí siempre porque deck1 y deck2 son None, diría que el IF no tiene sentido
                if self.hero1 is None or self.hero2 is None or self.deck1 is None or self.deck2 is None: 
                    self.deck1=[]
                    self.deck2=[]
                    # He modificado el codigo añadiendo dos collections para evitar tener que repetir el bucle for
                    # que retrasaba bastante la ejecución
                    collection1 = []
                    collection2 = []
                    # repaso todas las cartas y preservo las que son elegibles para el deck
                    for card in cards.db.keys():
                        if str(card) not in implemented_cards:
                            continue
                        cls = cards.db[card]
                        if not cls.collectible:
                            continue
                        if cls.type == CardType.HERO:
                            # Heroes are collectible...
                            continue
                        if cls.card_class and cls.card_class in [self.hero1, CardClass.NEUTRAL]:
                            # Play with more possibilities
                            collection1.append(cls)
                        if cls.card_class and cls.card_class in [self.hero2, CardClass.NEUTRAL]:
                            # Play with more possibilities
                            collection2.append(cls)

                    while len(self.deck1) < Deck.MAX_CARDS:
                        card = random.choice(collection1)
                        if self.deck1.count(card.id) < card.max_count_in_deck:
                            self.deck1.append(card.id)

                    while len(self.deck2) < Deck.MAX_CARDS:
                        card = random.choice(collection2)
                        if self.deck2.count(card.id) < card.max_count_in_deck:
                            self.deck2.append(card.id)
                    print(">>> Initialize PLAYER1")
                    self.player1=Player("Player1", self.deck1, self.hero1.default_hero)
                    print(">>> Initialize PLAYER2")
                    self.player2=Player("Player2", self.deck2, self.hero2.default_hero)
                    print(">>> Initialize GAME")
                    self.game=Game(players=(self.player1, self.player2))
                    self.game.start()
                    self.players_ordered=[self.game.player1, self.game.player2]
                    # At the root pretend the player just moved is p2 - p1 has the first move
                    self.playerJustMoved=2
                    self.playerToMove=1
                    self.lastMovePlayed=None
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
        self._take_action(action)
        reward=self._get_reward()
        ob=self._get_state()
        return ob, reward, reward != 0, {}

    def _take_action(self, action):
        possible_actions=self.__getMoves(); #get valid moves
        print(">>> possible_actions {}:{}".format(len(possible_actions),possible_actions))
        print(">>> alreadySelectedActions {}:{}".format(len(self.alreadySelectedActions),self.alreadySelectedActions))
        counter=0
        for a in self.alreadySelectedActions:
            possible_actions.remove(a) 
        print(">>> possible_actions {}:{}".format(len(possible_actions),possible_actions))
        
        # Hay una situación en el que possible_actions se vacía porque ya se han elegido todas las acciones posibles
        # por lo que la instrucción possible_actions[counter] Fallará al no contener ningún elemento.
        # Preguntar a Jesús. Es posible que cuando esto ocurra haya que rellenar el possible_actions con Move.end_turn???
        # Revisar el código del _getMoves porque hay varias cosas raras.

        while len(possible_actions)<869: #fill the entire action space by repeating some valid moves
            possible_actions.append(possible_actions[counter])
            counter=counter+1

        if possible_actions[action] == Move.end_turn: #if AI is ending turn - we need to register a random move for the other/random player
            print("doing end turn for AI")
            self.__doMove(possible_actions[action]) #do the AI Turn to swap game to the random player's turn
            self.alreadySelectedActions=[]
            possible_actions=self.__getMoves() #get the random player's actions
            action = random.choice(possible_actions) #pick a random one
            while action != Move.end_turn: #if it's not end turn
                print("doing single turn for rando")
                self.alreadySelectedActions.append(action)
                self.__doMove(action) #do it
                possible_actions=self.__getMoves() #and get the new set of actions
                for a in self.alreadySelectedActions:
                    possible_actions.remove(a)
                action=random.choice(possible_actions) #and pick a random one
            print("doing end turn for rando")
            self.__doMove(action) #end random player's turn
            self.alreadySelectedActions=[]
        else: #otherwise we just do the single AI action and keep track so its not used again
            print("doing single action for AI"+str(possible_actions[action]))
            self.__doMove(possible_actions[action])
            self.alreadySelectedActions.append(possible_actions[action])

    def __doMove(self, move, exceptionTester=[]):
        """ Update a state by carrying out the given move.
            Move format is [enum, index of selected card, target index, choice]
            Returns True if game is over
            Modified version of function from Ragowit's Fireplace fork
        """
        # print("move %s" % move[0])

        self.lastMovePlayed = move

        current_player = self.game.current_player

        if not self.game.step == Step.BEGIN_MULLIGAN:
            if current_player.playstate != PlayState.PLAYING:
                print("Attempt to execute move while current_player is in playstate: {}, move not executed".format(current_player.playstate.name))
                print("Attempted move: {}, on board:".format(move))
                self.render()
                return

            if current_player is self.game.player1:
                self.playerJustMoved = 1
            else:
                self.playerJustMoved = 2

        try:
            if move[0] == Move.mulligan:
                cards = [self.__currentMulliganer().choice.cards[i] for i in move[1]]
                self.__currentMulliganer().choice.choose(*cards)
                self.playerToMove = self.playerJustMoved
                self.playerJustMoved = -(self.playerJustMoved - 1) + 2
            elif move[0] == Move.end_mulligan:
                self.game.mulligan_done()
            elif move[0] == Move.end_turn:
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
        except exceptions.GameOver:
            return True
        except Exception as e:
            # print("Ran into exception: {} While executing move {} for player {}. Game State:".format(str(e), move, self.playerJustMoved))
            # self.render()
            exceptionTester.append(1) # array will eval to True
        if not self.game.step == Step.BEGIN_MULLIGAN:
            self.playerToMove = 1 if self.game.current_player is self.game.player1 else 2
        return False
    
    def __currentMulliganer(self):
        if not self.game.step == Step.BEGIN_MULLIGAN:
            return None
        return self.players_ordered[self.playerToMove - 1]

    def __getMoves(self):
        """ Get all possible moves from this state.
            Modified version of function from Ragowit's Fireplace fork
        """

        valid_moves = []

        if (self.game.step == Step.MAIN_ACTION):
            self.alreadySelectedActions = []

        # Mulligan
        if self.game.step == Step.BEGIN_MULLIGAN:
            player = self.__currentMulliganer()
            for s in player.choice.cards:
                valid_moves.append([Move.mulligan, s])
            valid_moves.append([Move.end_mulligan])
            return valid_moves

        current_player = self.game.current_player
        if current_player.playstate != PlayState.PLAYING:
            return []

        # Choose card
        if current_player.choice is not None:
            for i in range(len(current_player.choice.cards)):
                valid_moves.append([Move.choice, i])
            return valid_moves

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
                                else:
                                    valid_moves.append(
                                        [Move.play_card, current_player.hand.index(card), None, i])
                        elif len(card.targets) > 0:
                            for t in range(len(card.targets)):
                                valid_moves.append(
                                    [Move.play_card, current_player.hand.index(card), t, None])
                        else:
                            valid_moves.append(
                                [Move.play_card, current_player.hand.index(card), None, None])

            # Hero Power
            heropower = current_player.hero.power
            if heropower.is_usable():
                if len(heropower.targets) > 0:
                    for t in range(len(heropower.targets)):
                        valid_moves.append([Move.hero_power, None, t])
                else:
                    valid_moves.append([Move.hero_power, None, None])
            # Minion Attack
            for minion in current_player.field:
                if minion.can_attack():
                    for t in range(len(minion.targets)):
                        valid_moves.append(
                            [Move.minion_attack, current_player.field.index(minion), t])

            # Hero Attack
            hero = current_player.hero
            if hero.can_attack():
                for t in range(len(hero.targets)):
                    valid_moves.append([Move.hero_attack, None, t])

            valid_moves.append([Move.end_turn])
        return valid_moves

    def _get_reward(self):
        """ Get the current reward, from the perspective of the player who just moved
            1 for win, -1 for loss
            0 if game is not over
        """
        player=self.playerJustMoved
        if self.players_ordered[0].hero.health <= 0 and self.players_ordered[1].hero.health <= 0:  # tie
            return 0.1
        elif self.players_ordered[player - 1].hero.health <= 0:  # loss
            return -1
        elif self.players_ordered[2 - player].hero.health <= 0:  # win
            return 1
        else:
            return 0

    def _get_state(self):
        game=self.game
        player=self.players_ordered[self.playerToMove - 1]
        p1=player
        p2=player.opponent
        for i in range(10):
            try:
                print(">>>>",type(p1.hand[i]),p1.hand[i])
            except:
                print(">>>> no ",i)
        s={
            "myhero": p1.hero.card_class-1,
            "opphero": p2.hero.card_class-1,
            "myhealth": p1.hero.health,
            "opphealth": p2.hero.health,
            "myarmor": p1.hero.armor,
            "opparmor": p2.hero.armor,
            "myweaponatt": p1.weapon.atk if p1.weapon else 0,
            "oppweaponatt": p2.weapon.damage if p2.weapon else 0,
            "myweapondur": p1.weapon.durability if p1.weapon else 0,
            "oppweapondur": p2.weapon.durability if p2.weapon else 0, 
            "myheropoweravail": p1.hero.power.is_usable() * 1,
            "myunusedmanacrystals": p1.mana,
            "myusedmanacrystals": p1.max_mana-p1.mana,
            "oppcrystals": p2.max_mana,
            "mynumcardsinhand": len(p1.hand),
            "oppnumcardsinhand": len(p2.hand),
            "mynumminions": len(p1.field),
            "oppnumminions": len(p2.field),
            "mynumsecrets": len(p1.secrets),
            "oppnumsecrets": len(p2.secrets),
            "myhand0": implemented_cards.index(p1.hand[0]) if 0 < len(p1.hand) else 0,
            "myhand1": implemented_cards.index(p1.hand[1]) if 1 < len(p1.hand) else 0,
            "myhand2": implemented_cards.index(p1.hand[2]) if 2 < len(p1.hand) else 0,
            "myhand3": implemented_cards.index(p1.hand[3]) if 3 < len(p1.hand) else 0,
            "myhand4": implemented_cards.index(p1.hand[4]) if 4 < len(p1.hand) else 0,
            "myhand5": implemented_cards.index(p1.hand[5]) if 5 < len(p1.hand) else 0,
            "myhand6": implemented_cards.index(p1.hand[6]) if 6 < len(p1.hand) else 0,
            "myhand7": implemented_cards.index(p1.hand[7]) if 7 < len(p1.hand) else 0,
            "myhand8": implemented_cards.index(p1.hand[8]) if 8 < len(p1.hand) else 0,
            "myhand9": implemented_cards.index(p1.hand[9]) if 9 < len(p1.hand) else 0,
            "myfield0": implemented_cards.index(p1.field[0]) if 0 < len(p1.field) else 0,
            "myfield1": implemented_cards.index(p1.field[1]) if 1 < len(p1.field) else 0,
            "myfield2": implemented_cards.index(p1.field[2]) if 2 < len(p1.field) else 0,
            "myfield3": implemented_cards.index(p1.field[3]) if 3 < len(p1.field) else 0,
            "myfield4": implemented_cards.index(p1.field[4]) if 4 < len(p1.field) else 0,
            "myfield5": implemented_cards.index(p1.field[5]) if 5 < len(p1.field) else 0,
            "myfield6": implemented_cards.index(p1.field[6]) if 6 < len(p1.field) else 0,
            "oppfield0": implemented_cards.index(p2.field[0]) if 0 < len(p2.field) else 0,
            "oppfield1": implemented_cards.index(p2.field[1]) if 1 < len(p2.field) else 0,
            "oppfield2": implemented_cards.index(p2.field[2]) if 2 < len(p2.field) else 0,
            "oppfield3": implemented_cards.index(p2.field[3]) if 3 < len(p2.field) else 0,
            "oppfield4": implemented_cards.index(p2.field[4]) if 4 < len(p2.field) else 0,
            "oppfield5": implemented_cards.index(p2.field[5]) if 5 < len(p2.field) else 0,
            "oppfield6": implemented_cards.index(p2.field[6]) if 6 < len(p2.field) else 0,
            "myhand0att": p1.hand[0].atk if 0 < len(p1.hand) and p1.hand[0].type != 7 and p1.hand[0].type !=5 else 0,
            "myhand1att": p1.hand[1].atk if 1 < len(p1.hand) and p1.hand[1].type != 7 and p1.hand[1].type !=5 else 0,
            "myhand2att": p1.hand[2].atk if 2 < len(p1.hand) and p1.hand[2].type != 7 and p1.hand[2].type !=5 else 0,
            "myhand3att": p1.hand[3].atk if 3 < len(p1.hand) and p1.hand[3].type != 7 and p1.hand[3].type !=5 else 0,
            "myhand4att": p1.hand[4].atk if 4 < len(p1.hand) and p1.hand[4].type != 7 and p1.hand[4].type !=5 else 0,
            "myhand5att": p1.hand[5].atk if 5 < len(p1.hand) and p1.hand[5].type != 7 and p1.hand[5].type !=5 else 0,
            "myhand6att": p1.hand[6].atk if 6 < len(p1.hand) and p1.hand[6].type != 7 and p1.hand[6].type !=5 else 0,
            "myhand7att": p1.hand[7].atk if 7 < len(p1.hand) and p1.hand[7].type != 7 and p1.hand[7].type !=5 else 0,
            "myhand8att": p1.hand[8].atk if 8 < len(p1.hand) and p1.hand[8].type != 7 and p1.hand[8].type !=5 else 0,
            "myhand9att": p1.hand[9].atk if 9 < len(p1.hand) and p1.hand[9].type != 7 and p1.hand[9].type !=5 else 0,
            "myfield0att": p1.field[0].atk if 0 < len(p1.field) and p1.field[0].type != 7 and p1.field[0].type !=5 else 0,
            "myfield1att": p1.field[1].atk if 1 < len(p1.field) and p1.field[1].type != 7 and p1.field[1].type !=5 else 0,
            "myfield2att": p1.field[2].atk if 2 < len(p1.field) and p1.field[2].type != 7 and p1.field[2].type !=5 else 0,
            "myfield3att": p1.field[3].atk if 3 < len(p1.field) and p1.field[3].type != 7 and p1.field[3].type !=5 else 0,
            "myfield4att": p1.field[4].atk if 4 < len(p1.field) and p1.field[4].type != 7 and p1.field[4].type !=5 else 0,
            "myfield5att": p1.field[5].atk if 5 < len(p1.field) and p1.field[5].type != 7 and p1.field[5].type !=5 else 0,
            "myfield6att": p1.field[6].atk if 6 < len(p1.field) and p1.field[6].type != 7 and p1.field[6].type !=5 else 0,
            "oppfield0att": p2.field[0].atk if 0 < len(p2.field) and p2.field[0].type != 7 and p2.field[0].type !=5 else 0,
            "oppfield1att": p2.field[1].atk if 1 < len(p2.field) and p2.field[1].type != 7 and p2.field[1].type !=5 else 0,
            "oppfield2att": p2.field[2].atk if 2 < len(p2.field) and p2.field[2].type != 7 and p2.field[2].type !=5 else 0,
            "oppfield3att": p2.field[3].atk if 3 < len(p2.field) and p2.field[3].type != 7 and p2.field[3].type !=5 else 0,
            "oppfield4att": p2.field[4].atk if 4 < len(p2.field) and p2.field[4].type != 7 and p2.field[4].type !=5 else 0,
            "oppfield5att": p2.field[5].atk if 5 < len(p2.field) and p2.field[5].type != 7 and p2.field[5].type !=5 else 0,
            "oppfield6att": p2.field[6].atk if 6 < len(p2.field) and p2.field[6].type != 7 and p2.field[6].type !=5 else 0,
            "myhand0def": p1.hand[0].health if 0 < len(p1.hand) and p1.hand[0].type != 7 and p1.hand[0].type !=5 else 0,
            "myhand1def": p1.hand[1].health if 1 < len(p1.hand) and p1.hand[1].type != 7 and p1.hand[1].type !=5 else 0,
            "myhand2def": p1.hand[2].health if 2 < len(p1.hand) and p1.hand[2].type != 7 and p1.hand[2].type !=5 else 0,
            "myhand3def": p1.hand[3].health if 3 < len(p1.hand) and p1.hand[3].type != 7 and p1.hand[3].type !=5 else 0,
            "myhand4def": p1.hand[4].health if 4 < len(p1.hand) and p1.hand[4].type != 7 and p1.hand[4].type !=5 else 0,
            "myhand5def": p1.hand[5].health if 5 < len(p1.hand) and p1.hand[5].type != 7 and p1.hand[5].type !=5 else 0,
            "myhand6def": p1.hand[6].health if 6 < len(p1.hand) and p1.hand[6].type != 7 and p1.hand[6].type !=5 else 0,
            "myhand7def": p1.hand[7].health if 7 < len(p1.hand) and p1.hand[7].type != 7 and p1.hand[7].type !=5 else 0,
            "myhand8def": p1.hand[8].health if 8 < len(p1.hand) and p1.hand[8].type != 7 and p1.hand[8].type !=5 else 0,
            "myhand9def": p1.hand[9].health if 9 < len(p1.hand) and p1.hand[9].type != 7 and p1.hand[9].type !=5 else 0,
            "myfield0def": p1.field[0].health if 0 < len(p1.field) and p1.field[0].type != 7 and p1.field[0].type !=5 else 0,
            "myfield1def": p1.field[1].health if 1 < len(p1.field) and p1.field[1].type != 7 and p1.field[1].type !=5 else 0,
            "myfield2def": p1.field[2].health if 2 < len(p1.field) and p1.field[2].type != 7 and p1.field[2].type !=5 else 0,
            "myfield3def": p1.field[3].health if 3 < len(p1.field) and p1.field[3].type != 7 and p1.field[3].type !=5 else 0,
            "myfield4def": p1.field[4].health if 4 < len(p1.field) and p1.field[4].type != 7 and p1.field[4].type !=5 else 0,
            "myfield5def": p1.field[5].health if 5 < len(p1.field) and p1.field[5].type != 7 and p1.field[5].type !=5 else 0,
            "myfield6def": p1.field[6].health if 6 < len(p1.field) and p1.field[6].type != 7 and p1.field[6].type !=5 else 0,
            "oppfield0def": p2.field[0].health if 0 < len(p2.field) and p2.field[0].type != 7 and p2.field[0].type !=5 else 0,
            "oppfield1def": p2.field[1].health if 1 < len(p2.field) and p2.field[1].type != 7 and p2.field[1].type !=5 else 0,
            "oppfield2def": p2.field[2].health if 2 < len(p2.field) and p2.field[2].type != 7 and p2.field[2].type !=5 else 0,
            "oppfield3def": p2.field[3].health if 3 < len(p2.field) and p2.field[3].type != 7 and p2.field[3].type !=5 else 0,
            "oppfield4def": p2.field[4].health if 4 < len(p2.field) and p2.field[4].type != 7 and p2.field[4].type !=5 else 0,
            "oppfield5def": p2.field[5].health if 5 < len(p2.field) and p2.field[5].type != 7 and p2.field[5].type !=5 else 0,
            "oppfield6def": p2.field[6].health if 6 < len(p2.field) and p2.field[6].type != 7 and p2.field[6].type !=5 else 0,
            "myhand0effects_windfury": 1 if 0 < len(p1.hand) and p1.hand[0].windfury else 0,
            "myhand0effects_divineshield": 1 if 0 < len(p1.hand) and p1.hand[0].type != 5 and p1.hand[0].type != 7 and p1.hand[0].divine_shield else 0,
            "myhand0effects_charge": 1 if 0 < len(p1.hand) and p1.hand[0].type != 5 and p1.hand[0].type != 7 and p1.hand[0].charge else 0,
            "myhand0effects_taunt": 1 if 0 < len(p1.hand) and p1.hand[0].type != 5 and p1.hand[0].type != 7 and p1.hand[0].taunt else 0,
            "myhand0effects_stealth": 1 if 0 < len(p1.hand) and p1.hand[0].type != 5 and p1.hand[0].type != 7 and p1.hand[0].stealthed else 0,
            "myhand0effects_poisonous": 1 if 0 < len(p1.hand) and p1.hand[0].type != 5 and p1.hand[0].type != 7 and p1.hand[0].poisonous else 0,
            "myhand0effects_cantbetargeted": 1 if 0 < len(p1.hand) and p1.hand[0].type != 5 and p1.hand[0].type != 7 and (p1.hand[0].cant_be_targeted_by_abilities or p1.hand[0].cant_be_targeted_by_hero_powers) else 0,
            "myhand0effects_aura": 1 if 0 < len(p1.hand) and p1.hand[0].aura else 0,
            "myhand0effects_deathrattle": 1 if 0 < len(p1.hand) and p1.hand[0].type != 5 and p1.hand[0].has_deathrattle else 0,
            "myhand0effects_frozen": 1 if 0 < len(p1.hand) and p1.hand[0].type != 5 and p1.hand[0].type != 7 and p1.hand[0].frozen else 0,
            "myhand0effects_silenced": 1 if 0 < len(p1.hand) and p1.hand[0].type != 5 and p1.hand[0].type != 7 and p1.hand[0].silenced else 0,
            "myhand1effects_windfury": 1 if 1 < len(p1.hand) and p1.hand[1].windfury else 0,
            "myhand1effects_divineshield": 1 if 1 < len(p1.hand) and p1.hand[1].type!=5 and p1.hand[1].type!=7 and p1.hand[1].divine_shield else 0,
            "myhand1effects_charge": 1 if 1 < len(p1.hand) and p1.hand[1].type != 5 and p1.hand[1].type != 7 and p1.hand[1].charge else 0,
            "myhand1effects_taunt": 1 if 1 < len(p1.hand) and p1.hand[1].type!=5 and p1.hand[1].type!=7 and p1.hand[1].taunt else 0,
            "myhand1effects_stealth": 1 if 1 < len(p1.hand) and p1.hand[1].type != 5 and p1.hand[1].type != 7 and p1.hand[1].stealthed else 0,
            "myhand1effects_poisonous": 1 if 1 < len(p1.hand) and p1.hand[1].type != 5 and p1.hand[1].type != 7 and p1.hand[1].poisonous else 0,
            "myhand1effects_cantbetargeted": 1 if 1 < len(p1.hand) and p1.hand[1].type != 5 and p1.hand[1].type != 7 and (p1.hand[1].cant_be_targeted_by_abilities or p1.hand[1].cant_be_targeted_by_hero_powers) else 0,
            "myhand1effects_aura": 1 if 1 < len(p1.hand) and p1.hand[1].aura else 0,
            "myhand1effects_deathrattle": 1 if 1 < len(p1.hand) and p1.hand[1].type!=5 and p1.hand[1].has_deathrattle else 0,
            "myhand1effects_frozen": 1 if 1 < len(p1.hand) and p1.hand[1].type != 5 and p1.hand[1].type != 7 and p1.hand[1].frozen else 0,
            "myhand1effects_silenced": 1 if 1 < len(p1.hand) and p1.hand[1].type != 5 and p1.hand[1].type != 7 and p1.hand[1].silenced else 0,
            "myhand2effects_windfury": 1 if 2 < len(p1.hand) and p1.hand[2].windfury else 0,
            "myhand2effects_divineshield": 1 if 2 < len(p1.hand) and p1.hand[2].type!=5 and p1.hand[2].type!=7 and p1.hand[2].divine_shield else 0,
            "myhand2effects_charge": 1 if 2 < len(p1.hand) and p1.hand[2].type != 5 and p1.hand[2].type != 7 and p1.hand[2].charge else 0,
            "myhand2effects_taunt": 1 if 2 < len(p1.hand) and p1.hand[2].type != 5 and p1.hand[2].type != 7 and p1.hand[2].taunt else 0,
            "myhand2effects_stealth": 1 if 2 < len(p1.hand) and p1.hand[2].type!=5 and p1.hand[2].type!=7 and p1.hand[2].stealthed else 0,
            "myhand2effects_poisonous": 1 if 2 < len(p1.hand) and p1.hand[2].type != 5 and p1.hand[2].type != 7 and p1.hand[2].poisonous else 0,
            "myhand2effects_cantbetargeted": 1 if 2 < len(p1.hand) and p1.hand[2].type != 5 and p1.hand[2].type != 7 and (p1.hand[2].cant_be_targeted_by_abilities or p1.hand[2].cant_be_targeted_by_hero_powers) else 0,
            "myhand2effects_aura": 1 if 2 < len(p1.hand) and p1.hand[2].aura else 0,
            "myhand2effects_deathrattle": 1 if 2 < len(p1.hand) and p1.hand[2].type!=5 and p1.hand[2].has_deathrattle else 0,
            "myhand2effects_frozen": 1 if 2 < len(p1.hand) and p1.hand[2].type != 5 and p1.hand[2].type != 7 and p1.hand[2].frozen else 0,
            "myhand2effects_silenced": 1 if 2 < len(p1.hand) and p1.hand[2].type != 5 and p1.hand[2].type != 7 and p1.hand[2].silenced else 0,
            "myhand3effects_windfury": 1 if 3 < len(p1.hand) and p1.hand[3].windfury else 0,
            "myhand3effects_divineshield": 1 if 3 < len(p1.hand) and p1.hand[3].type != 5 and p1.hand[3].type != 7 and p1.hand[3].divine_shield else 0,
            "myhand3effects_charge": 1 if 3 < len(p1.hand) and p1.hand[3].type != 5 and p1.hand[3].type != 7 and p1.hand[3].charge else 0,
            "myhand3effects_taunt": 1 if 3 < len(p1.hand) and p1.hand[3].type!=5 and p1.hand[3].type != 7 and p1.hand[3].taunt else 0,
            "myhand3effects_stealth": 1 if 3 < len(p1.hand) and p1.hand[3].type != 5 and p1.hand[3].type != 7 and p1.hand[3].stealthed else 0,
            "myhand3effects_poisonous": 1 if 3 < len(p1.hand) and p1.hand[3].type != 5 and p1.hand[3].type != 7 and p1.hand[3].poisonous else 0,
            "myhand3effects_cantbetargeted": 1 if 3 < len(p1.hand) and p1.hand[3].type != 5 and p1.hand[3].type != 7 and (p1.hand[3].cant_be_targeted_by_abilities or p1.hand[3].cant_be_targeted_by_hero_powers) else 0,
            "myhand3effects_aura": 1 if 3 < len(p1.hand) and p1.hand[3].aura else 0,
            "myhand3effects_deathrattle": 1 if 3 < len(p1.hand) and p1.hand[3].type!=5 and p1.hand[3].has_deathrattle else 0,
            "myhand3effects_frozen": 1 if 3 < len(p1.hand) and p1.hand[3].type != 5 and p1.hand[3].type != 7 and p1.hand[3].frozen else 0,
            "myhand3effects_silenced": 1 if 3 < len(p1.hand) and p1.hand[3].type != 5 and p1.hand[3].type != 7 and p1.hand[3].silenced else 0,
            "myhand4effects_windfury": 1 if 4 < len(p1.hand) and p1.hand[4].windfury else 0,
            "myhand4effects_divineshield": 1 if 4 < len(p1.hand) and p1.hand[4].type != 5 and p1.hand[4].type != 7 and p1.hand[4].divine_shield else 0,
            "myhand4effects_charge": 1 if 4 < len(p1.hand) and p1.hand[4].type != 5 and p1.hand[4].type != 7 and p1.hand[4].charge else 0,
            "myhand4effects_taunt": 1 if 4 < len(p1.hand) and p1.hand[4].type!=5 and p1.hand[4].type != 7 and p1.hand[4].taunt else 0,
            "myhand4effects_stealth": 1 if 4 < len(p1.hand) and p1.hand[4].type != 5 and p1.hand[4].type != 7 and p1.hand[4].stealthed else 0,
            "myhand4effects_poisonous": 1 if 4 < len(p1.hand) and p1.hand[4].type != 5 and p1.hand[4].type != 7 and p1.hand[4].poisonous else 0,
            "myhand4effects_cantbetargeted": 1 if 4 < len(p1.hand) and p1.hand[4].type != 5 and p1.hand[4].type != 7 and (p1.hand[4].cant_be_targeted_by_abilities or p1.hand[4].cant_be_targeted_by_hero_powers) else 0,
            "myhand4effects_aura": 1 if 4 < len(p1.hand) and p1.hand[4].aura else 0,
            "myhand4effects_deathrattle": 1 if 4 < len(p1.hand) and p1.hand[4].type!=5 and p1.hand[4].has_deathrattle else 0,
            "myhand4effects_frozen": 1 if 4 < len(p1.hand) and p1.hand[4].type != 5 and p1.hand[4].type != 7 and p1.hand[4].frozen else 0,
            "myhand4effects_silenced": 1 if 4 < len(p1.hand) and p1.hand[4].type != 5 and p1.hand[4].type != 7 and p1.hand[4].silenced else 0,
            "myhand5effects_windfury": 1 if 5 < len(p1.hand) and p1.hand[5].windfury else 0,
            "myhand5effects_divineshield": 1 if 5 < len(p1.hand) and p1.hand[5].type != 5 and p1.hand[5].type != 7 and p1.hand[5].divine_shield else 0,
            "myhand5effects_charge": 1 if 5 < len(p1.hand) and p1.hand[5].type!=5 and p1.hand[5].type!= 7 and p1.hand[5].charge else 0,
            "myhand5effects_taunt": 1 if 5 < len(p1.hand) and p1.hand[5].type != 5 and p1.hand[5].type != 7 and p1.hand[5].taunt else 0,
            "myhand5effects_stealth": 1 if 5 < len(p1.hand) and p1.hand[5].type != 5 and p1.hand[5].type != 7 and p1.hand[5].stealthed else 0,
            "myhand5effects_poisonous": 1 if 5 < len(p1.hand) and p1.hand[5].type != 5 and p1.hand[5].type != 7 and p1.hand[5].poisonous else 0,
            "myhand5effects_cantbetargeted": 1 if 5 < len(p1.hand) and p1.hand[5].type != 5 and p1.hand[5].type != 7 and (p1.hand[5].cant_be_targeted_by_abilities or p1.hand[5].cant_be_targeted_by_hero_powers) else 0,
            "myhand5effects_aura": 1 if 5 < len(p1.hand) and p1.hand[5].aura else 0,
            "myhand5effects_deathrattle": 1 if 5 < len(p1.hand) and p1.hand[5].type!=5 and p1.hand[5].has_deathrattle else 0,
            "myhand5effects_frozen": 1 if 5 < len(p1.hand) and p1.hand[5].type!=5 and p1.hand[5].type != 7 and p1.hand[5].frozen else 0,
            "myhand5effects_silenced": 1 if 5 < len(p1.hand) and p1.hand[5].type != 5 and p1.hand[5].type != 7 and p1.hand[5].silenced else 0,
            "myhand6effects_windfury": 1 if 6 < len(p1.hand) and p1.hand[6].windfury else 0,
            "myhand6effects_divineshield": 1 if 6 < len(p1.hand) and p1.hand[6].type != 5 and p1.hand[6].type != 7 and p1.hand[6].divine_shield else 0,
            "myhand6effects_charge": 1 if 6 < len(p1.hand) and p1.hand[6].type!=5 and p1.hand[6].type != 7 and p1.hand[6].charge else 0,
            "myhand6effects_taunt": 1 if 6 < len(p1.hand) and p1.hand[6].type!=5 and p1.hand[6].type != 7 and p1.hand[6].taunt else 0,
            "myhand6effects_stealth": 1 if 6 < len(p1.hand) and p1.hand[6].type != 5 and p1.hand[6].type != 7 and p1.hand[6].stealthed else 0,
            "myhand6effects_poisonous": 1 if 6 < len(p1.hand) and p1.hand[6].type != 5 and p1.hand[6].type != 7 and p1.hand[6].poisonous else 0,
            "myhand6effects_cantbetargeted": 1 if 6 < len(p1.hand) and p1.hand[6].type != 5 and p1.hand[6].type != 7 and (p1.hand[6].cant_be_targeted_by_abilities or p1.hand[6].cant_be_targeted_by_hero_powers) else 0,
            "myhand6effects_aura": 1 if 6 < len(p1.hand) and p1.hand[6].aura else 0,
            "myhand6effects_deathrattle": 1 if 6 < len(p1.hand) and p1.hand[6].type!=5 and p1.hand[6].has_deathrattle else 0,
            "myhand6effects_frozen": 1 if 6 < len(p1.hand) and p1.hand[6].type != 5 and p1.hand[6].type != 7 and p1.hand[6].frozen else 0,
            "myhand6effects_silenced": 1 if 6 < len(p1.hand) and p1.hand[6].type != 5 and p1.hand[6].type != 7 and p1.hand[6].silenced else 0,
            "myhand7effects_windfury": 1 if 7 < len(p1.hand) and p1.hand[7].windfury else 0,
            "myhand7effects_divineshield": 1 if 7 < len(p1.hand) and p1.hand[7].type != 5 and p1.hand[7].type != 7 and p1.hand[7].divine_shield else 0,
            "myhand7effects_charge": 1 if 7 < len(p1.hand) and p1.hand[7].type!=5 and p1.hand[7].type != 7 and p1.hand[7].charge else 0,
            "myhand7effects_taunt": 1 if 7 < len(p1.hand) and p1.hand[7].type!=5 and p1.hand[7].type != 7 and p1.hand[7].taunt else 0,
            "myhand7effects_stealth": 1 if 7 < len(p1.hand) and p1.hand[7].type!=5 and p1.hand[7].type != 7 and p1.hand[7].stealthed else 0,
            "myhand7effects_poisonous": 1 if 7 < len(p1.hand) and p1.hand[7].type != 5 and p1.hand[7].type != 7 and p1.hand[7].poisonous else 0,
            "myhand7effects_cantbetargeted": 1 if 7 < len(p1.hand) and p1.hand[7].type != 5 and p1.hand[7].type != 7 and (p1.hand[7].cant_be_targeted_by_abilities or p1.hand[7].cant_be_targeted_by_hero_powers) else 0,
            "myhand7effects_aura": 1 if 7 < len(p1.hand) and p1.hand[7].aura else 0,
            "myhand7effects_deathrattle": 1 if 7 < len(p1.hand) and p1.hand[7].type!=5 and p1.hand[7].has_deathrattle else 0,
            "myhand7effects_frozen": 1 if 7 < len(p1.hand) and p1.hand[7].type!=5 and p1.hand[7].type != 7 and p1.hand[7].frozen else 0,
            "myhand7effects_silenced": 1 if 7 < len(p1.hand) and p1.hand[7].type != 5 and p1.hand[7].type != 7 and p1.hand[7].silenced else 0,
            "myhand8effects_windfury": 1 if 8 < len(p1.hand) and p1.hand[8].windfury else 0,
            "myhand8effects_divineshield": 1 if 8 < len(p1.hand) and p1.hand[8].type != 5 and p1.hand[8].type != 7 and p1.hand[8].divine_shield else 0,
            "myhand8effects_charge": 1 if 8 < len(p1.hand) and p1.hand[8].type != 5 and p1.hand[8].type != 7 and p1.hand[8].charge else 0,
            "myhand8effects_taunt": 1 if 8 < len(p1.hand) and p1.hand[8].type != 5 and p1.hand[8].type != 7 and p1.hand[8].taunt else 0,
            "myhand8effects_stealth": 1 if 8 < len(p1.hand) and p1.hand[8].type != 5 and p1.hand[8].type != 7 and p1.hand[8].stealthed else 0,
            "myhand8effects_poisonous": 1 if 8 < len(p1.hand) and p1.hand[8].type != 5 and p1.hand[8].type != 7 and p1.hand[8].poisonous else 0,
            "myhand8effects_cantbetargeted": 1 if 8 < len(p1.hand) and p1.hand[8].type != 5 and p1.hand[8].type != 7 and (p1.hand[8].cant_be_targeted_by_abilities or p1.hand[8].cant_be_targeted_by_hero_powers) else 0,
            "myhand8effects_aura": 1 if 8 < len(p1.hand) and p1.hand[8].aura else 0,
            "myhand8effects_deathrattle": 1 if 8 < len(p1.hand) and p1.hand[8].type!=5 and p1.hand[8].has_deathrattle else 0,
            "myhand8effects_frozen": 1 if 8 < len(p1.hand) and p1.hand[8].type != 5 and p1.hand[8].type != 7 and p1.hand[8].frozen else 0,
            "myhand8effects_silenced": 1 if 8 < len(p1.hand) and p1.hand[8].type != 5 and p1.hand[8].type != 7 and p1.hand[8].silenced else 0,
            "myhand9effects_windfury": 1 if 9 < len(p1.hand) and p1.hand[9].windfury else 0,
            "myhand9effects_divineshield": 1 if 9 < len(p1.hand) and p1.hand[9].type != 5 and p1.hand[9].type != 7 and p1.hand[9].divine_shield else 0,
            "myhand9effects_charge": 1 if 9 < len(p1.hand) and p1.hand[9].type!=5 and p1.hand[9].type != 7 and p1.hand[9].charge else 0,
            "myhand9effects_taunt": 1 if 9 < len(p1.hand) and p1.hand[9].type!=5 and p1.hand[9].type != 7 and p1.hand[9].taunt else 0,
            "myhand9effects_stealth": 1 if 9 < len(p1.hand) and p1.hand[9].type!=5 and p1.hand[9].type != 7 and p1.hand[9].stealthed else 0,
            "myhand9effects_poisonous": 1 if 9 < len(p1.hand) and p1.hand[9].type != 5 and p1.hand[9].type != 7 and p1.hand[9].poisonous else 0,
            "myhand9effects_cantbetargeted": 1 if 9 < len(p1.hand) and p1.hand[9].type != 5 and p1.hand[9].type != 7 and (p1.hand[9].cant_be_targeted_by_abilities or p1.hand[9].cant_be_targeted_by_hero_powers) else 0,
            "myhand9effects_aura": 1 if 9 < len(p1.hand) and p1.hand[9].aura else 0,
            "myhand9effects_deathrattle": 1 if 9 < len(p1.hand) and p1.hand[9].type!=5 and p1.hand[9].has_deathrattle else 0,
            "myhand9effects_frozen": 1 if 9 < len(p1.hand) and p1.hand[9].type!=5 and p1.hand[9].type != 7 and p1.hand[9].frozen else 0,
            "myhand9effects_silenced": 1 if 9 < len(p1.hand) and p1.hand[9].type != 5 and p1.hand[9].type != 7 and p1.hand[9].silenced else 0,
            "myfield0effects_windfury": 1 if 0 < len(p1.field) and p1.field[0].windfury else 0,
            "myfield0effects_divineshield": 1 if 0 < len(p1.field) and p1.field[0].type != 5 and p1.field[0].type != 7 and p1.field[0].divine_shield else 0,
            "myfield0effects_charge": 1 if 0 < len(p1.field) and p1.field[0].type!=5 and p1.field[0].type != 7 and p1.field[0].charge else 0,
            "myfield0effects_taunt": 1 if 0 < len(p1.field) and p1.field[0].type!=5 and p1.field[0].type != 7 and p1.field[0].taunt else 0,
            "myfield0effects_stealth": 1 if 0 < len(p1.field) and p1.field[0].type != 5 and p1.field[0].type != 7 and p1.field[0].stealthed else 0,
            "myfield0effects_poisonous": 1 if 0 < len(p1.field) and p1.field[0].type!=5 and p1.field[0].type != 7 and p1.field[0].poisonous else 0,
            "myfield0effects_cantbetargeted": 1 if 0 < len(p1.field) and p1.field[0].type != 5 and p1.field[0].type != 7 and (p1.field[0].cant_be_targeted_by_abilities or p1.field[0].cant_be_targeted_by_hero_powers) else 0,
            "myfield0effects_aura": 1 if 0 < len(p1.field) and p1.field[0].aura else 0,
            "myfield0effects_deathrattle": 1 if 0 < len(p1.field) and p1.field[0].type!=5 and p1.field[0].has_deathrattle else 0,
            "myfield0effects_frozen": 1 if 0 < len(p1.field) and p1.field[0].type!=5 and p1.field[0].type != 7 and p1.field[0].frozen else 0,
            "myfield0effects_silenced": 1 if 0 < len(p1.field) and p1.field[0].type != 5 and p1.field[0].type != 7 and p1.field[0].silenced else 0,
            "myfield1effects_windfury": 1 if 1 < len(p1.field) and p1.field[1].windfury else 0,
            "myfield1effects_divineshield": 1 if 1 < len(p1.field) and p1.field[1].type != 5 and p1.field[1].type != 7 and p1.field[1].divine_shield else 0,
            "myfield1effects_charge": 1 if 1 < len(p1.field) and p1.field[1].type!=5 and p1.field[1].type != 7 and p1.field[1].charge else 0,
            "myfield1effects_taunt": 1 if 1 < len(p1.field) and p1.field[1].type!=5 and p1.field[1].type != 7 and p1.field[1].taunt else 0,
            "myfield1effects_stealth": 1 if 1 < len(p1.field) and p1.field[1].type!=5 and p1.field[1].type != 7 and p1.field[1].stealthed else 0,
            "myfield1effects_poisonous": 1 if 1 < len(p1.field) and p1.field[1].type != 5 and p1.field[1].type != 7 and p1.field[1].poisonous else 0,
            "myfield1effects_cantbetargeted": 1 if 1 < len(p1.field) and p1.field[1].type != 5 and p1.field[1].type != 7 and (p1.field[1].cant_be_targeted_by_abilities or p1.field[1].cant_be_targeted_by_hero_powers) else 0,
            "myfield1effects_aura": 1 if 1 < len(p1.field) and p1.field[1].aura else 0,
            "myfield1effects_deathrattle": 1 if 1 < len(p1.field) and p1.field[1].type!=5 and p1.field[1].has_deathrattle else 0,
            "myfield1effects_frozen": 1 if 1 < len(p1.field) and p1.field[1].type!=5 and p1.field[1].type != 7 and p1.field[1].frozen else 0,
            "myfield1effects_silenced": 1 if 1 < len(p1.field) and p1.field[1].type != 5 and p1.field[1].type != 7 and p1.field[1].silenced else 0,
            "myfield2effects_windfury": 1 if 2 < len(p1.field) and p1.field[2].windfury else 0,
            "myfield2effects_divineshield": 1 if 2 < len(p1.field) and p1.field[2].type != 5 and p1.field[2].type != 7 and p1.field[2].divine_shield else 0,
            "myfield2effects_charge": 1 if 2 < len(p1.field) and p1.field[2].type!=5 and p1.field[2].type != 7 and p1.field[2].charge else 0,
            "myfield2effects_taunt": 1 if 2 < len(p1.field) and p1.field[2].type!=5 and p1.field[2].type != 7 and p1.field[2].taunt else 0,
            "myfield2effects_stealth": 1 if 2 < len(p1.field) and p1.field[2].type != 5 and p1.field[2].type != 7 and p1.field[2].stealthed else 0,
            "myfield2effects_poisonous": 1 if 2 < len(p1.field) and p1.field[2].type != 5 and p1.field[2].type != 7 and p1.field[2].poisonous else 0,
            "myfield2effects_cantbetargeted": 1 if 2 < len(p1.field) and p1.field[2].type != 5 and p1.field[2].type != 7 and (p1.field[2].cant_be_targeted_by_abilities or p1.field[2].cant_be_targeted_by_hero_powers) else 0,
            "myfield2effects_aura": 1 if 2 < len(p1.field) and p1.field[2].aura else 0,
            "myfield2effects_deathrattle": 1 if 2 < len(p1.field) and p1.field[2].type!=5 and p1.field[2].has_deathrattle else 0,
            "myfield2effects_frozen": 1 if 2 < len(p1.field) and p1.field[2].type!=5 and p1.field[2].type != 7 and p1.field[2].frozen else 0,
            "myfield2effects_silenced": 1 if 2 < len(p1.field) and p1.field[2].type != 5 and p1.field[2].type != 7 and p1.field[2].silenced else 0,
            "myfield3effects_windfury": 1 if 3 < len(p1.field) and p1.field[3].windfury else 0,
            "myfield3effects_divineshield": 1 if 3 < len(p1.field) and p1.field[3].type != 5 and p1.field[3].type != 7 and p1.field[3].divine_shield else 0,
            "myfield3effects_charge": 1 if 3 < len(p1.field) and p1.field[3].type!=5 and p1.field[3].type != 7 and p1.field[3].charge else 0,
            "myfield3effects_taunt": 1 if 3 < len(p1.field) and p1.field[3].type!=5 and p1.field[3].type != 7 and p1.field[3].taunt else 0,
            "myfield3effects_stealth": 1 if 3 < len(p1.field) and p1.field[3].type!=5 and p1.field[3].type != 7 and p1.field[3].stealthed else 0,
            "myfield3effects_poisonous": 1 if 3 < len(p1.field) and p1.field[3].type!=5 and p1.field[3].type != 7 and p1.field[3].poisonous else 0,
            "myfield3effects_cantbetargeted": 1 if 3 < len(p1.field) and p1.field[3].type!=5 and p1.field[3].type != 7 and (p1.field[3].cant_be_targeted_by_abilities or p1.field[3].cant_be_targeted_by_hero_powers) else 0,
            "myfield3effects_aura": 1 if 3 < len(p1.field) and p1.field[3].aura else 0,
            "myfield3effects_deathrattle": 1 if 3 < len(p1.field) and p1.field[3].type!=5 and p1.field[3].has_deathrattle else 0,
            "myfield3effects_frozen": 1 if 3 < len(p1.field) and p1.field[3].type != 5 and p1.field[3].type != 7 and p1.field[3].frozen else 0,
            "myfield3effects_silenced": 1 if 3 < len(p1.field) and p1.field[3].type != 5 and p1.field[3].type != 7 and p1.field[3].silenced else 0,
            "myfield4effects_windfury": 1 if 4 < len(p1.field) and p1.field[4].windfury else 0,
            "myfield4effects_divineshield": 1 if 4 < len(p1.field) and p1.field[4].type != 5 and p1.field[4].type != 7 and p1.field[4].divine_shield else 0,
            "myfield4effects_charge": 1 if 4 < len(p1.field) and p1.field[4].type != 5 and p1.field[4].type != 7 and p1.field[4].charge else 0,
            "myfield4effects_taunt": 1 if 4 < len(p1.field) and p1.field[4].type!=5 and p1.field[4].type != 7  and p1.field[4].taunt else 0,
            "myfield4effects_stealth": 1 if 4 < len(p1.field) and p1.field[4].type!=5 and p1.field[4].type != 7  and p1.field[4].stealthed else 0,
            "myfield4effects_poisonous": 1 if 4 < len(p1.field) and p1.field[4].type!=5 and p1.field[4].type != 7  and p1.field[4].poisonous else 0,
            "myfield4effects_cantbetargeted": 1 if 4 < len(p1.field) and p1.field[4].type != 5 and p1.field[4].type != 7 and (p1.field[4].cant_be_targeted_by_abilities or p1.field[4].cant_be_targeted_by_hero_powers) else 0,
            "myfield4effects_aura": 1 if 4 < len(p1.field) and p1.field[4].aura else 0,
            "myfield4effects_deathrattle": 1 if 4 < len(p1.field) and p1.field[4].type!=5 and p1.field[4].has_deathrattle else 0,
            "myfield4effects_frozen": 1 if 4 < len(p1.field) and p1.field[4].type!=5 and p1.field[4].type != 7  and p1.field[4].frozen else 0,
            "myfield4effects_silenced": 1 if 4 < len(p1.field) and p1.field[4].type != 5 and p1.field[4].type != 7 and p1.field[4].silenced else 0,
            "myfield5effects_windfury": 1 if 5 < len(p1.field) and p1.field[5].windfury else 0,
            "myfield5effects_divineshield": 1 if 5 < len(p1.field) and p1.field[5].type != 5 and p1.field[5].type != 7 and p1.field[5].divine_shield else 0,
            "myfield5effects_charge": 1 if 5 < len(p1.field) and p1.field[5].type!=5 and p1.field[5].type != 7 and p1.field[5].charge else 0,
            "myfield5effects_taunt": 1 if 5 < len(p1.field) and p1.field[5].type!=5 and p1.field[5].type != 7 and p1.field[5].taunt else 0,
            "myfield5effects_stealth": 1 if 5 < len(p1.field) and p1.field[5].type!=5 and p1.field[5].type != 7 and p1.field[5].stealthed else 0,
            "myfield5effects_poisonous": 1 if 5 < len(p1.field) and p1.field[5].type!=5 and p1.field[5].type != 7 and p1.field[5].poisonous else 0,
            "myfield5effects_cantbetargeted": 1 if 5 < len(p1.field) and p1.field[5].type != 5 and p1.field[5].type != 7 and (p1.field[5].cant_be_targeted_by_abilities or p1.field[5].cant_be_targeted_by_hero_powers) else 0,
            "myfield5effects_aura": 1 if 5 < len(p1.field) and p1.field[5].aura else 0,
            "myfield5effects_deathrattle": 1 if 5 < len(p1.field) and p1.field[5].type!=5 and p1.field[5].has_deathrattle else 0,
            "myfield5effects_frozen": 1 if 5 < len(p1.field) and p1.field[5].type!=5 and p1.field[5].type != 7 and p1.field[5].frozen else 0,
            "myfield5effects_silenced": 1 if 5 < len(p1.field) and p1.field[5].type != 5 and p1.field[5].type != 7 and p1.field[5].silenced else 0,
            "myfield6effects_windfury": 1 if 6 < len(p1.field) and p1.field[6].windfury else 0,
            "myfield6effects_divineshield": 1 if 6 < len(p1.field) and p1.field[6].type != 5 and p1.field[6].type != 7 and p1.field[6].divine_shield else 0,
            "myfield6effects_charge": 1 if 6 < len(p1.field) and p1.field[6].type!=5 and p1.field[6].type != 7 and p1.field[6].charge else 0,
            "myfield6effects_taunt": 1 if 6 < len(p1.field) and p1.field[6].type!=5 and p1.field[6].type != 7 and p1.field[6].taunt else 0,
            "myfield6effects_stealth": 1 if 6 < len(p1.field) and p1.field[6].type!=5 and p1.field[6].type != 7 and p1.field[6].stealthed else 0,
            "myfield6effects_poisonous": 1 if 6 < len(p1.field) and p1.field[6].type != 5 and p1.field[6].type != 7 and p1.field[6].poisonous else 0,
            "myfield6effects_cantbetargeted": 1 if 6 < len(p1.field) and p1.field[6].type!=5 and p1.field[6].type != 7 and (p1.field[6].cant_be_targeted_by_abilities or p1.field[6].cant_be_targeted_by_hero_powers) else 0,
            "myfield6effects_aura": 1 if 6 < len(p1.field) and p1.field[6].aura else 0,
            "myfield6effects_deathrattle": 1 if 6 < len(p1.field) and p1.field[6].type!=5 and p1.field[6].has_deathrattle else 0,
            "myfield6effects_frozen": 1 if 6 < len(p1.field) and p1.field[6].type!=5 and p1.field[6].type != 7 and p1.field[6].frozen else 0,
            "myfield6effects_silenced": 1 if 6 < len(p1.field) and p1.field[6].type != 5 and p1.field[6].type != 7 and p1.field[6].silenced else 0,
            "oppfield0effects_windfury": 1 if 0 < len(p2.field) and p2.field[0].windfury else 0,
            "oppfield0effects_divineshield": 1 if 0 < len(p2.field) and p2.field[0].type!=5 and p2.field[0].type!=7 and p2.field[0].divine_shield else 0,
            "oppfield0effects_charge": 1 if 0 < len(p2.field) and p2.field[0].type != 5 and p2.field[0].type != 7 and p2.field[0].charge else 0,
            "oppfield0effects_taunt": 1 if 0 < len(p2.field) and p2.field[0].type!=5 and p2.field[0].type!=7 and p2.field[0].taunt else 0,
            "oppfield0effects_stealth": 1 if 0 < len(p2.field) and p2.field[0].type!=5 and p2.field[0].type!=7 and p2.field[0].stealthed else 0,
            "oppfield0effects_poisonous": 1 if 0 < len(p2.field) and p2.field[0].type!=5 and p2.field[0].type!=7 and p2.field[0].poisonous else 0,
            "oppfield0effects_cantbetargeted": 1 if 0 < len(p2.field) and p2.field[0].type != 5 and p2.field[0].type != 7 and (p2.field[0].cant_be_targeted_by_abilities or p2.field[0].cant_be_targeted_by_hero_powers) else 0,
            "oppfield0effects_aura": 1 if 0 < len(p2.field) and p2.field[0].aura else 0,
            "oppfield0effects_deathrattle": 1 if 0 < len(p2.field) and p2.field[0].type != 5 and p2.field[0].type != 7 and p2.field[0].has_deathrattle else 0,
            "oppfield0effects_frozen": 1 if 0 < len(p2.field) and p2.field[0].type!=5 and p2.field[0].type!=7 and p2.field[0].frozen else 0,
            "oppfield0effects_silenced": 1 if 0 < len(p2.field) and p2.field[0].type!=5 and p2.field[0].type!=7 and p2.field[0].silenced else 0,
            "oppfield1effects_windfury": 1 if 1 < len(p2.field) and p2.field[1].windfury else 0,
            "oppfield1effects_divineshield": 1 if 1 < len(p2.field) and p2.field[1].type!=5 and p2.field[1].type!=7 and p2.field[1].divine_shield else 0,
            "oppfield1effects_charge": 1 if 1 < len(p2.field) and p2.field[1].type!=5 and p2.field[1].type!=7 and p2.field[1].charge else 0,
            "oppfield1effects_taunt": 1 if 1 < len(p2.field) and p2.field[1].type!=5 and p2.field[1].type!=7 and p2.field[1].taunt else 0,
            "oppfield1effects_stealth": 1 if 1 < len(p2.field) and p2.field[1].type!=5 and p2.field[1].type!=7 and p2.field[1].stealthed else 0,
            "oppfield1effects_poisonous": 1 if 1 < len(p2.field) and p2.field[1].type!=5 and p2.field[1].type!=7 and p2.field[1].poisonous else 0,
            "oppfield1effects_cantbetargeted": 1 if 1 < len(p2.field) and p2.field[1].type != 5 and p2.field[1].type != 7 and (p2.field[1].cant_be_targeted_by_abilities or p2.field[1].cant_be_targeted_by_hero_powers) else 0,
            "oppfield1effects_aura": 1 if 1 < len(p2.field) and p2.field[1].aura else 0,
            "oppfield1effects_deathrattle": 1 if 1 < len(p2.field) and p2.field[1].type!=5 and p2.field[1].has_deathrattle else 0,
            "oppfield1effects_frozen": 1 if 1 < len(p2.field) and p2.field[1].type!=5 and p2.field[1].type!=7 and p2.field[1].frozen else 0,
            "oppfield1effects_silenced": 1 if 1 < len(p2.field) and p2.field[1].type != 5 and p2.field[1].type != 7 and p2.field[1].silenced else 0,
            "oppfield2effects_windfury": 1 if 2 < len(p2.field) and p2.field[2].windfury else 0,
            "oppfield2effects_divineshield": 1 if 2 < len(p2.field) and p2.field[2].type!=5 and p2.field[2].type!=7 and p2.field[2].divine_shield else 0,
            "oppfield2effects_charge": 1 if 2 < len(p2.field) and p2.field[2].type!=5 and p2.field[2].type!=7 and p2.field[2].charge else 0,
            "oppfield2effects_taunt": 1 if 2 < len(p2.field) and p2.field[2].type!=5 and p2.field[2].type!=7 and p2.field[2].taunt else 0,
            "oppfield2effects_stealth": 1 if 2 < len(p2.field) and p2.field[2].type!=5 and p2.field[2].type!=7 and p2.field[2].stealthed else 0,
            "oppfield2effects_poisonous": 1 if 2 < len(p2.field) and p2.field[2].type != 5 and p2.field[2].type != 7 and p2.field[2].poisonous else 0,
            "oppfield2effects_cantbetargeted": 1 if 2 < len(p2.field) and p2.field[2].type!=5 and (p2.field[2].cant_be_targeted_by_abilities or p2.field[2].cant_be_targeted_by_hero_powers) else 0,
            "oppfield2effects_aura": 1 if 2 < len(p2.field) and p2.field[2].aura else 0,
            "oppfield2effects_deathrattle": 1 if 2 < len(p2.field) and p2.field[2].type!=5 and p2.field[2].has_deathrattle else 0,
            "oppfield2effects_frozen": 1 if 2 < len(p2.field) and p2.field[2].type!=5 and p2.field[2].type!=7 and p2.field[2].frozen else 0,
            "oppfield2effects_silenced": 1 if 2 < len(p2.field) and p2.field[2].type != 5 and p2.field[2].type != 7 and p2.field[2].silenced else 0,
            "oppfield3effects_windfury": 1 if 3 < len(p2.field) and p2.field[3].windfury else 0,
            "oppfield3effects_divineshield": 1 if 3 < len(p2.field) and p2.field[3].type!=5 and p2.field[3].type!=7 and p2.field[3].divine_shield else 0,
            "oppfield3effects_charge": 1 if 3 < len(p2.field) and p2.field[3].type!=5 and p2.field[3].type!=7 and p2.field[3].charge else 0,
            "oppfield3effects_taunt": 1 if 3 < len(p2.field) and p2.field[3].type!=5 and p2.field[3].type!=7 and p2.field[3].taunt else 0,
            "oppfield3effects_stealth": 1 if 3 < len(p2.field) and p2.field[3].type!=5 and p2.field[3].type!=7 and p2.field[3].stealthed else 0,
            "oppfield3effects_poisonous": 1 if 3 < len(p2.field) and p2.field[3].type!=5 and p2.field[3].type!=7 and p2.field[3].poisonous else 0,
            "oppfield3effects_cantbetargeted": 1 if 3 < len(p2.field) and p2.field[3].type!=5 and p2.field[3].type!=7 and (p2.field[3].cant_be_targeted_by_abilities or p2.field[3].cant_be_targeted_by_hero_powers) else 0,
            "oppfield3effects_aura": 1 if 3 < len(p2.field) and p2.field[3].aura else 0,
            "oppfield3effects_deathrattle": 1 if 3 < len(p2.field) and p2.field[3].type!=5 and p2.field[3].has_deathrattle else 0,
            "oppfield3effects_frozen": 1 if 3 < len(p2.field) and p2.field[3].type!=5 and p2.field[3].type!=7 and p2.field[3].frozen else 0,
            "oppfield3effects_silenced": 1 if 3 < len(p2.field) and p2.field[3].type != 5 and p2.field[3].type != 7 and p2.field[3].silenced else 0,
            "oppfield4effects_windfury": 1 if 4 < len(p2.field) and p2.field[4].windfury else 0,
            "oppfield4effects_divineshield": 1 if 4 < len(p2.field) and p2.field[4].type!=5 and p2.field[4].type!=7 and p2.field[4].divine_shield else 0,
            "oppfield4effects_charge": 1 if 4 < len(p2.field) and p2.field[4].type!=5 and p2.field[4].type!=7 and p2.field[4].charge else 0,
            "oppfield4effects_taunt": 1 if 4 < len(p2.field) and p2.field[4].type!=5 and p2.field[4].type!=7 and p2.field[4].taunt else 0,
            "oppfield4effects_stealth": 1 if 4 < len(p2.field) and p2.field[4].type!=5 and p2.field[4].type!=7 and p2.field[4].stealthed else 0,
            "oppfield4effects_poisonous": 1 if 4 < len(p2.field) and p2.field[4].type!=5 and p2.field[4].type!=7 and p2.field[4].poisonous else 0,
            "oppfield4effects_cantbetargeted": 1 if 4 < len(p2.field) and p2.field[4].type!=5 and (p2.field[4].cant_be_targeted_by_abilities or p2.field[4].cant_be_targeted_by_hero_powers) else 0,
            "oppfield4effects_aura": 1 if 4 < len(p2.field) and p2.field[4].aura else 0,
            "oppfield4effects_deathrattle": 1 if 4 < len(p2.field) and p2.field[4].type!=5 and p2.field[4].has_deathrattle else 0,
            "oppfield4effects_frozen": 1 if 4 < len(p2.field) and p2.field[4].type!=5 and p2.field[4].type!=7 and p2.field[4].frozen else 0,
            "oppfield4effects_silenced": 1 if 4 < len(p2.field) and p2.field[4].type != 5 and p2.field[4].type != 7 and p2.field[4].silenced else 0,
            "oppfield5effects_windfury": 1 if 5 < len(p2.field) and p2.field[5].windfury else 0,
            "oppfield5effects_divineshield": 1 if 5 < len(p2.field) and p2.field[5].type!=5 and p2.field[5].type!=7 and p2.field[5].divine_shield else 0,
            "oppfield5effects_charge": 1 if 5 < len(p2.field) and p2.field[5].type!=5 and p2.field[5].type!=7 and p2.field[5].charge else 0,
            "oppfield5effects_taunt": 1 if 5 < len(p2.field) and p2.field[5].type!=5 and p2.field[5].type!=7 and p2.field[5].taunt else 0,
            "oppfield5effects_stealth": 1 if 5 < len(p2.field) and p2.field[5].type!=5 and p2.field[5].type!=7 and p2.field[5].stealthed else 0,
            "oppfield5effects_poisonous": 1 if 5 < len(p2.field) and p2.field[5].type != 5 and p2.field[5].type != 7 and p2.field[5].poisonous else 0,
            "oppfield5effects_cantbetargeted": 1 if 5 < len(p2.field) and p2.field[5].type != 5 and p2.field[5].type != 7 and (p2.field[5].cant_be_targeted_by_abilities or p2.field[5].cant_be_targeted_by_hero_powers) else 0,
            "oppfield5effects_aura": 1 if 5 < len(p2.field) and p2.field[5].aura else 0,
            "oppfield5effects_deathrattle": 1 if 5 < len(p2.field) and p2.field[5].type!=5 and p2.field[5].has_deathrattle else 0,
            "oppfield5effects_frozen": 1 if 5 < len(p2.field) and p2.field[5].type!=5 and p2.field[5].type!=7 and p2.field[5].frozen else 0,
            "oppfield5effects_silenced": 1 if 5 < len(p2.field) and p2.field[5].type!=5 and p2.field[5].type!=7 and p2.field[5].silenced else 0,
            "oppfield6effects_windfury": 1 if 6 < len(p2.field) and p2.field[6].windfury else 0,
            "oppfield6effects_divineshield": 1 if 6 < len(p2.field) and p2.field[6].type!=5 and p2.field[6].type!=7 and p2.field[6].divine_shield else 0,
            "oppfield6effects_charge": 1 if 6 < len(p2.field) and p2.field[6].type!=5 and p2.field[6].type!=7 and p2.field[6].charge else 0,
            "oppfield6effects_taunt": 1 if 6 < len(p2.field) and p2.field[6].type!=5 and p2.field[6].type!=7 and p2.field[6].taunt else 0,
            "oppfield6effects_stealth": 1 if 6 < len(p2.field) and p2.field[6].type!=5 and p2.field[6].type!=7 and p2.field[6].stealthed else 0,
            "oppfield6effects_poisonous": 1 if 6 < len(p2.field) and p2.field[6].type!=5 and p2.field[6].type!=7 and p2.field[6].poisonous else 0,
            "oppfield6effects_cantbetargeted": 1 if 6 < len(p2.field) and p2.field[6].type != 5 and p2.field[6].type != 7 and (p2.field[6].cant_be_targeted_by_abilities or p2.field[6].cant_be_targeted_by_hero_powers) else 0,
            "oppfield6effects_aura": 1 if 6 < len(p2.field) and p2.field[6].aura else 0,
            "oppfield6effects_deathrattle": 1 if 6 < len(p2.field) and p2.field[6].type!=5 and p2.field[6].has_deathrattle else 0,
            "oppfield6effects_frozen": 1 if 6 < len(p2.field) and p2.field[6].type!=5 and p2.field[6].type!=7 and p2.field[6].frozen else 0,
            "oppfield6effects_silenced": 1 if 6 < len(p2.field) and p2.field[6].type != 5 and p2.field[6].type != 7 and p2.field[6].silenced else 0,
            "myfield0canattack":  1 if 0 < len(p1.field) and p1.field[0].can_attack() else 0,
            "myfield1canattack": 1 if 1 < len(p1.field) and p1.field[1].can_attack() else 0,
            "myfield2canattack": 1 if 2 < len(p1.field) and p1.field[2].can_attack() else 0,
            "myfield3canattack": 1 if 3 < len(p1.field) and p1.field[3].can_attack() else 0,
            "myfield4canattack": 1 if 4 < len(p1.field) and p1.field[4].can_attack() else 0,
            "myfield5canattack": 1 if 5 < len(p1.field) and p1.field[5].can_attack() else 0,
            "myfield6canattack": 1 if 6 < len(p1.field) and p1.field[6].can_attack() else 0,
            "myherocanattack": 1 if p1.hero.can_attack() else 0
        }
        return s
