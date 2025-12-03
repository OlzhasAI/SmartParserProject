// frontend/renderer.js — V2 HATCH SUPPORT

export class RendererCAD2D {

    constructor(canvasId, infoPanelId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext("2d");

        this.infoPanel = document.getElementById(infoPanelId);

        // Геометрия
        this.objects = [];            
        this.layerVisibility = {};    

        // Камера
        this.offsetX = 0;
        this.offsetY = 0;
        this.scale = 0.00005;

        // Мышь
        this.drag = false;
        this.lastX = 0;
        this.lastY = 0;

        // Ховер
        this.hoveredObject = null;

        this._bindEvents();
        this._autoResize();
        this.requestRender();
    }

    // =============================================================
    // 1. ЗАГРУЗКА И ЦЕНТРИРОВАНИЕ
    // =============================================================
    loadGeometry(objects) {
        this.objects = objects;

        // Кэшируем Path2D объекты для производительности
        this.objects.forEach(obj => {
            if (obj.type === 'wall_svg' && obj.render.svgPath) {
                obj.render.path2d = new Path2D(obj.render.svgPath);
            }
            if (obj.layer && this.layerVisibility[obj.layer] === undefined) {
                this.layerVisibility[obj.layer] = true;
            }
        });

        this.fitToScreen(); 
        this.requestRender();
    }

    fitToScreen() {
        if (!this.objects || this.objects.length === 0) return;
        
        const bounds = this._calculateBounds();
        this._adjustView(bounds);
        this.requestRender();
    }

    _calculateBounds() {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        let hasGeometry = false;

        this.objects.forEach(obj => {
            if (!obj.render) return;

            // V2: SVG Path
            if (obj.type === 'wall_svg' && obj.render.svgPath) {
                // Парсим координаты из SVG строки
                const tokens = obj.render.svgPath.split(/\s+/);
                for (let t of tokens) {
                    const val = parseFloat(t);
                    if (!isNaN(val)) {
                        // Эвристика: SVG path идет парами x y, но сложно понять где X где Y без парсинга команд.
                        // Для bounds просто берем все числа. X и Y перемешаны, но min/max будет верным.
                        // (Если бы мы искали ширину/высоту, это было бы опасно, но для bbox всего облака - ок)
                        // НО: Если есть кривые (Q, C), там контрольные точки. Bounds будет включать контрольные точки.
                        // Это приемлемо для fitToScreen.
                        if (val < minX) minX = val;
                        if (val > maxX) maxX = val;
                        // Проблема: мы не знаем это X или Y.
                        // Предположим, что координаты распределены равномерно.
                        // Для надежности, парсим пары, зная что команды M, L, Q, C имеют структуру.
                        // Но это сложно.
                        // Упрощение: Ищем min/max по всем числам.
                        // Это даст bounding SQUARE (max_coord, max_coord), что может быть неточно, но безопасно (камера захватит все).
                        // Лучше: разделить на четные/нечетные? Нет, команды разной длины.
                        // Оставим "все числа" как грубую оценку.
                        if (val < minY) minY = val; // Временно
                        if (val > maxY) maxY = val;
                    }
                }
                hasGeometry = true;
            }
            // V1: Полигоны
            else if (obj.render.points) {
                obj.render.points.forEach(p => {
                    minX = Math.min(minX, p[0]);
                    minY = Math.min(minY, p[1]);
                    maxX = Math.max(maxX, p[0]);
                    maxY = Math.max(maxY, p[1]);
                });
                hasGeometry = true;
            }
            // V1: Линии
            else if (obj.render.x1 !== undefined) {
                minX = Math.min(minX, obj.render.x1, obj.render.x2);
                minY = Math.min(minY, obj.render.y1, obj.render.y2);
                maxX = Math.max(maxX, obj.render.x1, obj.render.x2);
                maxY = Math.max(maxY, obj.render.y1, obj.render.y2);
                hasGeometry = true;
            }
            // V1: Точки
            else if (obj.render.x !== undefined) {
                minX = Math.min(minX, obj.render.x);
                minY = Math.min(minY, obj.render.y);
                maxX = Math.max(maxX, obj.render.x);
                maxY = Math.max(maxY, obj.render.y);
                hasGeometry = true;
            }
        });
        
        if (!hasGeometry) return { minX: 0, minY: 0, maxX: 100, maxY: 100 };
        return { minX, minY, maxX, maxY };
    }

    _adjustView(bounds) {
        const { minX, minY, maxX, maxY } = bounds;
        
        const worldW = maxX - minX;
        const worldH = maxY - minY;

        const screenW = this.canvas.width;
        const screenH = this.canvas.height;
        
        if (worldW <= 0 || worldH <= 0) return;

        // 1. Рассчитываем масштаб (с запасом 1.1)
        const scaleX = screenW / worldW / 1.1;
        const scaleY = screenH / worldH / 1.1;
        this.scale = Math.min(scaleX, scaleY); 
        
        // 2. Определяем центр мировых координат и экрана
        const centerWorldX = minX + worldW / 2;
        const centerWorldY = minY + worldH / 2;
        
        const centerScreenX_in_WorldUnits = screenW / 2 / this.scale;
        const centerScreenY_in_WorldUnits = screenH / 2 / this.scale;
        
        // 3. Расчет смещения для центрирования
        this.offsetX = centerScreenX_in_WorldUnits - centerWorldX;
        this.offsetY = centerScreenY_in_WorldUnits - centerWorldY;
    }
    // =============================================================
    // 2. УПРАВЛЕНИЕ МЫШЬЮ
    // =============================================================

    _bindEvents() {
        this.canvas.addEventListener('mousedown', (e) => this._onMouseDown(e));
        window.addEventListener('mouseup', (e) => this._onMouseUp(e));
        this.canvas.addEventListener('mousemove', (e) => this._onMouseMove(e));
        this.canvas.addEventListener('wheel', (e) => this._onWheel(e), { passive: false });
    }

    _onMouseDown(e) {
        this.drag = true;
        this.lastX = e.clientX;
        this.lastY = e.clientY;
    }

    _onMouseUp(e) {
        this.drag = false;
    }

    _onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        if (this.drag) {
            const dx = e.clientX - this.lastX;
            const dy = e.clientY - this.lastY;

            this.lastX = e.clientX;
            this.lastY = e.clientY;

            this.offsetX += dx / this.scale;
            this.offsetY -= dy / this.scale;

            this.requestRender();
            return;
        }

        // Hover
        // Для V2 (SVG) нам нужны экранные координаты для isPointInPath с трансформом
        // Для V1 (Polygon) нам нужны мировые
        const wx = mouseX / this.scale - this.offsetX;
        const wy = (this.canvas.height - mouseY) / this.scale - this.offsetY;

        this._checkHover(wx, wy, mouseX, mouseY);
    }

    _checkHover(wx, wy, sx, sy) {
        const hit = this.objects.find(obj => {
            if (this.layerVisibility[obj.layer] === false) return false;

            // V2: SVG Path
            if (obj.type === 'wall_svg' && obj.render.path2d) {
                // Применяем трансформ к контексту временно, чтобы проверить точку
                this.ctx.save();
                this._applyWorldTransform();
                // isPointInPath проверяет точку в ТЕКУЩЕМ трансформе?
                // Документация: "The x and y coordinates ... are in the current coordinate system."
                // Значит если мы применили трансформ, мы должны передавать координаты В ЭТОЙ СИСТЕМЕ (т.е. мировые)?
                // НЕТ. isPointInPath обычно принимает экранные координаты, и проверяет попадают ли они в путь, нарисованный с текущим трансформом.
                // Проверим: "isPointInPath(x, y) ... checks if the point (x, y) is inside the area contained by the path."
                // В большинстве реализаций это "screen space" point vs "transformed path".
                // Попробуем передать SX, SY.
                const isInside = this.ctx.isPointInPath(obj.render.path2d, sx, sy);
                this.ctx.restore();
                return isInside;
            }

            // V1: Polygon
            if (obj.type === 'wall_polygon' && obj.render.points) {
                return this._isPointInPolygon([wx, wy], obj.render.points);
            }
            return false;
        });

        if (hit !== this.hoveredObject) {
            this.hoveredObject = hit;

            if (hit) {
                const mat = hit.material ? hit.material.toUpperCase() : "UNKNOWN";
                const th = hit.thickness ? `Thickness: ${hit.thickness}mm` : "";
                this.infoPanel.innerHTML = `<b>${hit.type}</b><br>Material: ${mat}<br>${th}`;
                this.canvas.style.cursor = "pointer";
            } else {
                this.infoPanel.innerHTML = "Инфо: наведите на объект";
                this.canvas.style.cursor = "crosshair";
            }

            this.requestRender();
        }
    }

    _isPointInPolygon(pt, polygon) {
        const x = pt[0], y = pt[1];
        let inside = false;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i][0], yi = polygon[i][1];
            const xj = polygon[j][0], yj = polygon[j][1];

            const intersect = ((yi > y) !== (yj > y)) &&
                (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    }

    _onWheel(e) {
        e.preventDefault();
        const zoomIntensity = 0.1;
        const delta = e.deltaY < 0 ? (1 + zoomIntensity) : (1 - zoomIntensity);

        const rect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const wx = mouseX / this.scale - this.offsetX;
        const wy = (this.canvas.height - mouseY) / this.scale - this.offsetY;

        this.scale *= delta;

        this.offsetX = mouseX / this.scale - wx;
        this.offsetY = (this.canvas.height - mouseY) / this.scale - wy;

        this.requestRender();
    }

    // =============================================================
    // 3. ОТРИСОВКА
    // =============================================================
    
    worldToScreen(wx, wy) {
        return {
            sx: (wx + this.offsetX) * this.scale,
            sy: this.canvas.height - (wy + this.offsetY) * this.scale 
        };
    }

    _applyWorldTransform() {
        // Устанавливает матрицу трансформации Canvas, чтобы рисовать в мировых координатах
        // sx = (wx + offX) * sc = wx*sc + offX*sc
        // sy = H - (wy + offY) * sc = -wy*sc + (H - offY*sc)

        const sc = this.scale;
        const tx = this.offsetX * sc;
        const ty = this.canvas.height - this.offsetY * sc;

        // setTransform(h_scale, v_skew, h_skew, v_scale, h_trans, v_trans)
        this.ctx.setTransform(sc, 0, 0, -sc, tx, ty);
    }

    render() {
        // Сброс трансформации для очистки
        this.ctx.setTransform(1, 0, 0, 1, 0, 0);
        this.ctx.fillStyle = "#fff"; 
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        if (this.objects) {
            this.objects.forEach(obj => {
                if (this.layerVisibility[obj.layer] === false) return;
                this._drawEntity(obj);
            });
        }
    }
    
    _drawEntity(obj) {
        // --- V2: SVG WALLS ---
        if (obj.type === 'wall_svg' && obj.render.path2d) {
            this.ctx.save();
            this._applyWorldTransform(); // Переходим в мировые координаты

            // Fill
            if (this.hoveredObject === obj) {
                this.ctx.fillStyle = "#ffff00";
            } else {
                this.ctx.fillStyle = obj.render.fillColor || "#999";
            }
            this.ctx.fill(obj.render.path2d);

            // Stroke (Non-scaling width emulation)
            // Чтобы толщина линии не менялась при зуме, нужно делить на scale
            this.ctx.strokeStyle = obj.render.strokeColor || "#000";
            this.ctx.lineWidth = (obj.render.lineWidth || 1) / this.scale;
            this.ctx.stroke(obj.render.path2d);

            this.ctx.restore();
            return;
        }

        // --- V1: POLYGONS ---
        if (obj.type === 'wall_polygon') {
             const { points, fillColor, strokeColor, lineWidth } = obj.render;
             if (!points || points.length < 2) return;

             this.ctx.setTransform(1, 0, 0, 1, 0, 0); // Рисуем в экранных (ручная проекция)
             this.ctx.beginPath();
             const start = this.worldToScreen(points[0][0], points[0][1]);
             this.ctx.moveTo(start.sx, start.sy);

             for (let i = 1; i < points.length; i++) {
                 const p = this.worldToScreen(points[i][0], points[i][1]);
                 this.ctx.lineTo(p.sx, p.sy);
             }
             this.ctx.closePath();

             if (this.hoveredObject === obj) {
                 this.ctx.fillStyle = "#ffff00";
             } else {
                 this.ctx.fillStyle = fillColor || "#999";
             }
             this.ctx.fill();

             this.ctx.strokeStyle = strokeColor || "#000";
             this.ctx.lineWidth = lineWidth || 1;
             this.ctx.stroke();
             return;
        }

        // --- V1: OPENINGS & LINES ---
        // Рисуем в экранных координатах
        this.ctx.setTransform(1, 0, 0, 1, 0, 0);

        if (obj.type === 'opening') {
            const { x, y, width, height, rotation, color } = obj.render;
            if (x === undefined) return;

            const screenPos = this.worldToScreen(x, y);
            this.ctx.save();
            this.ctx.translate(screenPos.sx, screenPos.sy);
            this.ctx.rotate(-rotation * Math.PI / 180);
            
            const w_final = Math.max(width * 1000 * this.scale, 3);
            const h_final = Math.max(height * 1000 * this.scale, 3);
            
            this.ctx.fillStyle = color || "#00aaff";
            this.ctx.fillRect(-w_final / 2, -h_final / 2, w_final, h_final);
            this.ctx.restore();
            return;
        }
        
        // Lines
        const { x1, y1, x2, y2, color, lineWidth } = obj.render;
        if (x1 !== undefined) {
            const p1 = this.worldToScreen(x1, y1);
            const p2 = this.worldToScreen(x2, y2);
            this.ctx.beginPath();
            this.ctx.strokeStyle = color || "#000"; 
            this.ctx.lineWidth = (lineWidth || 1); 
            this.ctx.moveTo(p1.sx, p1.sy);
            this.ctx.lineTo(p2.sx, p2.sy);
            this.ctx.stroke();
        }
    }

    requestRender() {
        if (this.renderRequest) cancelAnimationFrame(this.renderRequest);
        this.renderRequest = requestAnimationFrame(() => this.render());
    }
    
    updateLayerVisibility(layer, visible) {
        this.layerVisibility[layer] = visible;
        this.requestRender();
    }
    
    _autoResize() {
        const resize = () => {
            if (!this.canvas) return;
            this.canvas.width = this.canvas.clientWidth;
            this.canvas.height = this.canvas.clientHeight;
            this.requestRender();
        };
        window.addEventListener("resize", resize);
        resize();
    }
}
