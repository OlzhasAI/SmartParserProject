// frontend/dxf_loader.js

export default class DxfLoader {
    static loadFromAPI(bimData, renderer) {
        // 1. Проверка входящих данных
        if (!bimData || !bimData.plan) {
            console.warn("Нет данных плана в ответе API");
            return;
        }

        const renderObjects = [];

        // =========================================================
        // 2. ОБРАБОТКА СТЕН (Walls)
        // =========================================================
        if (bimData.plan.walls) {
            console.log(`Загружено стен из API: ${bimData.plan.walls.length}`);

            bimData.plan.walls.forEach(wall => {
                let p1, p2;

                // Проверяем формат координат
                if (wall.start && wall.end) {
                    p1 = wall.start;
                    p2 = wall.end;
                } else if (wall.geometry && wall.geometry.points) {
                    p1 = wall.geometry.points[0];
                    p2 = wall.geometry.points[1];
                } else {
                    return;
                }

                renderObjects.push({
                    id: wall.id,
                    layer: wall.layer || "WALLS",
                    type: 'wall',
                    render: {
                        x1: p1[0],
                        y1: p1[1],
                        x2: p2[0],
                        y2: p2[1],
                        color: "#000000",
                        lineWidth: 2
                    }
                });
            });
        }

        // =========================================================
        // 3. ОБРАБОТКА ДВЕРЕЙ И ОКОН (Openings) — НОВОЕ!
        // =========================================================
        // Мы вставляем это ПЕРЕД отправкой данных в рендерер
        if (bimData.plan.openings) {
            console.log(`Загружено проемов: ${bimData.plan.openings.length}`);
            
            bimData.plan.openings.forEach(op => {
                // Выбираем цвет: Окна - синие, Двери - коричневые
                const color = op.type === 'window' ? '#00aaff' : '#8B4513';
                
                renderObjects.push({
                    id: op.id,
                    layer: op.layer || "OPENINGS",
                    type: 'opening', // Специальный тип для рендерера
                    render: {
                        // Позиция центра блока
                        x: op.position[0],
                        y: op.position[1],
                        // Размеры
                        width: op.width,
                        height: 0.2,           // Визуальная толщина на плане
                        rotation: op.rotation, // Угол поворота
                        color: color
                    }
                });
            });
        }

        // =========================================================
        // 4. ОТПРАВКА В РЕНДЕРЕР
        // =========================================================
        // Отправляем полный список (стены + проемы) на отрисовку
        renderer.loadGeometry(renderObjects);
    }
}