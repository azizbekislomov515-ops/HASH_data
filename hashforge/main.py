"""Application entry point with lazy GUI imports for CLI use."""

import sys


def main() -> int:
    """Launch Qt, or dispatch explicit arguments to the CLI."""
    if len(sys.argv) > 1:
        from .cli import main as cli_main
        return cli_main(sys.argv[1:])
    from PySide6.QtWidgets import QApplication
    from .gui.main_window import MainWindow

    application = QApplication(sys.argv)
    application.setApplicationName("HashForge")
    application.setOrganizationName("HashForge")
    application.setApplicationVersion("1.0.0")
    application.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
