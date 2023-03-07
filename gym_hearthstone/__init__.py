import logging
from gymnasium.envs.registration import register

logger = logging.getLogger(__name__)

# register(
#     id='Hearthstone-v0',
#     entry_point='gym_hearthstone.envs:HearthstoneEnv',
# )

register(
    id='Hearthstone-v1',
    entry_point='gym_hearthstone.envs:HearthstoneUnnestedEnv',
)
