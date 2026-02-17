import sys

import pygame as pg

from src.config import Config
from src.events import EventHandler
from src.grid import Grid
from src.hint import HintManager
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
        self.font = pg.font.SysFont(config.font_name, config.font_size, bold=True)

        self.movement_gen = MovementGenerator()
        cell_size = (self.window.cell_width, self.window.cell_height)
        self.grid = Grid(config, self.font, cell_size, self.outlet, self.movement_gen)
        self.hint = HintManager(config, self.grid, self.outlet, self.font)

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

    def send_info(self):
        t_info = f"t_pause: {self.config.t_pause}, t_cont: {self.config.t_cont}, t_show: {self.config.t_show}"
        freq_info = (
            f"freq_mean: {self.config.freq_mean}, freq_std: {self.config.freq_std}"
        )
        delay_info = f"delay_before: {self.config.delay_before}, delay_after: {self.config.delay_after}, is_rand_delay: {self.config.is_rand_delay}"
        text_info = f"text: {self.config.text}"
        mode_info = f"mode: {self.config.mode}"
        xyz_info = f"is_x_move: {self.config.is_x_move}, is_y_move: {self.config.is_y_move}, is_z_move: {self.config.is_z_move}"

        self.send_marker(t_info)
        self.send_marker(freq_info)
        self.send_marker(delay_info)
        self.send_marker(text_info)
        self.send_marker(mode_info)
        self.send_marker(xyz_info)

    def quit(self):
        self.running = False

    def run(self):
        self.send_info()

        self.hint.start()

        while self.running:
            self.events.process()

            self.grid.update(self.state.is_active)

            self.hint.update(self.state.is_active)

            self.window.screen.fill(self.config.bg)
            self.grid.draw(self.window.screen)

            # за раз отображает все рисования
            pg.display.flip()
            self.clock.tick(self.config.fps)

        self.logger.close()
        pg.quit()
        sys.exit()
