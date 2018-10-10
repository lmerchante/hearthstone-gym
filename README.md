This repository contains a PIP package which is an OpenAI environment for
simulating an environment in which Hearthstone is played.


## Installation

Install the [OpenAI gym](https://gym.openai.com/docs/).

Then install this package via

```
pip install -e .
```

## Usage

```
import gym
import gym_hearthstone

env = gym.make('Hearthstone-v0')
```

See https://github.com/matthiasplappert/keras-rl/tree/master/examples for some
examples.


## The Environment

Uses Sabberstone and random decks