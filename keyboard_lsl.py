import pygame, math, random, os
from pylsl import StreamInfo, StreamOutlet

#set up pinned window on second monitor
x = -1920
y = 0
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"
os.environ['SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS'] = '0'


pygame.init()

flags = pygame.FULLSCREEN
screen = pygame.display.set_mode(size = (0, 0), flags = flags)

width  = screen.get_width()
height = screen.get_height()

n_cols = 11
n_rows = 4

w, h = width // n_cols, height // n_rows

sec_in_msec = 1e-3

speed_func = lambda t, freq: math.sin(t * freq * math.pi * sec_in_msec / 2) ** 2

info = StreamInfo(name = 'annotations', type = 'Events', channel_count = 1, nominal_srate = 0, channel_format = 'string', source_id = 'my_marker_stream')

outlet = StreamOutlet(info)

print('lsl outlet is created')

#print(pygame.font.get_fonts())

pygame.display.set_caption('Experiment')
clock = pygame.time.Clock()
t0 = pygame.time.get_ticks()

background = (55, 55, 55)
letter_foreground = (255, 255, 255)
shadow_foreground = (155, 155, 155)

FPS = 60

font = pygame.font.SysFont(name = 'Arial', size = 80, bold = True)

alphabet = '1234567890<ЁЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ'

cells = {}

for id, char in enumerate(alphabet):
    cells[char] = {
        'id': id,
        'letter': font.render(char, True, letter_foreground),
        'shadow': font.render(char, True, shadow_foreground),
        'alpha': random.random(),
        'amplitude': 20, #random.random() * 15 + 5,
        'frequency': 1, #random.random() * 4.8 + 0.2,
        'previous_speed': 0,
        'decrease': False
    }
    
#print(cells)

running = True

start_experiment = False

while running:
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if event.type == pygame.KEYDOWN:
            
            if event.key == pygame.K_ESCAPE:
                running = False
                
            if event.key == pygame.K_s:
                start_experiment = True
                outlet.push_sample(['start_experiment'])
            
            if event.key == pygame.K_e:
                start_experiment = False
                outlet.push_sample(['end_experiment'])

    t = pygame.time.get_ticks() - t0
    
    screen.fill(background)
    
    for char, params in cells.items():
        j, i = params['id'] // n_cols, params['id'] % n_cols
        
        speed = speed_func(t, params['frequency'])
        
        if speed < params['previous_speed'] and not params['decrease']:
            params['decrease'] = True
            #if char == 'А' and start_experiment:
            outlet.push_sample([f'letter_{char}_max'])
        elif speed > params['previous_speed'] and params['decrease']:
            params['decrease'] = False
            params['alpha'] = random.random()
            #if char == 'А' and start_experiment:
            outlet.push_sample([f'letter_{char}_min'])
            
        params['previous_speed'] = speed
        
        
        dirx = math.cos(math.tau * params['alpha'])
        diry = math.sin(math.tau * params['alpha'])
        
        dx = params['amplitude'] * dirx * speed
        dy = params['amplitude'] * diry * speed
        
        pygame.draw.rect(screen, (255, 0, 0), (i * w, j * h, w, h), 1)
        screen.blit(params['shadow'], (i * w + w / 2 - params['shadow'].get_width() / 2 + dx, j * h + h / 2 - params['shadow'].get_height() / 2 - dy))
        screen.blit(params['letter'], (i * w + w / 2 - params['letter'].get_width() / 2, j * h + h / 2 - params['letter'].get_height() / 2))
    
    
    #R = 20
    
    #print(alpha)
    
    #freq = 1 # 2 means 1 amplitude is 0.5 second
    
    #speed = abs(math.sin(t * freq * math.pi * sec_in_msec / 2))
    #speed = speed_func(t, freq)
    #print(speed, min_speed)

    
    #if speed < prev_speed and not decrease:
    #    decrease = True
    #elif speed > prev_speed and decrease:
    #    alpha = random.random()
        #dirx = math.cos(math.tau * alpha)
        #diry = math.sin(math.tau * alpha)
        #speed = abs(math.sin(t * freq * math.pi / 2))
    #    decrease = False
        #print('yeah')
        #screen.blit(letter, (0, 0))
    
    #prev_speed = speed
    
    #dirx = math.cos(math.tau * alpha)
    #diry = math.sin(math.tau * alpha)
    
    #dx = R * dirx * speed
    #dy = R * diry * speed
    
    #if moving_forward:
    #    travel += (dx1 - dx0) ** 2 + (dy1 - dy0) ** 2
    #    if travel >= R:
    #        moving_forward = False
    #else:
    #    travel -= (dx1 - dx0) ** 2 + (dy1 - dy0) ** 2
    #    if travel <= 0:
    #        moving_forward = True
    #        alpha = random.random()
    #        
    #print(travel)
    
    #dx = dx1
    #dy = dy1    
    
    #for i in range(n_col):
    #    for j in range(n_row):
    #        pygame.draw.rect(screen, (255, 0, 0), (i * w, j * h, w, h), 1)
    #        screen.blit(shadow, (i * w + w / 2 - letter.get_width() / 2 + dx, j * h + h / 2 - letter.get_height() / 2 - dy))
    #        screen.blit(letter, (i * w + w / 2 - letter.get_width() / 2, j * h + h / 2 - letter.get_height() / 2))
        
    #R * dirx * sin(t1) - R * dirx * sin
    
    #screen.blit(shadow, (width / 2 + dx, height / 2 - dy))
    #screen.blit(letter, (width / 2, height / 2))
    
    
    pygame.display.flip()
    dt = clock.tick(FPS)
    #print(f'dt = {dt}')

pygame.quit()