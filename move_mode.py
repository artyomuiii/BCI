import time
import pygame as pg
import numpy as np
import math, random, os, json
from pylsl import StreamInfo, StreamOutlet


with open('move_mode.json', encoding='utf-8') as file:
    conf = json.load(file)

# TODO: вынести все ф-ции в отдельные модули
def pinned_window(conf):
    """
    Set up pinned window on second monitor
    """
    x = conf['window_x']
    y = conf['window_y']
    os.environ['SDL_VIDEO_WINDOW_POS'] = f'{x},{y}'
    os.environ['SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS'] = '0'

pg.init()

pinned_window(conf)


screen = pg.display.set_mode(size=(0, 0), flags=pg.FULLSCREEN)

width, height = screen.get_width(), screen.get_height()

n_cols = conf['num_cols'] # 11, 5
n_rows = conf['num_rows'] # 4, 9

w, h = width // n_cols, height // n_rows


sec_in_msec = 1e-3


def set_t(delay_t_scale, is_random=True):
    if is_random:
        return random.random() * delay_t_scale
    return delay_t_scale


def set_freq(freq_mean, freq_std):
    return abs(np.random.normal(0, freq_std)) + freq_mean


def speed_func(t, freq, t1, t2):
    """
    :param t: мс
    :param t1: сек
    :param t2: сек
    TODO: сделать все размерности одинаковыми
    """
    if freq <= 0:
        raise ValueError('`freq` must be positive')
    if t1 < 0:
        raise ValueError('`t1` must be non negative')
    if t2 < 0:
        raise ValueError('`t2` must be non negative')
    

    if t1 / sec_in_msec <= t <= (t1 + 1 / freq) / sec_in_msec:
        return math.sin((t - t1 / sec_in_msec) * math.tau * freq * sec_in_msec)
    elif 0 <= t < t1 / sec_in_msec or \
        (t1 + 1 / freq) / sec_in_msec < t <= (t1 + 1 / freq + t2) / sec_in_msec:
        return 0
    else:
        raise ValueError(f'`t` must be between 0 and {(t1 + 1 / freq + t2) / sec_in_msec}')


def sign(x):
    # TODO: найти уже готовое
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0


def get_move_info(speed, conf):
    x_move = sign(speed) if conf['x_move'] else 0
    y_move = sign(speed) if conf['y_move'] else 0
    z_move = sign(speed) if conf['z_move'] else 0
    return f"x: {x_move}, y: {y_move}, z: {z_move}"


def send(file, send_text):
    outlet.push_sample([send_text])
    file.write(f"{pg.time.get_ticks()/1000} " + send_text + '\n')


info = StreamInfo(name = 'annotations',
                  type = 'Events',
                  channel_count=1,
                  nominal_srate=0,
                  channel_format='string',
                  source_id='my_marker_stream')
outlet = StreamOutlet(info)

pg.display.set_caption('Experiment')
clock = pg.time.Clock()

text = conf["text"]
t_pause = conf["t_pause"] / sec_in_msec
t_cont = conf["t_cont"] / sec_in_msec
t_show = conf["t_show"] / sec_in_msec

font = pg.font.SysFont(name=conf['font_name'],
                           size=conf['font_size'],
                           bold=True)

cells = {}
for id, char in enumerate(conf['alphabet']):
    letter = font.render(char, True, conf['letter_foreground'])
    cells[char] = {
        'id': id,
        'letter_prime': letter,
        'letter_tmp': letter,
        'amplitude_x': (w / 2) * conf['amplitude_x_scale'],
        'amplitude_y': (h / 2) * conf['amplitude_y_scale'],
        'freq': set_freq(conf['freq_mean'], conf['freq_std']),
        't1': set_t(conf['delay_t1_scale'],
                    conf["is_random_delay"]),
        't2': set_t(conf['delay_t2_scale'],
                    conf["is_random_delay"]),
        'start_t': 0,
        'moving': False,
        'prev_speed': 0
    }

running = True
start_experiment = False

cur_simbol_idx = 0
t_cur = None

with open(conf["lof_file_name"], 'w', encoding='utf-8') as log:

    while running:

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
                
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    running = False
                    
                if event.key == pg.K_s:
                    start_experiment = True
                    t0 = pg.time.get_ticks()
                    send(log, 'start_experiment')

                if event.key == pg.K_e:
                    start_experiment = False
                    send(log, 'end_experiment')

                if event.key == pg.K_SPACE:
                    send(log, 'pressed_space')
        
        screen.fill(conf['bg'])
        
        for char, cell in cells.items():
            j, i = cell['id'] // n_cols, cell['id'] % n_cols
            
            if start_experiment:
                
                t = pg.time.get_ticks() - t0
                
                try:
                    speed = speed_func(t - cell['start_t'],
                                       cell['freq'],
                                       cell['t1'],
                                       cell['t2'])
                    cell['prev_speed'] = speed

                    if speed != 0 and not cell['moving']:
                        send(log, f'{char}_start_{get_move_info(speed, conf)}')
                        cell['moving'] = True
                    
                    if speed == 0 and cell['prev_speed'] == 0 and cell['moving']:
                        send(log, f'{char}_end')
                        cell['moving'] = False

                    rect_x = i * w + w / 2 - cell['letter_tmp'].get_width() / 2
                    rect_y = j * h + h / 2 - cell['letter_tmp'].get_height() / 2
                    rect_width = cell['letter_tmp'].get_width()
                    rect_height = cell['letter_tmp'].get_height()
                        

                except ValueError:
                    cell['start_t'] = t
                    speed = speed_func(t - cell['start_t'],
                                       cell['freq'],
                                       cell['t1'],
                                       cell['t2'])
                    cell['prev_speed'] = 0
                    cell['moving'] = False

                dx = cell['amplitude_x'] * speed if conf['x_move'] else 0
                dy = cell['amplitude_y'] * speed if conf['y_move'] else 0

                cell['letter_tmp'] = pg.transform.smoothscale(
                    cell['letter_prime'], 
                    (
                        cell['letter_prime'].get_width() * (speed + 1), 
                        cell['letter_prime'].get_height() * (speed + 1)
                    )
                    ) if conf['z_move'] else cell['letter_prime']
                
            else:
                dx = 0
                dy = 0
            
            if char == text[cur_simbol_idx] and start_experiment:

                if t_cur is None:
                    t_cur = pg.time.get_ticks()
                    send(log, f"{char}_show_start")

                elif t_cur < pg.time.get_ticks() <= t_cur + t_cont:
                    cell['letter_tmp'] = pg.transform.smoothscale(
                        font.render(char, True, conf["start_fg"]),
                        cell['letter_tmp'].get_size())
                
                elif t_cur + t_cont < pg.time.get_ticks() <= t_cur + t_show - t_cont:
                    pass
                
                elif t_cur + t_show - t_cont < pg.time.get_ticks() <= t_cur + t_show:
                    cell['letter_tmp'] = pg.transform.smoothscale(
                        font.render(char, True, conf["end_fg"]),
                        cell['letter_tmp'].get_size())
                
                elif t_cur + t_show < pg.time.get_ticks() <= t_cur + t_show + t_pause:
                    pass
                
                elif cur_simbol_idx < len(text) - 1:
                    send(log, f"{char}_show_end")
                    cur_simbol_idx += 1
                    t_cur = None


            screen.blit(cell['letter_tmp'],
                        (i * w + w / 2 - cell['letter_tmp'].get_width() / 2 + dx,
                         j * h + h / 2 - cell['letter_tmp'].get_height() / 2 + dy))

        pg.display.flip()
        dt = clock.tick(conf['FPS'])

pg.quit()
