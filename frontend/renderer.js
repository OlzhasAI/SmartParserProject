// frontend/renderer.js — ФИНАЛЬНАЯ ВЕРСИЯ С ФИКСИРОВАННОЙ ВИДИМОСТЬЮ

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

        this._bindEvents();
        this._autoResize();
        this.requestRender();
    }

    // =============================================================
    // 1. ЗАГРУЗКА И ЦЕНТРИРОВАНИЕ
    // =============================================================
    loadGeometry(objects) {
        this.objects = objects;

        this.objects.forEach(obj => {
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
            if (obj.render) {
                // Включаем в границы как стены, так и проемы (по их точке вставки)
                if (obj.render.x1 !== undefined) {
                    minX = Math.min(minX, obj.render.x1, obj.render.x2);
                    minY = Math.min(minY, obj.render.y1, obj.render.y2);
                    maxX = Math.max(maxX, obj.render.x1, obj.render.x2);
                    maxY = Math.max(maxY, obj.render.y1, obj.render.y2);
                    hasGeometry = true;
                } else if (obj.render.x !== undefined) {
                    minX = Math.min(minX, obj.render.x);
                    minY = Math.min(minY, obj.render.y);
                    maxX = Math.max(maxX, obj.render.x);
                    maxY = Math.max(maxY, obj.render.y);
                    hasGeometry = true;
                }
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
        if (!this.drag) return;

        const dx = e.clientX - this.lastX;
        const dy = e.clientY - this.lastY;

        this.lastX = e.clientX;
        this.lastY = e.clientY;

        this.offsetX += dx / this.scale;
        this.offsetY -= dy / this.scale; 

        this.requestRender();
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

    render() {
        this.ctx.fillStyle = "#fff"; 
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        if (this.objects) {
            this.objects.forEach(obj => {
                if (this.layerVisibility[obj.layer] === false) return;
                if (obj.render) this._drawEntity(obj);
            });
        }
    }
    
    _drawEntity(obj) {
        // --- 1. РИСОВАНИЕ ПРОЕМОВ (ДВЕРИ/ОКНА) ---
        if (obj.type === 'opening') {
            const { x, y, width, height, rotation, color } = obj.render;
            if (x === undefined) return;

            const screenPos = this.worldToScreen(x, y);
            
            this.ctx.save();
            
            this.ctx.translate(screenPos.sx, screenPos.sy);
            this.ctx.rotate(-rotation * Math.PI / 180);
            
            // ИСПРАВЛЕНИЕ: Умножаем на 1000 (метры -> мм) и гарантируем минимальный размер
            const w_world_units = width * 1000;
            const h_world_units = height * 1000; 
            
            // Рассчитанный размер в пикселях
            const w_scaled = w_world_units * this.scale;
            const h_scaled = h_world_units * this.scale;
            
            // Если размер меньше 3 пикселей, делаем его 3 пикселя для видимости
            const MIN_VISIBLE_PIXELS = 3; 

            const w_final = Math.max(w_scaled, MIN_VISIBLE_PIXELS);
            const h_final = Math.max(h_scaled, MIN_VISIBLE_PIXELS);
            
            this.ctx.fillStyle = color || "#00aaff";
            
            // Рисуем прямоугольник с центром в точке (0,0)
            this.ctx.fillRect(-w_final / 2, -h_final / 2, w_final, h_final);
            
            this.ctx.restore();
            return;
        }

        // --- 2. РИСОВАНИЕ СТЕН (ЛИНИИ) ---
        const { x1, y1, x2, y2, color, lineWidth } = obj.render;
        
        if (x1 !== undefined && y1 !== undefined) {
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