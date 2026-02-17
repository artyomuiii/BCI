from dataclasses import dataclass


@dataclass
class ExperimentState:
    is_active: bool = False  # идёт ли сейчас эксперимент
