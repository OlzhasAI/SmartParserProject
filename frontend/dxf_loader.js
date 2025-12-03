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
        if (bimData.scene && bimData.scene.walls) {
            console.log(`Загружено стен (V2): ${bimData.scene.walls.length}`);

            bimData.scene.walls.forEach(wall => {
                renderObjects.push({
                    id: wall.id,
                    layer: "WALLS_V2", // Dummy layer
                    type: 'wall_svg',
                    material: wall.material,
                    render: {
                        svgPath: wall.svgPath,
                        fillColor: wall.color,
                        strokeColor: "#000000",
                        lineWidth: 1
                    }
                });
            });

            // Openings/Rooms placeholder if V2 supported them
            // ...
        }

        // =========================================================
        // LEGACY PLAN (V1)
        // =========================================================
        else if (bimData.plan) {
             // ... Old logic code ...
             // (Keeping it for safety if needed, or replacing?)
             // The prompt says "Update", usually implies replacement or extension.
             // Given I replaced backend entirely to V2, V1 data won't come.
             // But I'll keep the logic if structure matches V1 for resilience.

             if (bimData.plan.walls) {
                bimData.plan.walls.forEach(wall => {
                    if (wall.coordinates && wall.coordinates.length >= 3) {
                         let fillColor = "#999999";
                         switch (wall.material) {
                            case 'concrete': fillColor = "#A9A9A9"; break;
                            case 'brick': fillColor = "#CD5C5C"; break;
                            case 'partition': fillColor = "#D3D3D3"; break;
                         }
                         renderObjects.push({
                            id: wall.id, type: 'wall_polygon',
                            material: wall.material,
                            render: { points: wall.coordinates, fillColor, strokeColor: "#000", lineWidth: 1 }
                         });
                    } else {
                        // lines fallback
                        // ...
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
