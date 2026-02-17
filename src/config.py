from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    # Размеры окна и сетки
    win_x: int = -1920
    win_y: int = 0
    num_cols: int = 11
    num_rows: int = 4

    # Вводимый текст
    text: str = "КРАНОВЩИК"

    # Режим эксперимента
    mode: str = "blink"  # blink / move

    # Среднее и дисперсия частоты показа символов
    freq_mean: float = 1.0
    freq_std: float = 0.1

    # Пауза до показа символа, после и флаг случайных значений паузы
    delay_before: float = 0.4
    delay_after: float = 0.6
    is_rand_delay: bool = True  # из равномерного [0, delay_*]

    # Тайминги (в секундах) для подсказок вводимых букв
    t_pause: float = 1.0  # пауза между буквами
    t_cont: float = 1.0  # длительность подсветки (старт/финиш)
    t_show: float = 5.0  # общее время показа буквы

    # Алфавит
    alphabet: str = "1234567890_ЙЦУКЕНГШЩЗХФЫВАПРОЛДЖЭЁЯЧСМИТЬБЮЪ"

    # Техническое
    fps: int = 60
    log_file_name: str = "logs/log.txt"
    font_size: int = 55
    font_name: str = "Arial"

    # ---------- Режим "move" ----------
    # По каким осям будет движение
    is_x_move: bool = False
    is_y_move: bool = False
    is_z_move: bool = True

    # ---------- Режим "blink" ----------
    duty: float = 0.2  # доля на показ символа от периода

    # Масштаб амплитуды при горизонтальном и вертикальном смещениях
    amp_x_scale: float = 0.5
    amp_y_scale: float = 0.5

    # ---------- Цвета (RGB) ----------
    # Обычный цвет фона и букв
    bg: List[int] = field(default_factory=lambda: [255, 255, 255])
    fg: List[int] = field(default_factory=lambda: [0, 0, 0])

    # Цвет фона (прямоугольника) и букв при мигании в режиме "blink"
    bg_blink: List[int] = field(default_factory=lambda: [100, 30, 120])
    fg_blink: List[int] = field(default_factory=lambda: [200, 220, 50])

    # Цвет букв при подсказках испытуемому (старт/финиш)
    fg_start: List[int] = field(default_factory=lambda: [0, 255, 0])
    fg_end: List[int] = field(default_factory=lambda: [255, 0, 0])
