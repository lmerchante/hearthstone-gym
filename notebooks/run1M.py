
import os
import time
import sys #-- lo he necesitado para importar el paquete
sys.path.append('..')
import gymnasium as gym
import gym_hearthstone
from stable_baselines3 import DQN


import time
import os
print(os.getpid())

env = gym.make('Hearthstone-v1', action_type = "type", reward_mode = "complex", decks = "classic", opponent_model = "dqn_100k")

steps = 10000
reply_batch_size=1
run = "jesus_agent_opponent"
env.reset_stats()
start = time.time()
env.reset()

model = DQN("MultiInputPolicy", env, batch_size=reply_batch_size, policy_kwargs={"normalize_images":False} ,verbose=0)
model.learn(total_timesteps=steps, log_interval=4)

end = time.time()
env.display_stats()
print("Avg steps per game: " + str(steps / env.curr_episode))
print("Total running time: {:.2f} and running time per game: {:.2f}".format(end-start, (end-start) / env.curr_episode) )

## Calcular estadísticas
# ======================

env.display_stats()

total_time = end-start

if(env.curr_episode > 0):
    avg_time = (end-start) / env.curr_episode
    avg_steps = steps / env.curr_episode
else:
    avg_time = (end-start) 
    avg_steps = steps 


if (env.wins + env.losses > 0):
    win_rate = env.wins / (env.wins + env.losses)
else:
    win_rate = 0

print("Avg steps per game: " + str(avg_steps))
print("Total running time: {:.2f} and running time per game: {:.2f}".format(total_time, avg_time) )

## Crear ficheros
file_name = str(env.action_type) + "__" + str(env.reward_mode) + "__" + str(steps) + "__" + str(run)

# METRICS
data_file = open('./metrics/' + file_name + '.txt', 'w')
data_file.write("Games, AvgStepsGame, TotalTime, AvgTimeGame, TotalReward, WinRate \n")
data_file.write("{},{:.2f},{:.2f},{:.2f},{:.2f},{:.2f}".format(env.curr_episode, avg_steps, total_time, avg_time, env.total_reward, win_rate))
data_file.close()

# REWARD DATA
data_file = open('./reward_data/' + file_name + '.csv', 'w')
data_file.write("Games, Reward \n")
for key in env.reward_dict:
    data_file.write("{},{:.2f} \n".format(key, env.reward_dict[key]))
data_file.close()

#model.save("./dqn_models/" + file_name + "_dqn")
#env.close()


model.save("dqn_10k_ag_opp")

env.close()