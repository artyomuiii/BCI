import json
import sys

import pygame as pg

from src.utils.utils import (
    cell_processing,
    event_processing,
    get_cells,
    get_outlet,
    hint_processing,
    pinned_window,
)


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "cfgs/cfg.json"
    with open(cfg_path, encoding="utf-8") as cfg_file:
        cfg = json.load(cfg_file)

    pg.init()

    pinned_window(cfg)

    scr = pg.display.set_mode(size=(0, 0), flags=pg.FULLSCREEN)

    n_cols = cfg["num_cols"]  # 11, 5
    n_rows = cfg["num_rows"]  # 4, 9
    w, h = scr.get_width() // n_cols, scr.get_height() // n_rows

    outlet = get_outlet()

    pg.display.set_caption("Experiment")
    clock = pg.time.Clock()

    font = pg.font.SysFont(name="Arial", size=cfg["font_size"], bold=True)

    cells = get_cells(cfg, font, w, h)

    is_end = False
    is_running = True
    is_start_exp = False

    cur_simbol_id = 0
    t_cur = None
    t0 = None

    with open(cfg["log_file_name"], "w", encoding="utf-8") as log:

        while is_running:

            is_running, is_start_exp, t0 = event_processing(
                outlet, log, is_running, is_start_exp, t0
            )

            scr.fill(cfg["bg"])

            for char, cell in cells.items():
                i, j = cell["id"] // n_cols, cell["id"] % n_cols

                dx, dy, cell["letter_tmp"] = cell_processing(
                    char, cell, is_start_exp, t0, outlet, log, cfg, font
                )

                t_cur, cur_simbol_id, is_end = hint_processing(
                    char,
                    cur_simbol_id,
                    is_start_exp,
                    is_end,
                    t_cur,
                    cell,
                    font,
                    outlet,
                    log,
                    cfg,
                )

                # отрисовка
                scr.blit(
                    cell["letter_tmp"],
                    (
                        j * w + w / 2 - cell["letter_tmp"].get_width() / 2 + dx,
                        i * h + h / 2 - cell["letter_tmp"].get_height() / 2 + dy,
                    ),
                )

            pg.display.flip()
            clock.tick(cfg["FPS"])

    pg.quit()
