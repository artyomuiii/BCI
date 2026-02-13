from dataclasses import dataclass


@dataclass
class ExperimentState:
    # TODO зачем нужны эти параметры?
    is_active: bool = False  # идёт ли сейчас эксперимент
