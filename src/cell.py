import pygame as pg


class Cell:
    def __init__(
        self, id, char, row, col, font, config, outlet, movement_gen, cell_size
    ):
        """:param cell_size: w x h"""
        self.id = id
        self.char = char
        self.row = row
        self.col = col
        self.config = config
        self.outlet = outlet
        self.mg = movement_gen

        # Шрифты
        self.font = font  # шрифт с меняющимся размером
        self.default_font = font  # шрифт с заданным размером

        # Статические поверхности
        self.letter = font.render(char, True, config.fg)
        self.letter_blink = font.render(char, True, config.fg_blink)

        # Прямоугольник и его раздутая версия для blink-подсветки
        cell_w, cell_h = cell_size
        x = col * cell_w + cell_w // 2
        y = row * cell_h + cell_h // 2
        self.rect = self.letter.get_rect(center=(x, y))
        pad = 10
        self.rect_blink = self.rect.inflate(pad * 2, pad * 2)

        # Амплитуды смещения
        self.amp_x = (cell_w / 2) * config.amp_x_scale
        self.amp_y = (cell_h / 2) * config.amp_y_scale

        # Параметры движения
        self.freq = self.mg.generate_freq(config.freq_mean, config.freq_std)
        self.delay_before = self.mg.generate_delay(
            config.delay_before, config.is_rand_delay
        )
        self.delay_after = self.mg.generate_delay(
            config.delay_after, config.is_rand_delay
        )

        # Динамические состояния
        self.start_t = 0  # момент начала текущего цикла (мс)
        self.prev_speed = 0.0
        self.current_speed = 0.0
        self.is_moving = False
        self.dx = 0
        self.dy = 0
        self.current_surface = self.letter
        self.override_surface = None  # для временной замены (при подсказках)

    def update(self, current_time: int, is_active: bool):
        if not is_active:
            self.dx = self.dy = 0
            self.current_speed = 0
            return

        t = current_time - self.start_t

        try:
            if self.config.mode == "move":
                speed = self.mg.get_move_speed(
                    t, self.freq, self.delay_before, self.delay_after
                )
            elif self.config.mode == "blink":
                speed = self.mg.get_blink_speed(
                    t, self.freq, self.delay_before, self.delay_after, self.config.duty
                )

            self.current_speed = speed

            # Начало движения
            if speed != 0 and not self.is_moving:
                self.outlet.send(f"{self.char}_start_{self._move_info(speed)}")
                self.is_moving = True

            # Конец движения
            if speed == 0 and self.prev_speed == 0 and self.is_moving:
                self.outlet.send(f"{self.char}_end")
                self.is_moving = False

        # Переполнение времени – перезапуск цикла
        except ValueError:
            self.start_t = pg.time.get_ticks()

            # Пересчитываем паузы между буквами -> вносим случайность
            self.delay_before = self.mg.generate_delay(
                self.config.delay_before, self.config.is_rand_delay
            )
            self.delay_after = self.mg.generate_delay(
                self.config.delay_after, self.config.is_rand_delay
            )

            self.current_speed = 0
            self.prev_speed = 0
            self.is_moving = False

        self._update_render()
        self.prev_speed = self.current_speed

    def _update_render(self):
        """Обновляет surface и смещения на основе текущей скорости и режима"""
        if self.override_surface is not None:
            self.current_surface = self.override_surface
            self.dx = self.dy = 0
            return

        mode = self.config.mode

        if mode == "blink":
            if self.is_moving:
                self.current_surface = self.letter_blink
            else:
                self.current_surface = self.letter

            # Приращений нет
            self.dx = self.dy = 0

        elif mode == "move":
            # Считаем приращения
            self.dx = self.amp_x * self.current_speed if self.config.is_x_move else 0
            self.dy = self.amp_y * self.current_speed if self.config.is_y_move else 0

            # Новый отмасштабированный рендер буквы
            if self.config.is_z_move:
                # [-1, 1] -> [0, 2] - увеличение размера от 0 до 2ух раз
                scale = self.current_speed + 1.0

                # Масштабирование старого шрифта
                w = int(self.letter.get_width() * scale)
                h = int(self.letter.get_height() * scale)
                self.current_surface = pg.transform.smoothscale(self.letter, (w, h))

                # Создание нового шрифта
                # TODO: для лучшей производительности можно шкалировать по сетке, перед
                #   этим кэшируя шрифты
                # new_size = int(self.default_font.get_height() * scale)
                # self.font = pg.font.SysFont(self.config.font_name, new_size, bold=True)
                # self.current_surface = self.font.render(self.char, True, self.config.fg)
            else:
                self.current_surface = self.letter

        else:
            raise ValueError(f"Unknown `mode`: {mode}!")

    def draw(self, screen):
        """Отрисовка ячейки на экране"""
        # Прямоугольный фон для режима `blink`
        if self.is_moving and self.config.mode == "blink":
            pg.draw.rect(screen, self.config.bg_blink, self.rect_blink)

        # Позиция с учётом смещения (dx, dy)
        rect = self.current_surface.get_rect(
            center=(self.rect.centerx + self.dx, self.rect.centery + self.dy)
        )
        screen.blit(self.current_surface, rect)

    def set_override_surface(self, surface):
        self.override_surface = surface
        self._update_render()

    def clear_override(self):
        self.override_surface = None
        self._update_render()

    def _sign(self, x):
        """Кастомный sign"""
        return 1 if x > 0 else -1

    def _move_info(self, speed) -> str:
        """Строка с информацией для маркеров о движении"""
        if self.config.mode == "blink":
            return "blink"

        if self.config.mode == "move":
            is_x_move = self._sign(speed) if self.config.is_x_move else 0
            is_y_move = self._sign(speed) if self.config.is_y_move else 0
            is_z_move = self._sign(speed) if self.config.is_z_move else 0

            info = f"x: {is_x_move}, y: {is_y_move}, z: {is_z_move}"

            return info

        raise ValueError("Incorrect 'mode' value!")
