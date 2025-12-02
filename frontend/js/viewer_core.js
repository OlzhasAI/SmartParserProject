let gl;
let shaderProgram;

let lineBuffer = null;
let lineCount = 0;

let GPU_Lines = [];  
// Элемент: { layer, x1,y1,x2,y2 }

function uploadDXFGeometry(lines) {
    GPU_Lines = lines;
    updateGPUBuffer();
}

function updateGPUBuffer() {
    const vertices = [];

    GPU_Lines.forEach(l => {
        if (!LayersDict[l.layer].visible) return;

        vertices.push(
            l.x1, l.y1,
            l.x2, l.y2
        );
    });

    lineCount = vertices.length / 2;

    lineBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, lineBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STATIC_DRAW);
}
