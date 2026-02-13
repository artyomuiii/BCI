import pygame as pg

from src.cell import Cell


class Grid:
    def __init__(self, config, font, cell_size, outlet, movement_gen):
        """:param cell_size: w x h"""
        self.config = config
        self.cells = {}

        for idx, char in enumerate(config.alphabet):
            row, col = divmod(idx, config.num_cols)
            cell = Cell(
                idx, char, row, col, font, config, outlet, movement_gen, cell_size
            )
            self.cells[char] = cell

    def update(self, is_active: bool):
        # TODO с current_time непорядок
        for cell in self.cells.values():
            current_time = pg.time.get_ticks()
            cell.update(current_time, is_active)

    def draw(self, screen):
        for cell in self.cells.values():
            cell.draw(screen)

    def get_cell(self, char: str):
        return self.cells[char]
