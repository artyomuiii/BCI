import sys

import pygame as pg

from src.config import Config
from src.events import EventHandler
from src.grid import Grid
from src.logger import Logger
from src.lsl import LSLOutlet
from src.movement import MovementGenerator
from src.state import ExperimentState
from src.window import WindowManager


class ExperimentApp:
    def __init__(self, config: Config):
        self.config = config
        pg.init()

        self.window = WindowManager(config)
        self.logger = Logger(config.log_file_name)
        self.outlet = LSLOutlet(self.logger)
        self.font = pg.font.SysFont("Arial", config.font_size, bold=True)

        self.movement_gen = MovementGenerator()
        cell_size = (self.window.cell_width, self.window.cell_height)
        self.grid = Grid(config, self.font, cell_size, self.outlet, self.movement_gen)
        # TODO логика неверная: dx, dy зануляются
        # self.hint = HintManager(config, self.grid, self.outlet, self.font)

        self.state = ExperimentState()
        self.events = EventHandler(self)
        self.clock = pg.time.Clock()
        self.running = True

    def start_experiment(self):
        self.state.is_active = True
        self.outlet.send("start_experiment")
        # self.hint.start(self.state.start_time)

    def end_experiment(self):
        self.state.is_active = False
        self.outlet.send("end_experiment")

    def send_marker(self, msg: str):
        self.outlet.send(msg)

    def quit(self):
        self.running = False

    def run(self):
        while self.running:
            self.events.process()

            self.grid.update(self.state.is_active)
            # now = pg.time.get_ticks()  # TODO правильная ли размерность?
            # self.hint.update(now, self.state.is_active)

            self.window.screen.fill(self.config.bg)
            self.grid.draw(self.window.screen)
            # TODO как будто отрисовка подсказок проискходит раньше заполнения всего экаран, но это не точно

            # за раз отображает все рисования
            pg.display.flip()
            self.clock.tick(self.config.fps)

        self.logger.close()
        pg.quit()
        sys.exit()
