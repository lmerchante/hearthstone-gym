from typing import Dict, Tuple, Union
import torch as th
from torch.nn import functional as F

from gymnasium import spaces
from hearthstone.enums import CardClass,CardSet, CardType
from fireplace import cards
from fireplace.utils import get_script_definition


import re
import string


def get_implemented_cards():
    return implemented_cards

def get_obs_space():
    return obs_space

def get_setup_dict():
    return setup_dict


# ==========================================================================
# Create Implemented cards & Setup dict
# ==========================================================================

GREEN = "\033[92m"
RED = "\033[91m"
ENDC = "\033[0m"
PREFIXES = {
    GREEN: "Implemented",
    RED: "Not implemented",
}
counter = 0
implemented_cards = []
unimplemented_cards = []
setup_dict = {
    CardClass.DEATHKNIGHT: [],
    CardClass.DRUID: [],
    CardClass.HUNTER: [],
    CardClass.MAGE: [],
    CardClass.PALADIN: [],
    CardClass.PRIEST: [],
    CardClass.ROGUE: [],
    CardClass.SHAMAN: [],
    CardClass.WARLOCK: [],
    CardClass.WARRIOR: [],
    CardClass.DEMONHUNTER: [],
    CardClass.NEUTRAL: []
}

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

# ==========================================================================
# Clean description of cards
# ==========================================================================
cards.db.initialize()
for id in sorted(cards.db):
    card = cards.db[id]
    ret = card.description
    # elimina texto en cursiva había algunas etiquetas con </I>
    ret = re.sub("<i>.+</i>", "", ret, flags=re.IGNORECASE)
    #elimina texto en negrita, cuando aparecían 2 secuencias en negrita no eliminaba todas
    ret = re.sub(r"<\/?b[^>]*>", "", ret)
    # elimina todas las palabras de SOLVED_KEYWORDS
    ret = re.sub("(" + "|".join(SOLVED_KEYWORDS) + ")", "", ret)
    # elimina otras etiquetas HTML, pero despues de corregir lo anterior, no aparecen más
    ret = re.sub("<[^>]*>", "", ret)

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

    # Mira si la carta tiene un script definition
    carddef = get_script_definition(id)
    # https://github.com/jleclanche/fireplace/blob/58c5c60dc4502956d1a7a12c616c9b6201598edb/fireplace/utils.py#L103

    if carddef:
        implemented = True

    # Kazakus sometimes ends up in an infinite loop, so we will treat it as not implemented
    # Card id -> CFM_621 & BT_203
    if card.id == "CFM_621":
        implemented = False
    if card.id == "BT_203":
        implemented = False
    if card.id == "NEW1_038":
        implemented = False

    color = GREEN if implemented else RED
    name = color + "%s: %s" % (PREFIXES[color], card.name) + ENDC

    if implemented:
        implemented_cards.append(card.id)
        # fill_setup_list
        if (card.collectible and card.type != CardType.HERO):
            # print(card.card_class)
            setup_dict[card.card_class].append(card)
        else:
            counter += 1

    else:
        unimplemented_cards.append(card.id)

IMPLEMENTED_CARDS = len(implemented_cards)
UNIMPLEMENTED_CARDS = len(unimplemented_cards)

print("IMPLEMENTED CARDS: "+str(IMPLEMENTED_CARDS))
print("UNIMPLEMENTED CARDS: "+str(UNIMPLEMENTED_CARDS))
print("Implemented but Uncollectible: " + str(counter))

for key in setup_dict:
    print(str(key) + " amount of cards is: " + str(len(setup_dict[key])))

# ==========================================================================
# Get Observations
# ==========================================================================

def get_observations(p1, p2):
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







# ==========================================================================
# Define observation space
# ==========================================================================

obs_space = spaces.Dict({
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

#Function that is giving an error in stable Baselines Dqn
def preprocess_obs(
    obs: th.Tensor,
    observation_space: spaces.Space = obs_space,
    normalize_images: bool = True,
) -> Union[th.Tensor, Dict[str, th.Tensor]]:
    """
    Preprocess observation to be to a neural network.
    For images, it normalizes the values by dividing them by 255 (to have values in [0, 1])
    For discrete observations, it create a one hot vector.

    :param obs: Observation
    :param observation_space:
    :param normalize_images: Whether to normalize images or not
        (True by default)
    :return:
    """

    if isinstance(observation_space, spaces.Discrete):
        # One hot encoding and convert to float to avoid errors
        tmp=th.tensor(obs)
        if tmp==observation_space.n:
            tmp=tmp-1
        return F.one_hot(tmp, num_classes=observation_space.n).float()


    elif isinstance(observation_space, spaces.Dict):
        # Do not modify by reference the original observation
        assert isinstance(obs, Dict), f"Expected dict, got {type(obs)}"
        preprocessed_obs = {}
        for key, _obs in obs.items():
            preprocessed_obs[key] = preprocess_obs(_obs, observation_space[key])
        return preprocessed_obs

    else:
        raise NotImplementedError(f"Preprocessing not implemented for {observation_space}")

