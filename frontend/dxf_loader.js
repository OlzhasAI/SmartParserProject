// frontend/dxf_loader.js

export default class DxfLoader {
    static loadFromAPI(bimData, renderer) {
        if (!bimData) {
            console.warn("Нет данных в ответе API");
            return;
        }

        const renderObjects = [];

        // =========================================================
        // SCENE V2 (HATCH-BASED)
        // =========================================================
        if (bimData.plan.walls) {
            console.log(`Загружено стен из API: ${bimData.plan.walls.length}`);

            bimData.plan.walls.forEach(wall => {

                // --- ЛОГИКА SMART WALLS (ПОЛИГОНЫ) ---
                if (wall.coordinates && wall.coordinates.length >= 3) {

                    // Определяем цвет заливки по материалу
                    let fillColor = "#999999"; // Default Gray
                    let strokeColor = "#000000";

                    switch (wall.material) {
                        case 'concrete':
                            fillColor = "#A9A9A9"; // Dark Gray
                            break;
                        case 'brick':
                            fillColor = "#CD5C5C"; // Reddish
                            break;
                        case 'partition':
                            fillColor = "#D3D3D3"; // Light Gray
                            strokeColor = "#444444";
                            break;
                    }

                    renderObjects.push({
                        id: wall.id,
                        layer: wall.layer || "WALLS",
                        type: 'wall_polygon', // Новый тип для полигонов
                        material: wall.material,
                        thickness: wall.thickness,
                        render: {
                            points: wall.coordinates, // [[x,y], [x,y], ...]
                            fillColor: fillColor,
                            strokeColor: strokeColor,
                            lineWidth: 1
                        }
                    });

                } else {
                    // --- FALLBACK: ЛИНЕЙНЫЕ СТЕНЫ ---
                    let p1, p2;

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
                        type: 'wall_line',
                        render: {
                            x1: p1[0],
                            y1: p1[1],
                            x2: p2[0],
                            y2: p2[1],
                            color: "#000000",
                            lineWidth: 2
                        }
                    });
                }
            });

            // Openings/Rooms placeholder if V2 supported them
            // ...
        }

        // =========================================================
        // 3. ОБРАБОТКА ДВЕРЕЙ И ОКОН (Openings)
        // =========================================================
        if (bimData.plan.openings) {
            console.log(`Загружено проемов: ${bimData.plan.openings.length}`);
            
            bimData.plan.openings.forEach(op => {
                const color = op.type === 'window' ? '#00aaff' : '#8B4513';
                
                renderObjects.push({
                    id: op.id,
                    layer: op.layer || "OPENINGS",
                    type: 'opening',
                    render: {
                        x: op.position[0],
                        y: op.position[1],
                        width: op.width,
                        height: 0.2,
                        rotation: op.rotation,
                        color: color
                    }
                });
             }
             if (bimData.plan.openings) {
                 bimData.plan.openings.forEach(op => {
                     const color = op.type === 'window' ? '#00aaff' : '#8B4513';
                     renderObjects.push({
                         id: op.id, type: 'opening',
                         render: { x: op.position[0], y: op.position[1], width: op.width, height: 0.2, rotation: op.rotation, color }
                     });
                 });
             }
        }

        // =========================================================
        // 4. ОТПРАВКА В РЕНДЕРЕР
        // =========================================================
        renderer.loadGeometry(renderObjects);
    }
}
