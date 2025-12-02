let LayersDict = {};  // { layerName: { visible: true, color: [r,g,b], count: 0 } }

function randomColor() {
    // Мягкие цвета — стиль Revit Light Theme
    const base = [
        [0.25, 0.25, 0.28],  // тёмно-серый
        [0.35, 0.45, 0.65],  // синий
        [0.65, 0.35, 0.35],  // красный
        [0.35, 0.65, 0.45],  // зелёный
        [0.55, 0.45, 0.25],  // коричневый
        [0.5, 0.5, 0.6],     // стальной
    ];
    return base[Math.floor(Math.random() * base.length)];
}

function initLayer(layerName) {
    if (!LayersDict[layerName]) {
        LayersDict[layerName] = {
            visible: true,
            color: randomColor(),
            count: 0
        };
    }
}

function convertDXFToLines(dxf) {
    console.log("DXF:", dxf);

    const lines = [];

    // 1. Линии (LINE)
    if (dxf?.source_info?.examples?.lines) {
        dxf.source_info.examples.lines.forEach(l => {
            initLayer(l.layer);

            LayersDict[l.layer].count++;

            lines.push({
                layer: l.layer,
                x1: l.start[0],
                y1: l.start[1],
                x2: l.end[0],
                y2: l.end[1]
            });
        });
    }

    // 2. Полилинии (LWPOLYLINE)
    if (dxf?.source_info?.examples?.polylines) {
        dxf.source_info.examples.polylines.forEach(pl => {
            initLayer(pl.layer);

            for (let i = 0; i < pl.points.length - 1; i++) {
                let p1 = pl.points[i];
                let p2 = pl.points[i + 1];

                LayersDict[pl.layer].count++;

                lines.push({
                    layer: pl.layer,
                    x1: p1[0],
                    y1: p1[1],
                    x2: p2[0],
                    y2: p2[1]
                });
            }
        });
    }

    return lines;
}
