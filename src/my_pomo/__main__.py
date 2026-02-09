"""Entry point for running my_pomo as a module: python -m my_pomo"""

from my_pomo.app import PomoApp


def main():
    """Run the My-Pomo application."""
    app = PomoApp()
    app.run()


if __name__ == "__main__":
    main()
