import sys
import math
import cv2
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QSpinBox, QGroupBox, 
                               QCheckBox, QLineEdit, QComboBox, QPushButton as QBtn)
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QPolygonF, QImage, QPixmap


class Shape:
    """Base class for all shapes"""
    def __init__(self, name, width, height, contour=None):
        self.name = name
        self.width = width
        self.height = height
        self.contour = contour  # OpenCV contour for camera-detected shapes
    
    def draw(self, painter, x, y, direction=None):
        """Override in subclasses to draw the shape"""
        pass
    
    def calculate_optimized_layout(self, surface_width, surface_height, min_gap=5):
        """
        Override this method to provide custom optimization for your shape.
        Returns: (positions_list, calculated_gap)
        where positions_list = [(x, y, direction), ...]
        """
        # Default hexagonal packing
        cols_even = max(1, int((surface_width - min_gap) / (self.width + min_gap)))
        
        packing_factor = self.get_packing_efficiency()
        row_spacing = self.height * packing_factor
        rows = max(1, int((surface_height - min_gap) / (row_spacing + min_gap)))
        
        if cols_even > 0:
            gap_x = (surface_width - self.width * cols_even) / (cols_even + 1)
        else:
            gap_x = 0
            
        if rows > 0:
            gap_y = (surface_height - row_spacing * rows) / (rows + 1)
        else:
            gap_y = 0
        
        calculated_gap = (gap_x + gap_y) / 2
        positions = []
        
        for row in range(rows):
            if row % 2 == 0:
                cols = cols_even
                x_offset = gap_x
            else:
                cols = cols_even
                x_offset = gap_x + (self.width + gap_x) / 2
                
                last_x = x_offset + (cols - 1) * (self.width + gap_x) + self.width
                if last_x > surface_width - gap_x:
                    cols = max(0, cols - 1)
            
            for col in range(cols):
                x = x_offset + col * (self.width + gap_x)
                y = gap_y + row * (row_spacing + gap_y)
                positions.append((x, y, None))
        
        return positions, calculated_gap
    
    def get_packing_efficiency(self):
        return 0.866
    
    def supports_optimization(self):
        return True


class CameraDetectedShape(Shape):
    """Shape detected from camera with custom contour"""
    def __init__(self, name, width, height, contour):
        super().__init__(name, width, height, contour)
        self.normalized_contour = self.normalize_contour(contour)
    
    def supports_optimization(self):
        """Camera shapes should not be optimized - we don't know their tessellation pattern"""
        return False
    
    def normalize_contour(self, contour):
        """Normalize contour to 0-1 range"""
        if contour is None or len(contour) == 0:
            return []
        
        contour = contour.reshape(-1, 2)
        min_x, min_y = contour.min(axis=0)
        max_x, max_y = contour.max(axis=0)
        
        w = max_x - min_x
        h = max_y - min_y
        
        if w == 0 or h == 0:
            return []
        
        normalized = []
        for point in contour:
            norm_x = (point[0] - min_x) / w
            norm_y = (point[1] - min_y) / h
            normalized.append((norm_x, norm_y))
        
        return normalized
    
    def draw(self, painter, x, y, direction=None):
        from PySide6.QtCore import QPointF
        
        if not self.normalized_contour:
            # Fallback to rectangle
            painter.drawRect(int(x), int(y), self.width, self.height)
            return
        
        # Scale normalized contour to target size
        scaled_points = []
        for norm_x, norm_y in self.normalized_contour:
            px = x + norm_x * self.width
            py = y + norm_y * self.height
            scaled_points.append(QPointF(px, py))
        
        painter.drawPolygon(scaled_points)


class RectangleShape(Shape):
    def draw(self, painter, x, y, direction=None):
        painter.drawRect(int(x), int(y), self.width, self.height)
    
    def supports_optimization(self):
        return False


class CircleShape(Shape):
    def draw(self, painter, x, y, direction=None):
        painter.drawEllipse(int(x), int(y), self.width, self.height)
    
    def get_packing_efficiency(self):
        return 0.866


class TriangleShape(Shape):
    def draw(self, painter, x, y, direction=None):
        from PySide6.QtCore import QPoint
        if direction == "down":
            points = [
                QPoint(int(x), int(y)),
                QPoint(int(x + self.width), int(y)),
                QPoint(int(x + self.width / 2), int(y + self.height))
            ]
        else:
            points = [
                QPoint(int(x + self.width / 2), int(y)),
                QPoint(int(x), int(y + self.height)),
                QPoint(int(x + self.width), int(y + self.height))
            ]
        painter.drawPolygon(points)
    
    def calculate_optimized_layout(self, surface_width, surface_height, min_gap=5):
        cols = max(1, int((surface_width - min_gap) / (self.width + min_gap)))
        triangle_pair_height = self.height
        rows = max(1, int((surface_height - min_gap) / (triangle_pair_height + min_gap)))
        
        if cols > 0:
            gap_x = (surface_width - self.width * cols) / (cols + 1)
        else:
            gap_x = 0
            
        if rows > 0:
            gap_y = (surface_height - triangle_pair_height * rows) / (rows + 1)
        else:
            gap_y = 0
        
        calculated_gap = (gap_x + gap_y) / 2
        positions = []
        
        for row in range(rows):
            y = gap_y + row * (triangle_pair_height + gap_y)
            
            for col in range(cols):
                x = gap_x + col * (self.width + gap_x)
                positions.append((x, y, "up"))
                
            if cols > 1:
                for col in range(cols - 1):
                    x = gap_x + col * (self.width + gap_x) + (self.width + gap_x) / 2
                    positions.append((x, y, "down"))
        
        return positions, calculated_gap


class CameraWidget(QWidget):
    """Widget to show camera feed and detect shapes"""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(320, 240)
        self.camera_image = None
        self.detected_contour = None
        self.capture = None
        
    def start_camera(self):
        """Start camera capture"""
        self.capture = cv2.VideoCapture(1)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 30ms refresh
    
    def stop_camera(self):
        """Stop camera capture"""
        if hasattr(self, 'timer'):
            self.timer.stop()
        if self.capture:
            self.capture.release()
            self.capture = None
    
    def update_frame(self):
        """Update camera frame and detect shapes"""
        if not self.capture:
            return
        
        ret, frame = self.capture.read()
        if not ret:
            return
        
        # Resize for display
        frame = cv2.resize(frame, (320, 240))
        
        # Detect shape
        self.detected_contour = self.detect_shape(frame)
        
        # Draw contour on frame
        if self.detected_contour is not None:
            cv2.drawContours(frame, [self.detected_contour], -1, (0, 255, 0), 2)
        
        # Convert to QImage for display
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        self.camera_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        self.update()
    
    def detect_shape(self, frame):
        """Detect the largest shape in frame"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply blur and threshold
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Get largest contour by area
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Filter out small contours (noise)
        if cv2.contourArea(largest_contour) < 500:
            return None
        
        # Approximate contour to reduce points
        epsilon = 0.01 * cv2.arcLength(largest_contour, True)
        approx = cv2.approxPolyDP(largest_contour, epsilon, True)
        
        return approx
    
    def get_detected_contour(self):
        """Return the currently detected contour"""
        return self.detected_contour
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        if self.camera_image:
            painter.drawImage(0, 0, self.camera_image)
        else:
            painter.fillRect(self.rect(), QColor(50, 50, 50))
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(self.rect(), Qt.AlignCenter, "Camera Off")


class SurfaceCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.surface_width = 800
        self.surface_height = 600
        self.shape = None
        self.calculated_gap = 10
        self.shapes_positions = []
        self.optimize_packing = False
        
        self.setMinimumSize(self.surface_width, self.surface_height)
        
    def set_surface_size(self, width, height):
        self.surface_width = width
        self.surface_height = height
        self.setMinimumSize(width, height)
        self.calculate_positions()
        self.update()
        
    def set_shape(self, shape):
        self.shape = shape
        self.calculate_positions()
        self.update()
    
    def set_optimize_packing(self, optimize):
        self.optimize_packing = optimize
        self.calculate_positions()
        self.update()
        
    def get_calculated_gap(self):
        return self.calculated_gap
        
    def calculate_positions(self):
        """Calculate optimal positions for shapes"""
        self.shapes_positions = []
        
        if not self.shape:
            return
        
        if self.optimize_packing and self.shape.supports_optimization():
            self.shapes_positions, self.calculated_gap = self.shape.calculate_optimized_layout(
                self.surface_width, self.surface_height
            )
        else:
            self.calculate_standard_positions()
    
    def calculate_standard_positions(self):
        """Standard grid layout with equal gaps"""
        min_gap = 5
        
        cols = max(1, int((self.surface_width - min_gap) / (self.shape.width + min_gap)))
        rows = max(1, int((self.surface_height - min_gap) / (self.shape.height + min_gap)))
        
        if cols > 0:
            gap_x = (self.surface_width - self.shape.width * cols) / (cols + 1)
        else:
            gap_x = 0
            
        if rows > 0:
            gap_y = (self.surface_height - self.shape.height * rows) / (rows + 1)
        else:
            gap_y = 0
        
        self.calculated_gap = (gap_x + gap_y) / 2
        
        for row in range(rows):
            for col in range(cols):
                x = gap_x + col * (self.shape.width + gap_x)
                y = gap_y + row * (self.shape.height + gap_y)
                self.shapes_positions.append((x, y, None))
                
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw surface background
        painter.fillRect(0, 0, self.surface_width, self.surface_height, QColor(240, 240, 240))
        
        # Draw border
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawRect(0, 0, self.surface_width, self.surface_height)
        
        # Draw shapes
        if self.shape and self.shapes_positions:
            painter.setBrush(QBrush(QColor(70, 130, 180)))
            painter.setPen(QPen(QColor(50, 90, 140), 2))
            
            for x, y, direction in self.shapes_positions:
                self.shape.draw(painter, x, y, direction)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shape Spreader - Camera Detection")
        
        # Shape registry
        self.shapes = {
            "Rectangle": RectangleShape,
            "Circle": CircleShape,
            "Triangle": TriangleShape
        }
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        # Canvas
        self.canvas = SurfaceCanvas()
        layout.addWidget(self.canvas, stretch=1)
        
        # Control panel
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls.setMaximumWidth(350)
        
        # Camera widget
        camera_group = QGroupBox("Camera Detection")
        camera_layout = QVBoxLayout()
        
        self.camera_widget = CameraWidget()
        camera_layout.addWidget(self.camera_widget)
        
        camera_btn_layout = QHBoxLayout()
        self.start_camera_btn = QPushButton("Start Camera")
        self.start_camera_btn.clicked.connect(self.start_camera)
        camera_btn_layout.addWidget(self.start_camera_btn)
        
        self.stop_camera_btn = QPushButton("Stop Camera")
        self.stop_camera_btn.clicked.connect(self.stop_camera)
        self.stop_camera_btn.setEnabled(False)
        camera_btn_layout.addWidget(self.stop_camera_btn)
        camera_layout.addLayout(camera_btn_layout)
        
        self.capture_btn = QPushButton("Capture Shape")
        self.capture_btn.clicked.connect(self.capture_shape)
        self.capture_btn.setEnabled(False)
        camera_layout.addWidget(self.capture_btn)
        
        camera_group.setLayout(camera_layout)
        controls_layout.addWidget(camera_group)
        
        # Surface size controls
        surface_group = QGroupBox("Surface Size")
        surface_layout = QVBoxLayout()
        
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Width:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 2000)
        self.width_spin.setValue(800)
        self.width_spin.valueChanged.connect(self.update_surface)
        width_layout.addWidget(self.width_spin)
        surface_layout.addLayout(width_layout)
        
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 2000)
        self.height_spin.setValue(600)
        self.height_spin.valueChanged.connect(self.update_surface)
        height_layout.addWidget(self.height_spin)
        surface_layout.addLayout(height_layout)
        
        surface_group.setLayout(surface_layout)
        controls_layout.addWidget(surface_group)
        
        # Shape size controls
        shape_size_group = QGroupBox("Shape Size")
        shape_size_layout = QVBoxLayout()
        
        sw_layout = QHBoxLayout()
        sw_layout.addWidget(QLabel("Width:"))
        self.shape_w_spin = QSpinBox()
        self.shape_w_spin.setRange(10, 500)
        self.shape_w_spin.setValue(50)
        self.shape_w_spin.valueChanged.connect(self.update_detected_shape)
        sw_layout.addWidget(self.shape_w_spin)
        shape_size_layout.addLayout(sw_layout)
        
        sh_layout = QHBoxLayout()
        sh_layout.addWidget(QLabel("Height:"))
        self.shape_h_spin = QSpinBox()
        self.shape_h_spin.setRange(10, 500)
        self.shape_h_spin.setValue(50)
        self.shape_h_spin.valueChanged.connect(self.update_detected_shape)
        sh_layout.addWidget(self.shape_h_spin)
        shape_size_layout.addLayout(sh_layout)
        
        shape_size_group.setLayout(shape_size_layout)
        controls_layout.addWidget(shape_size_group)
        
        # Optimization option
        self.optimize_check = QCheckBox("Optimize Packing")
        self.optimize_check.setChecked(False)
        self.optimize_check.stateChanged.connect(self.toggle_optimization)
        controls_layout.addWidget(self.optimize_check)
        
        # Manual shape selection
        shape_select_layout = QHBoxLayout()
        shape_select_layout.addWidget(QLabel("Manual Shape:"))
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(list(self.shapes.keys()))
        self.shape_combo.currentTextChanged.connect(self.on_shape_selected)
        shape_select_layout.addWidget(self.shape_combo)
        controls_layout.addLayout(shape_select_layout)
        
        # Info label
        self.info_label = QLabel("Start camera and capture a shape")
        self.info_label.setWordWrap(True)
        controls_layout.addWidget(self.info_label)
        
        controls_layout.addStretch()
        layout.addWidget(controls)
        
        self.current_shape_name = None
        self.detected_shape = None
    
    def start_camera(self):
        self.camera_widget.start_camera()
        self.start_camera_btn.setEnabled(False)
        self.stop_camera_btn.setEnabled(True)
        self.capture_btn.setEnabled(True)
    
    def stop_camera(self):
        self.camera_widget.stop_camera()
        self.start_camera_btn.setEnabled(True)
        self.stop_camera_btn.setEnabled(False)
        self.capture_btn.setEnabled(False)
    
    def capture_shape(self):
        """Capture the detected shape from camera"""
        contour = self.camera_widget.get_detected_contour()
        
        if contour is None:
            self.info_label.setText("No shape detected! Show a clear shape to camera.")
            return
        
        # Create a camera-detected shape
        width = self.shape_w_spin.value()
        height = self.shape_h_spin.value()
        
        self.detected_shape = CameraDetectedShape("Camera Shape", width, height, contour)
        self.current_shape_name = "Camera Shape"
        self.canvas.set_shape(self.detected_shape)
        self.update_info()
    
    def update_detected_shape(self):
        """Update the size of detected shape"""
        if self.detected_shape:
            width = self.shape_w_spin.value()
            height = self.shape_h_spin.value()
            self.detected_shape.width = width
            self.detected_shape.height = height
            self.canvas.set_shape(self.detected_shape)
            self.update_info()
    
    def on_shape_selected(self, shape_name):
        self.current_shape_name = shape_name
        self.detected_shape = None
        shape_class = self.shapes.get(shape_name)
        if shape_class:
            width = self.shape_w_spin.value()
            height = self.shape_h_spin.value()
            shape = shape_class(shape_name, width, height)
            self.canvas.set_shape(shape)
            self.update_info()
        
    def update_surface(self):
        width = self.width_spin.value()
        height = self.height_spin.value()
        self.canvas.set_surface_size(width, height)
        self.update_info()
    
    def toggle_optimization(self):
        self.canvas.set_optimize_packing(self.optimize_check.isChecked())
        self.update_info()
            
    def update_info(self):
        if self.canvas.shape:
            count = len(self.canvas.shapes_positions)
            gap = self.canvas.get_calculated_gap()
            mode = "Optimized" if self.optimize_check.isChecked() else "Standard"
            opt_available = "Yes" if self.canvas.shape.supports_optimization() else "No"
            self.info_label.setText(
                f"Shape: {self.current_shape_name}\n"
                f"Count: {count} shapes\n"
                f"Layout: {mode}\n"
                f"Optimization: {opt_available}\n"
                f"Surface: {self.width_spin.value()}x{self.height_spin.value()}\n"
                f"Shape: {self.shape_w_spin.value()}x{self.shape_h_spin.value()}\n"
                f"Auto Gap: {gap:.1f}px"
            )
    
    def closeEvent(self, event):
        self.camera_widget.stop_camera()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())