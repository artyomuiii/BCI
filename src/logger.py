import os

import pygame as pg


class Logger:
    def __init__(self, filepath: str):
        # Создаём папку, если её нет
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.file = open(filepath, "w", encoding="utf-8")

    def write(self, message: str):
        timestamp = pg.time.get_ticks() / 1000.0
        self.file.write(f"{timestamp:.3f}: {message}\n")
        self.file.flush()

    def close(self):
        self.file.close()
