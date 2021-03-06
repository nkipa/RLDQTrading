# mainly keras model to RLDQ model, some important settings here so far
# Programming marko.rantala@pvoodoo.com
# v1.0.0.1 20190305
# 1.0.0.3  20190308 model changed 
# v1.0.1.0 20190310 Start of 
##############################
# own ad: For NinjaTrader related stuff: check https://pvoodoo.com or blog: https://pvoodoo.blogspot.com/?view=flipcard
##############################

import keras
from keras.models import Sequential
from keras.models import load_model, Model
from keras.layers import Dense, LSTM, Flatten, Input, concatenate
from keras.optimizers import Adam

import numpy as np
import random
from collections import deque
import constant

Debug=True  # or constant.Debug


class PVAgent:
  def __init__(self, time_steps, feature_count, is_eval=False, model_name=""):
    self.time_steps = time_steps  # period 
    self.feature_count = feature_count
    self.action_size = 3  # no_action, buy, sell, 1 is actually based to constant.py now, it is active GO FLAT > exit trade, maybe 4 actions needed [No action, Long, Short, Exit]
    self.memory = deque(maxlen=256)  # according some new study, no need to be high at stock data .. but try 128,256,512  (DayTrading -> short is okay)  
    self.inventory = []
    self.model_name = model_name
    self.is_eval = is_eval

    # next ones are actually quite important parameters here, try with different settings!, general guidance is available from the web
    self.gamma = 0.80   #
    self.epsilon = 1.0
    self.epsilon_min = 0.01
    self.epsilon_decay = 0.995
    self.learning_rate = 0.001   # actually a learning rate to Adam optimizer, this might be even smaller as some ..

    self.model = load_model("models/" + model_name + ".h5") if is_eval else self._model()

    
    # just a simple model first, add dropouts or batch normalization and experiment some dif shapes and sizes and activations  (tanh?, but set scaler ?)
  def _model(self):
  
  
    feature_input = Input(shape=(self.time_steps, self.feature_count), name="Market_inputs")   # 3D shape here.., actually market features, suitable directly to recurrent neural networks
    
    lstm = LSTM(32, return_sequences=True, activation="relu")(feature_input)
    flattened_features = LSTM(16, return_sequences=False, activation="relu")(lstm)  # or without that but you need to set return sequences false at previous then to get flattened shape
    
    # flattened_price=lstm
    #flattened_price = Flatten()(feature_input)  # 3D shape is/was meant to LSTMm, CONV, recurrent models,  keep time_steps short otherwise, even 1 if reasonable feature match, try those recurrent ones too!!
    
    state_input = Input(shape=(constant.PositionStateWidth,), name="Position_inputs") # 2D [Flat no more  => Long,Short,Current_PnL]  anyway to merge this , position features
 
    state = Dense(8, activation="relu")(state_input)
    #state_input = Input() what if this is not connected ?, lets try
   
   
    merged = concatenate([flattened_features, state], axis=1)   # the most simplest merged model now 
    
    #merged = Dense(units=64,  activation="relu")(merged)
    merged = Dense(units=16, activation="relu")(merged)
    
    preds = Dense(self.action_size, activation="softmax", name="Actions")(merged) #   activation linear, softmax could be used as well?
    
    model = Model(inputs=[feature_input, state_input], outputs=preds)
    #model = Model(inputs=feature_input, outputs=preds)
    
    model.compile(optimizer=Adam(lr=self.learning_rate), loss="mse")
    
    # if Debug:
        # print("Model:")
        # print(model.layers[0].input.shape.as_list())
        # print(model)
    
    return model
    
    # next is/was identical, just for info , not used any more and don't even fit to input any more,  if you prefer that way of building, but additional input will be added so previous one is easier to handle
    # model = Sequential()
    # model.add(Dense(units=64, input_shape=(self.feature_count,), activation="relu"))
    # model.add(Dense(units=8, activation="relu"))
    # model.add(Dense(self.action_size, activation="linear"))  # or use softmax 
    # model.compile(loss="mse", optimizer=Adam())

    # return model

  def act(self, state):
    if not self.is_eval and np.random.rand() <= self.epsilon:
      return random.randrange(self.action_size)
      #return np.argmax(np.random.multinomial(1, [0.6, 0.2, 0.2]))   # see the distribution, so NO action is preferred to speed up training, maybe [0.8, 0.1, 0.1] could be used as well
        # here could be some restrictions too , new model, index 0 is active -> sell to exit, back to normal distribution
      
    options = self.model.predict(state) # modified with 0
    return np.argmax(options[0])
    #return options   # or should it be options[0] to be same format

  def expReplay(self, batch_size):
    mini_batch = []
    l = len(self.memory)
    for i in range(l - batch_size + 1, l):
      mini_batch.append(self.memory.popleft())

    states0, states1, targets = [],[], []
    for state, action, reward, next_state, done in mini_batch:
      target = reward
      if not done:
        #if Debug:
        #    print("expRep: shapes: ", next_state[0].shape, next_state[1].shape)
        target = reward + self.gamma * np.amax(self.model.predict(next_state)[0])  ## simple kartpole model  next_state[0] to forget second input
        

      target_f = self.model.predict(state)  #Modif with 0
      target_f[0][action] = target

      states0.append(state[0])  # modified state, only first , market_state
      states1.append(state[1])  # position_state, added as a list 
      targets.append(target_f)

    self.model.fit([np.vstack(states0), np.vstack(states1)], [np.vstack(targets)], epochs=1, verbose=0)

    if self.epsilon > self.epsilon_min:
      self.epsilon *= self.epsilon_decay

##############################
# own ad: For NinjaTrader related stuff: check https://pvoodoo.com or blog: https://pvoodoo.blogspot.com/?view=flipcard
##############################
