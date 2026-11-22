"""Restrained light and dark Qt styles."""


def stylesheet(dark: bool) -> str:
    """Return the application palette and widget styles."""
    background, surface, text, border = (
        ("#181b20", "#23272e", "#eef0f3", "#41464f") if dark else
        ("#f4f6f8", "#ffffff", "#20262e", "#cbd1d9")
    )
    return f"""
        QWidget {{ background: {background}; color: {text}; font-size: 13px; }}
        QMainWindow, QDialog {{ background: {background}; }}
        QLineEdit, QPlainTextEdit, QTableWidget, QComboBox {{
            background: {surface}; border: 1px solid {border};
            padding: 6px; selection-background-color: #246fba;
        }}
        QTableWidget {{ alternate-background-color: {"#2c323b" if dark else "#edf1f5"}; }}
        QTableWidget::item:alternate {{ background: {"#2c323b" if dark else "#edf1f5"}; }}
        QPushButton, QToolButton {{
            background: {surface}; border: 1px solid {border};
            border-radius: 4px; padding: 7px 10px;
        }}
        QPushButton:hover, QToolButton:hover {{ border-color: #258bb4; }}
        QPushButton:disabled {{ color: #858b95; }}
        QHeaderView::section {{ background: {surface}; padding: 8px; border: none;
            border-bottom: 1px solid {border}; }}
        QTabBar::tab {{ padding: 10px 18px; border-bottom: 3px solid transparent; }}
        QTabBar::tab:selected {{ border-bottom: 3px solid #219ca4; }}
        QGroupBox {{ border: 1px solid {border}; margin-top: 14px; padding-top: 12px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 10px; }}
        QProgressBar {{ border: 1px solid {border}; text-align: center; min-height: 18px; }}
        QProgressBar::chunk {{ background: #219ca4; }}
        QLabel[status="error"] {{ color: {"#ff9393" if dark else "#b22030"}; }}
        QLabel[status="match"] {{ color: {"#72d5a4" if dark else "#137442"}; font-weight: bold; }}
        QLabel[status="mismatch"] {{ color: {"#ff9393" if dark else "#b22030"}; font-weight: bold; }}
    """
