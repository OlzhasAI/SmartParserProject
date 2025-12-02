// CAD Core Engine
// Создаёт сцену, камеру, WebGLRenderer и Canvas Overlay

let cadEngine = {
    scene: null,
    camera: null,
    renderer: null,
    canvas: null,
    ctx: null,

    width: 0,
    height: 0,

    init() {
        this.canvas = document.getElementById("cad-canvas");
        this.ctx = this.canvas.getContext("2d");

        this.resize();

        // THREE.js сцена
        this.scene = new THREE.Scene();
        this.camera = new THREE.OrthographicCamera(
            this.width / -2,
            this.width / 2,
            this.height / 2,
            this.height / -2,
            0.1,
            10000
        );
        this.camera.position.set(0, 0, 100);
        this.camera.lookAt(0, 0, 0);

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(this.width, this.height);

        // Привязываем WebGL поверх Canvas
        const viewer = document.getElementById("viewer-container");
        viewer.appendChild(this.renderer.domElement);

        this.animate();
    },

    animate() {
        requestAnimationFrame(() => this.animate());
        this.renderer.render(this.scene, this.camera);
    },

    resize() {
        this.width = window.innerWidth - 260;
        this.height = window.innerHeight - 40;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
    }
};

window.addEventListener("load", () => cadEngine.init());
window.addEventListener("resize", () => cadEngine.resize());
