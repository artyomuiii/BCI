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

    def start(self, current_time: int):
        """Начинает показ подсказок с первой буквы"""
        # TODO current_time не нравится тут
        self.current_idx = 0
        self._show_next(current_time)

    def _show_next(self, current_time: int):
        if self.current_idx >= len(self.text):
            return

        char = self.text[self.current_idx]

        self.current_cell = self.grid.get_cell(char)
        self.state = "showing"
        self.phase_start = current_time
        self.outlet.send(f"show_{char}_start")

    def update(self, current_time: int, is_active: bool):
        if not is_active or self.state == "idle":
            return

        cell = self.current_cell

        elapsed = current_time - self.phase_start

        if self.state == "showing":
            if elapsed <= self.t_cont:
                # Подсветка в начале, чтобы обратить внимание на букву
                surf = self.font.render(cell.char, True, self.fg_start)
                cell.set_override_surface(surf)

            elif elapsed <= self.t_show - self.t_cont:
                # Середина – обычный вид
                # TODO мб сделать так, чтобы clear_override вызывался только 1 раз
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
                    # TODO опять проблема с current_time
                    self._show_next(current_time)
                else:
                    self.state = "idle"
                    self.current_cell = None
