from src.app import ExperimentApp
from src.config import Config


def main():
    # При необходимости можно переопределить параметры, например:
    # config = Config(num_cols=5, num_rows=9, mode="move")
    config = Config()

    app = ExperimentApp(config)
    app.run()


if __name__ == "__main__":
    main()
