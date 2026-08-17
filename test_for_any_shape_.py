import sys
import math
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QSpinBox, QGroupBox, 
                               QCheckBox, QLineEdit, QComboBox, QPushButton as QBtn)
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QPolygonF


class Shape:
    """Base class for all shapes"""
    def __init__(self, name, width, height):
        self.name = name
        self.width = width
        self.height = height
    
    def draw(self, painter, x, y, direction=None):
        """Override in subclasses to draw the shape"""
        pass
    
    def calculate_optimized_layout(self, surface_width, surface_height, min_gap=5):
        """
        Override this method to provide custom optimization for your shape.
        Returns: (positions_list, calculated_gap)
        where positions_list = [(x, y, direction), ...]
        
        Default implementation uses hexagonal packing with offset rows.
        """
        # Calculate columns for even rows
        cols_even = max(1, int((surface_width - min_gap) / (self.width + min_gap)))
        
        # Get packing efficiency factor
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
        
        # Hexagonal packing pattern
        for row in range(rows):
            if row % 2 == 0:
                cols = cols_even
                x_offset = gap_x
            else:
                cols = cols_even
                x_offset = gap_x + (self.width + gap_x) / 2
                
                # Check if offset row fits
                last_x = x_offset + (cols - 1) * (self.width + gap_x) + self.width
                if last_x > surface_width - gap_x:
                    cols = max(0, cols - 1)
            
            for col in range(cols):
                x = x_offset + col * (self.width + gap_x)
                y = gap_y + row * (row_spacing + gap_y)
                positions.append((x, y, None))
        
        return positions, calculated_gap
    
    def get_packing_efficiency(self):
        """
        Return vertical packing efficiency factor.
        1.0 = no optimization (full height spacing)
        0.866 = hexagonal packing (good for circles)
        Override for custom efficiency
        """
        return 0.866
    
    def supports_optimization(self):
        """Whether this shape benefits from optimization"""
        return True


class RectangleShape(Shape):
    def draw(self, painter, x, y, direction=None):
        painter.drawRect(int(x), int(y), self.width, self.height)
    
    def supports_optimization(self):
        return False  # Grid is already optimal for rectangles


class CircleShape(Shape):
    def draw(self, painter, x, y, direction=None):
        painter.drawEllipse(int(x), int(y), self.width, self.height)
    
    def get_packing_efficiency(self):
        return 0.866  # Hexagonal packing is optimal for circles


class TriangleShape(Shape):
    def draw(self, painter, x, y, direction=None):
        from PySide6.QtCore import QPoint
        if direction == "down":
            # Inverted triangle
            points = [
                QPoint(int(x), int(y)),
                QPoint(int(x + self.width), int(y)),
                QPoint(int(x + self.width / 2), int(y + self.height))
            ]
        else:
            # Upright triangle
            points = [
                QPoint(int(x + self.width / 2), int(y)),
                QPoint(int(x), int(y + self.height)),
                QPoint(int(x + self.width), int(y + self.height))
            ]
        painter.drawPolygon(points)
    
    def calculate_optimized_layout(self, surface_width, surface_height, min_gap=5):
        """Custom tessellation for triangles with up/down alternation"""
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
        
        # Generate triangles in tessellation pattern
        for row in range(rows):
            y = gap_y + row * (triangle_pair_height + gap_y)
            
            # Add upright triangles
            for col in range(cols):
                x = gap_x + col * (self.width + gap_x)
                positions.append((x, y, "up"))
                
            # Add inverted triangles in the gaps
            if cols > 1:
                for col in range(cols - 1):
                    x = gap_x + col * (self.width + gap_x) + (self.width + gap_x) / 2
                    positions.append((x, y, "down"))
        
        return positions, calculated_gap


class HexagonShape(Shape):
    def draw(self, painter, x, y, direction=None):
        from PySide6.QtCore import QPointF
        # Regular hexagon (flat top)
        cx = x + self.width / 2
        cy = y + self.height / 2
        points = []
        for i in range(6):
            angle = math.pi / 3 * i
            px = cx + (self.width / 2) * math.cos(angle)
            py = cy + (self.height / 2) * math.sin(angle)
            points.append(QPointF(px, py))
        painter.drawPolygon(points)
    
    def get_packing_efficiency(self):
        return 0.75  # Hexagons pack very efficiently


class StarShape(Shape):
    def draw(self, painter, x, y, direction=None):
        from PySide6.QtCore import QPointF
        cx = x + self.width / 2
        cy = y + self.height / 2
        points = []
        for i in range(10):
            angle = (math.pi * 2 / 10) * i - math.pi / 2
            if i % 2 == 0:
                # Outer point
                r = min(self.width, self.height) / 2
            else:
                # Inner point
                r = min(self.width, self.height) / 4
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            points.append(QPointF(px, py))
        painter.drawPolygon(points)
    
    def get_packing_efficiency(self):
        return 0.85  # Stars have protruding points, less efficient packing


class DiamondShape(Shape):
    def draw(self, painter, x, y, direction=None):
        from PySide6.QtCore import QPoint
        cx = x + self.width / 2
        cy = y + self.height / 2
        points = [
            QPoint(int(cx), int(y)),  # Top
            QPoint(int(x + self.width), int(cy)),  # Right
            QPoint(int(cx), int(y + self.height)),  # Bottom
            QPoint(int(x), int(cy))  # Left
        ]
        painter.drawPolygon(points)
    
    def calculate_optimized_layout(self, surface_width, surface_height, min_gap=5):
        """Diamonds can tessellate by rotating alternate rows"""
        cols = max(1, int((surface_width - min_gap) / (self.width + min_gap)))
        
        # Diamonds can nest vertically by 50%
        effective_height = self.height * 0.5
        rows = max(1, int((surface_height - min_gap) / (effective_height + min_gap)))
        
        if cols > 0:
            gap_x = (surface_width - self.width * cols) / (cols + 1)
        else:
            gap_x = 0
            
        if rows > 0:
            gap_y = (surface_height - effective_height * rows) / (rows + 1)
        else:
            gap_y = 0
        
        calculated_gap = (gap_x + gap_y) / 2
        positions = []
        
        for row in range(rows):
            # Alternate rows offset horizontally
            if row % 2 == 0:
                x_offset = gap_x
                cols_in_row = cols
            else:
                x_offset = gap_x + (self.width + gap_x) / 2
                cols_in_row = cols
                # Check if offset row fits
                last_x = x_offset + (cols_in_row - 1) * (self.width + gap_x) + self.width
                if last_x > surface_width - gap_x:
                    cols_in_row = max(0, cols_in_row - 1)
            
            for col in range(cols_in_row):
                x = x_offset + col * (self.width + gap_x)
                y = gap_y + row * (effective_height + gap_y)
                positions.append((x, y, None))
        
        return positions, calculated_gap


class PentagonShape(Shape):
    def draw(self, painter, x, y, direction=None):
        from PySide6.QtCore import QPointF
        cx = x + self.width / 2
        cy = y + self.height / 2
        points = []
        for i in range(5):
            angle = (math.pi * 2 / 5) * i - math.pi / 2
            px = cx + (self.width / 2) * math.cos(angle)
            py = cy + (self.height / 2) * math.sin(angle)
            points.append(QPointF(px, py))
        painter.drawPolygon(points)
    
    def get_packing_efficiency(self):
        return 0.88  # Pentagons pack reasonably well


class CustomPolygonShape(Shape):
    """Custom shape defined by user points"""
    def __init__(self, name, width, height, points_str):
        super().__init__(name, width, height)
        self.parse_points(points_str)
    
    def parse_points(self, points_str):
        """Parse points from string like '0,0 50,0 25,50' (x,y pairs)"""
        self.points = []
        try:
            pairs = points_str.strip().split()
            for pair in pairs:
                x, y = pair.split(',')
                self.points.append((float(x), float(y)))
        except:
            # Default to triangle if parsing fails
            self.points = [(25, 0), (0, 50), (50, 50)]
    
    def draw(self, painter, x, y, direction=None):
        from PySide6.QtCore import QPointF
        if not self.points:
            return
        
        # Find bounds of original points
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        orig_w = max_x - min_x
        orig_h = max_y - min_y
        
        # Scale and translate points
        scaled_points = []
        for px, py in self.points:
            # Normalize to 0-1 range
            norm_x = (px - min_x) / orig_w if orig_w > 0 else 0
            norm_y = (py - min_y) / orig_h if orig_h > 0 else 0
            # Scale to target size
            scaled_x = x + norm_x * self.width
            scaled_y = y + norm_y * self.height
            scaled_points.append(QPointF(scaled_x, scaled_y))
        
        painter.drawPolygon(scaled_points)
    
    def get_packing_efficiency(self):
        return 0.85  # Default moderate packing for custom shapes


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
            # Use shape's custom optimization
            self.shapes_positions, self.calculated_gap = self.shape.calculate_optimized_layout(
                self.surface_width, self.surface_height
            )
        else:
            # Use standard grid layout
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
        self.setWindowTitle("Shape Spreader - Universal")
        
        # Shape registry
        self.shapes = {
            "Rectangle": RectangleShape,
            "Circle": CircleShape,
            "Triangle": TriangleShape,
            "Hexagon": HexagonShape,
            "Diamond": DiamondShape,
            "Pentagon": PentagonShape,
            "Star": StarShape
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
        self.shape_w_spin.valueChanged.connect(self.update_shape)
        sw_layout.addWidget(self.shape_w_spin)
        shape_size_layout.addLayout(sw_layout)
        
        sh_layout = QHBoxLayout()
        sh_layout.addWidget(QLabel("Height:"))
        self.shape_h_spin = QSpinBox()
        self.shape_h_spin.setRange(10, 500)
        self.shape_h_spin.setValue(50)
        self.shape_h_spin.valueChanged.connect(self.update_shape)
        sh_layout.addWidget(self.shape_h_spin)
        shape_size_layout.addLayout(sh_layout)
        
        shape_size_group.setLayout(shape_size_layout)
        controls_layout.addWidget(shape_size_group)
        
        # Optimization option
        self.optimize_check = QCheckBox("Optimize Packing")
        self.optimize_check.setChecked(False)
        self.optimize_check.stateChanged.connect(self.toggle_optimization)
        controls_layout.addWidget(self.optimize_check)
        
        # Shape selection dropdown
        shape_select_layout = QHBoxLayout()
        shape_select_layout.addWidget(QLabel("Shape Type:"))
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(list(self.shapes.keys()))
        self.shape_combo.currentTextChanged.connect(self.on_shape_selected)
        shape_select_layout.addWidget(self.shape_combo)
        controls_layout.addLayout(shape_select_layout)
        
        # Custom polygon input
        custom_group = QGroupBox("Custom Polygon (Optional)")
        custom_layout = QVBoxLayout()
        custom_layout.addWidget(QLabel("Points (x,y pairs):"))
        self.custom_points = QLineEdit()
        self.custom_points.setPlaceholderText("e.g., 25,0 50,50 0,50")
        custom_layout.addWidget(self.custom_points)
        
        self.custom_btn = QPushButton("Create Custom Shape")
        self.custom_btn.clicked.connect(self.create_custom_shape)
        custom_layout.addWidget(self.custom_btn)
        custom_group.setLayout(custom_layout)
        controls_layout.addWidget(custom_group)
        
        # Info label
        self.info_label = QLabel("Select a shape to begin")
        self.info_label.setWordWrap(True)
        controls_layout.addWidget(self.info_label)
        
        controls_layout.addStretch()
        layout.addWidget(controls)
        
        self.current_shape_name = None
        
    def on_shape_selected(self, shape_name):
        self.current_shape_name = shape_name
        self.update_shape()
        
    def create_custom_shape(self):
        points_str = self.custom_points.text().strip()
        if points_str:
            self.current_shape_name = "Custom"
            width = self.shape_w_spin.value()
            height = self.shape_h_spin.value()
            shape = CustomPolygonShape("Custom", width, height, points_str)
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
        
    def update_shape(self):
        if self.current_shape_name and self.current_shape_name != "Custom":
            shape_class = self.shapes.get(self.current_shape_name)
            if shape_class:
                width = self.shape_w_spin.value()
                height = self.shape_h_spin.value()
                shape = shape_class(self.current_shape_name, width, height)
                self.canvas.set_shape(shape)
                self.update_info()
            
    def update_info(self):
        if self.canvas.shape:
            count = len(self.canvas.shapes_positions)
            gap = self.canvas.get_calculated_gap()
            mode = "Optimized" if self.optimize_check.isChecked() else "Standard"
            opt_available = "Yes" if self.canvas.shape.supports_optimization() else "No (Already Optimal)"
            self.info_label.setText(
                f"Shape: {self.current_shape_name}\n"
                f"Count: {count} shapes\n"
                f"Layout: {mode}\n"
                f"Optimization Available: {opt_available}\n"
                f"Surface: {self.width_spin.value()}x{self.height_spin.value()}\n"
                f"Shape: {self.shape_w_spin.value()}x{self.shape_h_spin.value()}\n"
                f"Auto Gap: {gap:.1f}px"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())