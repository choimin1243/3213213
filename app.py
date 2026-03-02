import os
import time
from pathlib import Path

from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QPen, QPixmap, QGuiApplication, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow


class OverlayWindow(QMainWindow):
    """
    Transparent-looking overlay with:
      - black border
      - resizable window (native)
      - pen & eraser drawing
      - capture window region
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Overlay Draw & Capture (PyQt5)")
        self.resize(900, 600)

        # "Always on top" + frameless would break easy resizing.
        # So we keep a normal window for resizing, and make the background translucent.
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Make window background translucent.
        # Note: truly click-through transparency is OS-specific; this keeps interaction in the window.
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        # Drawing layer
        self.canvas = QPixmap(self.size())
        self.canvas.fill(Qt.transparent)

        self.drawing = False
        self.last_point = QPoint()

        # Modes
        self.mode = "pen"   # "pen" or "eraser"
        self.pen_width = 3
        self.eraser_width = 22

        # Output folder
        self.out_dir = Path("captures")
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def resizeEvent(self, event):
        # Expand canvas when window resizes; keep existing drawing.
        new_size = event.size()
        if new_size.width() > 0 and new_size.height() > 0:
            new_canvas = QPixmap(new_size)
            new_canvas.fill(Qt.transparent)
            painter = QPainter(new_canvas)
            painter.drawPixmap(0, 0, self.canvas)
            painter.end()
            self.canvas = new_canvas
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)

        # 1) Draw transparent background (nothing)
        # 2) Draw canvas strokes
        painter.drawPixmap(0, 0, self.canvas)

        # 3) Draw black border only
        border_pen = QPen(QColor(0, 0, 0, 255))
        border_pen.setWidth(2)
        painter.setPen(border_pen)
        # -1 to avoid clipping the border at edges
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

        painter.end()

    def _draw_line(self, start: QPoint, end: QPoint):
        painter = QPainter(self.canvas)

        if self.mode == "pen":
            pen = QPen(QColor(255, 0, 0, 255))  # 기본 빨강(원하면 바꾸세요)
            pen.setWidth(self.pen_width)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(pen)
            painter.drawLine(start, end)

        else:  # eraser
            # Transparent "erase" using CompositionMode_Clear
            pen = QPen(Qt.transparent)
            pen.setWidth(self.eraser_width)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setPen(pen)
            painter.drawLine(start, end)

        painter.end()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drawing and (event.buttons() & Qt.LeftButton):
            self._draw_line(self.last_point, event.pos())
            self.last_point = event.pos()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self._draw_line(self.last_point, event.pos())
            self.drawing = False
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key_Escape:
            self.close()
            return

        # Mode toggle
        if key == Qt.Key_P:
            self.mode = "pen"
            self.setWindowTitle("Overlay (Mode: PEN)  |  P=Pen, E=Eraser, C=Capture")
            return

        if key == Qt.Key_E:
            self.mode = "eraser"
            self.setWindowTitle("Overlay (Mode: ERASER)  |  P=Pen, E=Eraser, C=Capture")
            return

        # Clear all
        if key in (Qt.Key_Delete, Qt.Key_Backspace):
            self.canvas.fill(Qt.transparent)
            self.update()
            return

        # Capture window region
        if key == Qt.Key_C:
            self.capture_region()
            return

        # Open output folder (Windows/Mac/Linux)
        if key == Qt.Key_O:
            self.open_output_folder()
            return

        super().keyPressEvent(event)

    def capture_region(self):
        """
        Capture the window rectangle on screen (including border + drawings).
        Saves to captures/capture_YYYYmmdd_HHMMSS.png
        """
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return

        # IMPORTANT: hide window a moment? (optional)
        # If you want to capture "underneath" without the overlay itself, you'd need a different strategy.
        # Here we capture exactly what you see (overlay window area).
        geo: QRect = self.frameGeometry()  # includes window frame; for client-only use geometry()
        pix = screen.grabWindow(0, geo.x(), geo.y(), geo.width(), geo.height())

        ts = time.strftime("%Y%m%d_%H%M%S")
        out_path = self.out_dir / f"capture_{ts}.png"
        pix.save(str(out_path), "PNG")
        self.setWindowTitle(f"Saved: {out_path}")

    def open_output_folder(self):
        folder = str(self.out_dir.resolve())
        try:
            if os.name == "nt":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}"')
        except Exception:
            pass


def main():
    app = QApplication([])
    w = OverlayWindow()
    w.show()
    app.exec_()


if __name__ == "__main__":
    import sys
    main()
