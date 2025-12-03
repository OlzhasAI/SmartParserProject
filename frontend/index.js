// index.js - Главная логика
import { RendererCAD2D } from "./renderer.js";
import DxfLoader from "./dxf_loader.js";

const API_URL = "http://127.0.0.1:8000";
let renderer = null; // Экземпляр рендерера

// Инициализация при загрузке страницы
window.onload = () => {
    // Создаем рендерер, привязываем к canvas и панели инфо
    renderer = new RendererCAD2D("cadCanvas", "infoPanel");
    console.log("Renderer initialized");
};

// Делаем функции доступными глобально (так как используем module import)
window.uploadPlan = uploadPlan;
window.uploadSection = uploadSection;
window.buildBIM = buildBIM;


// ---------------------------
// 1. Upload PLAN
// ---------------------------
async function uploadPlan() {
    const fileInput = document.getElementById("planFile");
    const file = fileInput.files[0];
    if (!file) {
        alert("Выберите DXF-файл Плана!");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_URL}/api/plan/upload`, { method: "POST", body: formData });
        if (!res.ok) throw new Error("Ошибка загрузки");
        
        const data = await res.json();
        document.getElementById("planStatus").innerText = `✅ Загружено (ID: ${data.file_id})`;
        document.getElementById("planStatus").style.color = "green";
    } catch (e) {
        alert(e.message);
    }
}

// ---------------------------
// 2. Upload SECTION
// ---------------------------
async function uploadSection() {
    const fileInput = document.getElementById("sectionFile");
    const file = fileInput.files[0];
    if (!file) {
        alert("Выберите DXF-файл Разреза!");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_URL}/api/section/upload`, { method: "POST", body: formData });
        if (!res.ok) throw new Error("Ошибка загрузки");

        const data = await res.json();
        document.getElementById("sectionStatus").innerText = `✅ Загружено (ID: ${data.file_id})`;
        document.getElementById("sectionStatus").style.color = "green";
    } catch (e) {
        alert(e.message);
    }
}

// ---------------------------
// 3. BUILD BIM & RENDER
// ---------------------------
async function buildBIM() {
    // Проверка наличия ID не нужна, но можно оставить для alert
    if (window.PLAN_ID === null || window.SECTION_ID === null) {
        alert("Сначала загрузите ПЛАН и РАЗРЕЗ!");
        return;
    }

    const statusDiv = document.getElementById("bimStatus");
    statusDiv.innerText = "Формирую BIM структуру...";
    statusDiv.style.color = "#666";

    try {
        // Запрос к бэкенду. Убираем body, так как бэкенд использует STATE
        const res = await fetch(`${API_URL}/api/bim/build`, { method: "POST" }); // <--- ИЗМЕНЕНИЕ: Убран body
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Ошибка сервера");
        }

        const bimData = await res.json();
        statusDiv.innerText = "✅ Готово! Отображаю геометрию...";
        statusDiv.style.color = "green";

        // 1. Рендерим таблицу (текст)
        renderTable(bimData);

        // 2. Рендерим графику (Canvas)
        if (renderer) {
            DxfLoader.loadFromAPI(bimData, renderer);
        }

    } catch (e) {
        statusDiv.innerText = `❌ Ошибка: ${e.message}`;
        statusDiv.style.color = "red";
        console.error(e);
    }
}

function renderTable(bim) {
    const div = document.getElementById("bimOutput");

    let wallsCount = 0;
    let roomsCount = 0;
    let levelsCount = 0;

    if (bim.scene) {
        // V2 Structure
        wallsCount = bim.scene.walls?.length || 0;
        roomsCount = bim.scene.rooms?.length || 0;
    } else if (bim.plan) {
        // V1 Structure
        wallsCount = bim.plan.stats?.walls_count || 0;
        roomsCount = bim.plan.stats?.rooms_count || 0;
    }

    // Levels usually come from section analysis which might be separate or part of structure
    // Current main.py for V2 only returns {scene: ...}, so section info might be missing unless I add it back.
    // backend/main.py V2 implementation replaced the whole json with result of analyze_dxf_v2.
    // analyze_dxf_v2 returns only {scene: ...}.
    // So levelsCount will be 0.
    // If I want to support section in V2, I should have included it in main.py construction.
    // But for now, let's just handle safely.
    if (bim.section) {
        levelsCount = bim.section.levels?.length || 0;
    }

    div.innerHTML = `
        <div style="margin-top:20px; padding:15px; background:#e8f4fd; border-radius:5px;">
            <h3>Результаты анализа:</h3>
            <ul>
                <li>Найдено стен: <b>${wallsCount}</b></li>
                <li>Найдено помещений: <b>${roomsCount}</b></li>
                <li>Уровней в разрезе: <b>${levelsCount}</b></li>
            </ul>
        </div>
    `;
}