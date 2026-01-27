import pygame
import numpy as np
import math, random, os, json
from pylsl import StreamInfo, StreamOutlet


with open('move_mode.json', encoding='utf-8') as file:
    data_config = json.load(file)

# set up pinned window on second monitor
def pinned_window(data_config):
    x = data_config['window_x']
    y = data_config['window_y']
    os.environ['SDL_VIDEO_WINDOW_POS'] = f'{x},{y}'
    os.environ['SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS'] = '0'

pygame.init()

pinned_window(data_config)


screen = pygame.display.set_mode(size=(0, 0), flags=pygame.FULLSCREEN)

width, height = screen.get_width(), screen.get_height()

n_cols = data_config['num_cols'] # 11, 5
n_rows = data_config['num_rows'] # 4, 9

w, h = width // n_cols, height // n_rows


alphabet = data_config['alphabet']

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

def send(send_text):
    log.write(send_text + '\n')
    outlet.push_sample([send_text])

info = StreamInfo(name = 'annotations',
                  type = 'Events',
                  channel_count=1,
                  nominal_srate=0,
                  channel_format='string',
                  source_id='my_marker_stream')
outlet = StreamOutlet(info)

pygame.display.set_caption('Experiment')
clock = pygame.time.Clock()

FPS = data_config['FPS']
font_name = data_config['font_name']
font_size = data_config['font_size']
background = data_config['background']
letter_foreground = data_config['letter_foreground']
amplitude_x_scale = data_config['amplitude_x_scale']
amplitude_y_scale = data_config['amplitude_y_scale']
text = data_config["text"]
t_pause = data_config["t_pause"] / sec_in_msec
t_cont = data_config["t_cont"] / sec_in_msec
t_show = data_config["t_show"] / sec_in_msec
start_fg = data_config["start_fg"]
end_fg = data_config["end_fg"]
is_random_delay = data_config["is_random_delay"]

font = pygame.font.SysFont(name=font_name, size=font_size, bold=True)

cells = {}

for id, char in enumerate(alphabet):
    letter = font.render(char, True, letter_foreground)
    cells[char] = {
        'id': id,
        'letter_prime': letter,
        'letter_tmp': letter,
        'amplitude_x': (w / 2) * amplitude_x_scale,
        'amplitude_y': (h / 2) * amplitude_y_scale,
        'frequency': set_freq(),
        't1': set_t1(is_random_delay),
        't2': set_t2(is_random_delay),
        'start_t': 0,
        'moving': False,
        'stop': False,
        'previous_speed': 0
    }

running = True
start_experiment = False

cur_simbol_idx = 0
t_cur = None

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
                    send('start_experiment')
                
                if event.key == pygame.K_e:
                    start_experiment = False
                    send('end_experiment')

                if event.key == pygame.K_SPACE:
                    send('pressed_space')
        
        screen.fill(background)
        
        for char, params in cells.items():
            j, i = params['id'] // n_cols, params['id'] % n_cols
            
            if start_experiment:
                
                t = pygame.time.get_ticks() - t0
                
                try:
                    speed = speed_func(t - params['start_t'], params['frequency'],
                                       params['t1'], params['t2'])
                    params['previous_speed'] = speed

                    if speed != 0 and not params['moving']:
                        params['moving'] = True
                        send(f'{char}_start_{get_move_info(speed)}')
                    
                    if speed == 0 and params['previous_speed'] == 0 and \
                        not params['stop'] and params['moving']:
                        params['stop'] = True
                        send(f'{char}_end')
                
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
                
                # z coord moving
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
            

            if char == text[cur_simbol_idx] and start_experiment:

                if t_cur is None:
                    t_cur = pygame.time.get_ticks()
                    send(f"{char}_show_start")

                elif t_cur < pygame.time.get_ticks() <= t_cur + t_cont:
                    params['letter_tmp'] = pygame.transform.smoothscale(
                        font.render(char, True, start_fg), params['letter_tmp'].get_size())
                
                elif t_cur + t_cont < pygame.time.get_ticks() <= t_cur + t_show - t_cont:
                    pass
                
                elif t_cur + t_show - t_cont < pygame.time.get_ticks() <= t_cur + t_show:
                    params['letter_tmp'] = pygame.transform.smoothscale(
                        font.render(char, True, end_fg), params['letter_tmp'].get_size())
                
                elif t_cur + t_show < pygame.time.get_ticks() <= t_cur + t_show + t_pause:
                    pass
                
                elif cur_simbol_idx < len(text) - 1:
                    send(f"{char}_show_end")   
                    cur_simbol_idx += 1
                    t_cur = None



            screen.blit(params['letter_tmp'],
                        (i * w + w / 2 - params['letter_tmp'].get_width() / 2 + dx,
                        j * h + h / 2 - params['letter_tmp'].get_height() / 2 + dy))
        
        pygame.display.flip()
        dt = clock.tick(FPS)

pygame.quit()
