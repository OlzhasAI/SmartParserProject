let camera = {
    offset: [0,0],
    zoom: 0.00005,
    mode: "pan"
};

let mouseDown = false;
let lastX = 0;
let lastY = 0;

let LayerGroups = {};   // { "АР": ["АР_Монолит", "АР_Газоблок"], "ОВ": [...], ... }
let layerFilter = "";

window.onload = function() {
    const canvas = document.getElementById("dxfCanvas");
    initWebGL(canvas);

    canvas.addEventListener("mousedown", e => {
        mouseDown = true;
        lastX = e.clientX;
        lastY = e.clientY;
    });

    window.addEventListener("mouseup", () => mouseDown = false);

    window.addEventListener("mousemove", e => {
        if (!mouseDown) return;

        let dx = e.clientX - lastX;
        let dy = e.clientY - lastY;

        lastX = e.clientX;
        lastY = e.clientY;

        if (camera.mode === "pan") {
            camera.offset[0] += dx / 1000;
            camera.offset[1] -= dy / 1000;
        }

        renderScene(camera);
    });

    window.addEventListener("wheel", e => {
        if (camera.mode !== "zoom") return;

        camera.zoom *= (e.deltaY > 0 ? 0.9 : 1.1);
        renderScene(camera);
    });

    // Загрузка DXF JSON
    fetch("http://127.0.0.1:8000/api/plan/last")
        .then(r => r.json())
        .then(dxf => {
            const lines = convertDXFToLines(dxf);
            uploadDXFGeometry(lines);
            renderScene(camera);
        });
};

function setMode(m) {
    camera.mode = m;
}

function resetView() {
    camera.offset = [0,0];
    camera.zoom = 0.00005;
    renderScene(camera);
}

function fitToScreen() {
    camera.zoom = 0.0001;
    renderScene(camera);
}

function toggleLayers() {
    document.getElementById("layersPanel").classList.toggle("hidden");
}

function buildLayersPanel() {
    const list = document.getElementById("layersList");
    list.innerHTML = "";

    Object.keys(LayersDict).forEach(layer => {
        const div = document.createElement("div");

        div.innerHTML = `
            <input type="checkbox" checked onchange="toggleLayer('${layer}')">
            <span>${layer}</span>
            <span style="float:right; color:#888">${LayersDict[layer].count}</span>
        `;

        list.appendChild(div);
    });
}

function toggleLayer(layer) {
    LayersDict[layer].visible = !LayersDict[layer].visible;
    updateGPUBuffer();
    renderScene(camera);
}

fetch("http://127.0.0.1:8000/api/plan/last")
    .then(r => r.json())
    .then(dxf => {
        const lines = convertDXFToLines(dxf);
        uploadDXFGeometry(lines);

        buildLayersPanel();
        renderScene(camera);
    });

    // ГРУППИРУЕМ ПО ПРЕФИКСУ ДО "_" или ДО ПЕРВОЙ ЦИФРЫ
function buildLayerGroups() {
    LayerGroups = {};

    Object.keys(LayersDict).forEach(layerName => {
        let prefix = layerName.split("_")[0];

        if (!LayerGroups[prefix]) LayerGroups[prefix] = [];
        LayerGroups[prefix].push(layerName);
    });
}

function buildLayersPanel() {
    const panel = document.getElementById("layersList");
    panel.innerHTML = "";

    // ---- SEARCH BAR ----
    const search = document.createElement("input");
    search.placeholder = "Поиск по слоям...";
    search.className = "layer-search";
    search.oninput = e => {
        layerFilter = e.target.value.toLowerCase();
        buildLayersPanel();
    };
    panel.appendChild(search);

    // ---- MASTER BUTTONS ----
    const controls = document.createElement("div");
    controls.className = "layer-controls";

    controls.innerHTML = `
        <button onclick="showAllLayers()">Показать все</button>
        <button onclick="hideAllLayers()">Скрыть все</button>
    `;
    panel.appendChild(controls);

    // ---- GROUPS ----
    buildLayerGroups();

    Object.keys(LayerGroups).forEach(group => {
        const wrapper = document.createElement("div");
        wrapper.className = "layer-group";

        const header = document.createElement("div");
        header.className = "group-header";
        header.innerHTML = `<b>${group}</b> (${LayerGroups[group].length})`;
        wrapper.appendChild(header);

        const list = document.createElement("div");
        list.className = "group-content";

        LayerGroups[group].forEach(layer => {
            if (!layer.toLowerCase().includes(layerFilter)) return;

            const item = document.createElement("div");
            item.className = "layer-row";

            const color = LayersDict[layer].color;
            const rgb = `rgb(${color[0]*255},${color[1]*255},${color[2]*255})`;

            item.innerHTML = `
                <input type="checkbox" 
                       ${LayersDict[layer].visible ? "checked" : ""}
                       onchange="toggleLayer('${layer}')">

                <span class="color-box" style="background:${rgb}"></span>

                <span class="layer-name">${layer}</span>

                <span class="count">${LayersDict[layer].count}</span>
            `;

            list.appendChild(item);
        });

        wrapper.appendChild(list);
        panel.appendChild(wrapper);

        // Click group collapse
        header.onclick = () => {
            list.style.display = list.style.display === "none" ? "block" : "none";
        };
    });
}

function showAllLayers() {
    Object.keys(LayersDict).forEach(l => LayersDict[l].visible = true);
    updateGPUBuffer();
    buildLayersPanel();
    renderScene(camera);
}

function hideAllLayers() {
    Object.keys(LayersDict).forEach(l => LayersDict[l].visible = false);
    updateGPUBuffer();
    buildLayersPanel();
    renderScene(camera);
}
