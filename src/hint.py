import pygame as pg


class HintManager:
    def __init__(self, config, grid, outlet, font):
        self.text = config.text
        self.grid = grid
        self.outlet = outlet
        self.font = font

        # Тайминги (мс)
        self.t_pause = config.t_pause * 1000
        self.t_cont = config.t_cont * 1000
        self.t_show = config.t_show * 1000

        # Цвета букв в начале и в конце подсказки
        self.fg_start = config.fg_start
        self.fg_end = config.fg_end

        self.current_idx = 0
        self.state = "idle"  # "idle", "showing", "pausing"
        self.phase_start = 0
        self.current_cell = None

    def start(self):
        """Начинает показ подсказок с первой буквы"""
        self.current_idx = 0
        self._show_next()

    def _show_next(self):
        if self.current_idx >= len(self.text):
            return

        char = self.text[self.current_idx]

        self.current_cell = self.grid.get_cell(char)
        self.state = "showing"
        self.phase_start = pg.time.get_ticks()
        self.outlet.send(f"show_{char}_start")

    def update(self, is_active: bool):
        if not is_active or self.state == "idle":
            return

        cell = self.current_cell

        elapsed = pg.time.get_ticks() - self.phase_start

        if self.state in ["showing", "pausing"]:
            if elapsed <= self.t_cont:
                # Подсветка в начале, чтобы обратить внимание на букву
                surf = self.font.render(cell.char, True, self.fg_start)
                cell.set_override_surface(surf)

            elif elapsed <= self.t_show - self.t_cont:
                # Середина – обычный вид
                cell.clear_override()

            elif elapsed <= self.t_show:
                # Подсветка в конце, чтобы испытуемый готовился искать следующий символ
                surf = self.font.render(cell.char, True, self.fg_end)
                cell.set_override_surface(surf)

            elif elapsed <= self.t_show + self.t_pause:
                # Пауза – снять подсветку, отправить маркер окончания
                cell.clear_override()
                if self.state != "pausing":
                    self.outlet.send(f"show_{cell.char}_end")
                    self.state = "pausing"

            else:
                # Переход к следующей букве
                self.current_idx += 1
                if self.current_idx < len(self.text):
                    self._show_next()
                else:
                    self.state = "idle"
                    self.current_cell = None
