# coding:utf-8
# http://neuro-educator.com/rl1/

import numpy as np
from sequence import *
from hand_motion import *
from dummy_evaluator import *
from neural_network import *
from datetime import datetime

import sys

select_episode = 10
epsilon = 0.3# * (1 / (episode + 1))

def normalization(array, val_max, val_min):
    x_max = np.max(array)
    x_min = np.min(array)
    a = (val_max - val_min)/(x_max - x_min)
    b = -a*x_max + val_max
    return (a, b)

def inv_normalization(a, b, norm_q):
    return (norm_q - b)/a

def volts(q_teacher, q_k, T=1):
    exp_1=np.sum(np.exp(q_teacher/T))
    exp_2=np.exp(q_k/T)
    return exp_2/exp_1

def select_teach(input_array, q_teacher,episode,num=select_episode):
    index_array = np.argsort(q_teacher)[::-1]
    selected_input = input_array[index_array]
    selected_output = np.sort(q_teacher)[::-1]

    return selected_input[0,:num,:], selected_output[:,:num]

#5 [4] start main function. set parameters
argvs = sys.argv
target_type = argvs[1]
target_direct = argvs[2]
mode = argvs[3]

print('1',datetime.now())
t_window = 30  #number of time window
num_episodes = 200  #number of all trials

type_face = 5
type_ir = 1
type_action = 1

num_face = 100 #%
num_ir = 100 #5mm
num_action = 60 #%:pwm

gamma = 0.9
alpha = 0.5

epsilon = 0.1
mu = 0.9
epoch = 1000

val_max = 0.8
val_min = 0.2


# [5] main tourine
state = np.zeros((type_face+type_ir,t_window))
state_mean = np.zeros((type_face+type_ir,num_episodes))
action = np.zeros((1,num_episodes))
reward = np.zeros(num_episodes)

print('3',datetime.now())
state[:,0] = np.array([100,0,0,0,0,30])
action[:,0] = np.random.uniform(0,60)#TODO not enough

possible_a = np.linspace(0,60,100)

print('4',datetime.now())
# set qfunction as nn
input_size = type_face + type_ir + type_action
output_size = 1
hidden_size = (input_size + output_size )/3

q_teacher = np.zeros((output_size,num_episodes))

print('5',datetime.now())
Q_func = Neural(input_size, hidden_size, output_size)
first_iteacher = np.random.uniform(low=0,high=1,size=(input_size,2))
first_oteacher = np.random.uniform(low=0,high=1,size=(output_size,2))

#q_teacher[:,0]= first_oteacher[:,0]

print('6',datetime.now())

Q_func.train(first_iteacher.T,first_oteacher.T,epsilon, mu, epoch)

print('7',datetime.now())
rewed= 0
acted = action[:,0]

for episode in range(num_episodes-1):  #repeat for number of trials
    acted = action[:,episode] = acted
    print('epi',episode,datetime.now(),'act',acted,'rew',rewed)

    #mode = 'heuristic'
    mode = argvs[3]

    if episode == 0:
        state[:,0] = np.array([100,0,0,0,0,30])
    else:
        state[:,0] = before_state

    for t in range(1,t_window):  #roup for 1 time window
        state[:,t] = np.hstack((get_face(action[:,episode],argvs[1],argvs[2],t,t_window),get_ir(state[type_face,t-1])))

    ### calcurate s_{t+1}
    state_mean[:,episode+1]=seq2feature(state)
    #print('state_mean[:,episode]',state_mean[:,episode].T,state_mean)

    ### calcurate r_{t}
    reward[episode] = calc_reward(state/num_face, state/num_face, t_window, mode)
    print('reward',reward[episode])

    p_array= np.zeros((input_size,1))
    possible_q = np.zeros(num_action)

    ### calcurate a_{t+1} based on s_{t+1}
    for i in range(num_action):
        #print('possible_a[i]/num_action',possible_a[i]/num_action)
        p_array[:,0]=np.hstack((state_mean[:,episode+1]/num_face,possible_a[i]/num_action))
        C, possible_q[i]=Q_func.predict(p_array.T)
        #print('possible_a, possible_q',possible_a[i],possible_q[i])

    #epsilon = volts(q_teacher,np.argmax(possible_q))
    print('epsilon',epsilon)
    if epsilon >= np.random.uniform(0, 1):
        print('max')
        #next_action = np.argmax(q_table[next_state])
        action[:,episode+1]=np.argmax(possible_q)
    else:
        action[:,episode+1]=np.random.uniform(0,60)#TODO not enough
    #print('possible_q',possible_q)
    print('action',action[:,episode+1])

    ### update q-teacher(as q-function)
    ## calculate argmaxq_{t+1}
    next_q=np.max(possible_q)

    ## calculate q_{t}
    p_array[:,0]=np.hstack((state_mean[:,episode]/num_face,action[:,episode]/num_action))
    C, present_q = Q_func.predict(p_array.T)
    #present_q=inv_normalization(a, b, present_q)

    ## calcurate updated q_{t}
    q_teacher[:,episode] = present_q[0,0] + alpha*(reward[episode]+gamma*(next_q-present_q[0,0]))
    #q_teacher[:,episode] = present_q + alpha*(reward[episode]+gamma*(next_q-present_q[0,0]))
    print('q_teacher',q_teacher[:,episode])

    ## update q_function
    input_array = np.zeros((input_size,episode))
    input_array = np.hstack((((state_mean[:,:episode])/num_face).T,(action[:,:episode]/num_action).T))

    if episode>select_episode:
        selected_input, selected_teacher = select_teach(input_array,q_teacher[:,:episode],episode)
    else:
        selected_input = input_array
        selected_teacher = q_teacher[:,:episode]

    Q_func.train(selected_input,selected_teacher.T, epsilon, mu, epoch)
    #print('input',input_array)

    before_state = state[:,t_window-1]
    acted = action[:,episode+1]
    rewed = reward[episode]

np.savetxt('action_pwm.csv', action[0,:], fmt="%.0f", delimiter=",")
np.savetxt('reward_seq.csv', reward, fmt="%.5f",delimiter=",")
np.savetxt('situation.csv', state_mean.T,fmt="%.2f", delimiter=",")
