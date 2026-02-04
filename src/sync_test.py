import os

import pygame as pg
from pylsl import StreamInfo, StreamOutlet

BG = (30, 30, 40)
FG = (220, 220, 220)
PAUSE = 2.0
ACTION_PAUSE = 0.5

# Set up pinned window on second monitor
x = -1920
y = 0
os.environ["SDL_VIDEO_WINDOW_POS"] = f"{x},{y}"
os.environ["SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS"] = "0"

# Инициализация
pg.init()
screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
font = pg.font.SysFont(None, 48)
clock = pg.time.Clock()

# LSL поток для меток
info = StreamInfo(
    name="annotations",
    type="Events",  # 'Markers'
    channel_count=1,
    nominal_srate=0,
    channel_format="string",
    source_id="my_marker_stream",
)
outlet = StreamOutlet(info)


# Ф-ция отрисовки
def show(text):
    screen.fill(BG)
    text_surf = font.render(text, True, FG)
    w, h = screen.get_size()
    text_rect = text_surf.get_rect(center=(w // 2, h // 2))
    screen.blit(text_surf, text_rect)
    pg.display.flip()


# Основной цикл
i = 0
is_run, is_push = True, False
t0 = pg.time.get_ticks() / 1000
while is_run:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            pg.quit()
            exit()
        if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            is_run = False

    t = pg.time.get_ticks() / 1000 - t0

    if 0 <= t < PAUSE:
        # show(f"Пауза...")
        show("")
    elif (PAUSE <= t < PAUSE + ACTION_PAUSE) and not is_push:
        show("Выполните действие!")
        outlet.push_sample([f"action_{i + 1}"])
        is_push = True
        print(f"action_{i + 1}")
        i += 1
    elif t >= PAUSE + ACTION_PAUSE:
        is_push = False
        t0 = pg.time.get_ticks() / 1000

    clock.tick(60)

pg.quit()
