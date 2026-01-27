import pygame
import numpy as np
import math, random, os, json
from pylsl import StreamInfo, StreamOutlet


with open('move_mode.json', encoding='utf-8') as file:
    data_config = json.load(file)

# set up pinned window on second monitor
x = data_config['window_x']
y = data_config['window_y']
os.environ['SDL_VIDEO_WINDOW_POS'] = f'{x},{y}'
os.environ['SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS'] = '0'

pygame.init()

flags = pygame.FULLSCREEN
screen = pygame.display.set_mode(size=(0, 0), flags=flags)

width = screen.get_width()
height = screen.get_height()

n_cols = data_config['num_cols'] # 11, 5
n_rows = data_config['num_rows'] # 4, 9

alphabet = data_config['alphabet'].replace('\n', '')

w, h = width // n_cols, height // n_rows

sec_in_msec = 1e-3

freq_mean = data_config['frequency_mean']
freq_std = data_config['frequency_std']

delay_t1_scale = data_config['delay_t1_scale']
delay_t2_scale = data_config['delay_t2_scale']

def set_t1(is_random=True):
    if is_random:
        return random.random() * delay_t1_scale
    return delay_t1_scale

def set_t2(is_random=True):
    if is_random:
        return random.random() * delay_t2_scale
    return delay_t2_scale

def set_freq():
    return abs(np.random.normal(0, freq_std)) + freq_mean

def speed_func(t, freq, t1, t2):
    if freq <= 0:
        raise ValueError('freq must be positive')
    if t1 < 0:
        raise ValueError('t1 must be non negative')
    if t2 < 0:
        raise ValueError('t2 must be non negative')
    
    if t1 / sec_in_msec <= t <= (t1 + 1 / freq) / sec_in_msec:
        return math.sin((t - t1 / sec_in_msec) * math.tau * freq * sec_in_msec)
    elif 0 <= t < t1 / sec_in_msec or \
        (t1 + 1 / freq) / sec_in_msec < t <= (t1 + 1 / freq + t2) / sec_in_msec:
        return 0
    else:
        raise ValueError(f't must be between 0 and {(t1 + 1 / freq + t2) / sec_in_msec}')

def sign(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0

def get_move_info(speed):
    x_move = sign(speed) if data_config['x_move'] else 0
    y_move = sign(speed) if data_config['y_move'] else 0
    z_move = sign(speed) if data_config['z_move'] else 0
    return f"x: {x_move}, y: {y_move}, z: {z_move}"

info = StreamInfo(name = 'annotations',
                  type = 'Events',
                  channel_count=1,
                  nominal_srate=0,
                  channel_format='string',
                  source_id='my_marker_stream')
outlet = StreamOutlet(info)
lsl_output = data_config['lsl_output']

pygame.display.set_caption('Experiment')
clock = pygame.time.Clock()

FPS = data_config['FPS']
font_name = data_config['font_name']
font_size = data_config['font_size']
background = data_config['background']
letter_foreground = data_config['letter_foreground']
amplitude_x_scale = data_config['amplitude_x_scale']
amplitude_y_scale = data_config['amplitude_y_scale']
word = data_config["word"]
t_pause = data_config["t_pause"]
t_cont = data_config["t_cont"]
t_show = data_config["t_show"]

font = pygame.font.SysFont(name=font_name, size=font_size, bold=True)

cells = {}

for id, char in enumerate(alphabet):
    letter = font.render(char, True, letter_foreground)
    cells[char] = {
        'id': id,
        'letter_prime': letter,
        'letter_tmp': letter,
        'amplitude_x': (w / 2) * amplitude_x_scale, #random.random() * 15 + 5,
        'amplitude_y': (h / 2) * amplitude_y_scale,
        'frequency': set_freq(), #random.random() * 4.8 + 0.2,
        't1': set_t1(),
        't2': set_t2(),
        'start_t': 0,
        'moving': False,
        'stop': False,
        'previous_speed': 0
    }

running = True
start_experiment = False

cur_simbol = word[0]

with open('log.txt', 'w', encoding='utf-8') as log:

    while running:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    
                if event.key == pygame.K_s:
                    start_experiment = True
                    t0 = pygame.time.get_ticks()
                    #print('start_experiment')
                    log.write('start_experiment\n')
                    if lsl_output:
                        outlet.push_sample(['start_experiment'])
                
                if event.key == pygame.K_e:
                    start_experiment = False
                    #print('end_experiment')
                    log.write('end_experiment\n')
                    if lsl_output:
                        outlet.push_sample(['end_experiment'])
        
        screen.fill(background)
        
        for char, params in cells.items():
            j, i = params['id'] // n_cols, params['id'] % n_cols
            
            if start_experiment: # params['id'] == moving_id and start_experiment:
                
                t = pygame.time.get_ticks() - t0
                
                try:
                    speed = speed_func(t - params['start_t'], params['frequency'],
                                    params['t1'], params['t2'])
                    params['previous_speed'] = speed
                    if speed != 0 and not params['moving']:
                        params['moving'] = True
                        str_info = f'{char}_start_{get_move_info(speed)}'
                        #print(str_info)
                        log.write(str_info + '\n')
                        if lsl_output:
                            outlet.push_sample([str_info])
                    if speed == 0 and params['previous_speed'] == 0 and not params['stop'] and params['moving']:
                        params['stop'] = True
                        str_info = f'{char}_end'
                        #print(str_info)
                        log.write(str_info + '\n')
                        if lsl_output:
                            outlet.push_sample([str_info])
                
                except ValueError:
                    params['start_t'] = t
                    params['t1'] = set_t1()
                    params['t2'] = set_t2()
                    speed = speed_func(t - params['start_t'], params['frequency'],
                                       params['t1'], params['t2'])
                    params['previous_speed'] = 0
                    params['moving'] = False
                    params['stop'] = False
                
                # x coord moving
                dx = params['amplitude_x'] * speed if data_config['x_move'] else 0
                
                # y coord moving
                dy = params['amplitude_y'] * speed if data_config['y_move'] else 0
                
                # 'z' coord moving
                params['letter_tmp'] = pygame.transform.smoothscale(
                    params['letter_prime'], 
                    (
                        params['letter_prime'].get_width() * (speed + 1), 
                        params['letter_prime'].get_height() * (speed + 1)
                    )
                    ) if data_config['z_move'] else params['letter_prime']
                
            else:
                dx = 0
                dy = 0
            
            #if char == cur_simbol:
            #    old_size = params['letter_tmp'].get_size()

            screen.blit(params['letter_tmp'],
                        (i * w + w / 2 - params['letter_tmp'].get_width() / 2 + dx,
                        j * h + h / 2 - params['letter_tmp'].get_height() / 2 + dy))
        
        pygame.display.flip()
        dt = clock.tick(FPS)

pygame.quit()
