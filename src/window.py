import os

import pygame as pg


class WindowManager:
    def __init__(self, config):
        # Принудительное позиционирование окна
        os.environ["SDL_VIDEO_WINDOW_POS"] = f"{config.win_x},{config.win_y}"
        os.environ["SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS"] = "0"

        self.screen = pg.display.set_mode(size=(0, 0), flags=pg.FULLSCREEN)
        pg.display.set_caption("Experiment")

        # Размеры одной ячейки
        self.cell_width = self.screen.get_width() // config.num_cols
        self.cell_height = self.screen.get_height() // config.num_rows
