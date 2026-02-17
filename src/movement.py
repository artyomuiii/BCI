import math
import random

import numpy as np


class MovementGenerator:
    @staticmethod
    def get_move_speed(
        t_ms: float, freq: float, delay_before: float, delay_after: float
    ) -> float:
        """Возвращает скорость [-1..1] для момента t (мс)"""
        # Переводим в секунды
        t = t_ms / 1000.0

        # Пауза до показа символа
        if 0 <= t < delay_before:
            return 0.0

        # Активная фаза (один полный период)
        elif delay_before <= t < delay_before + 1.0 / freq:
            return math.sin((t - delay_before) * math.tau * freq)

        # Пауза после
        elif delay_before + 1.0 / freq <= t < delay_before + 1.0 / freq + delay_after:
            return 0.0

        else:
            raise ValueError("t вне допустимого диапазона!")

    @staticmethod
    def get_blink_speed(
        t_ms: float, freq: float, delay_before: float, delay_after: float, duty: float
    ) -> float:
        """Возвращает скорость [-1..1] для момента t (мс)"""
        # Переводим в секунды
        t = t_ms / 1000.0

        # Пауза до показа символа
        if 0 <= t < delay_before:
            return 0.0

        # Активная фаза (duty от одного полного периода - мигание)
        elif delay_before <= t < delay_before + (1.0 / freq) * duty:
            return math.sin((t - delay_before) * math.tau * freq)

        # Часть периода без мигания и пауза после
        elif (
            delay_before + (1.0 / freq) * duty
            <= t
            < delay_before + 1.0 / freq + delay_after
        ):
            return 0.0

        else:
            raise ValueError("t вне допустимого диапазона!")

    @staticmethod
    def generate_freq(mean: float, std: float) -> float:
        """Сэмплирует частоту (Гц)"""
        return abs(np.random.normal(0, std)) + mean

    @staticmethod
    def generate_delay(base: float, is_random: bool) -> float:
        """Задержка до/после показа символа (сек)"""
        if is_random:
            return random.random() * base
        return base
