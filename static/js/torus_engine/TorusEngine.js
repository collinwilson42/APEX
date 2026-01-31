/**
 * TORUS ENGINE - MAIN COMPONENT
 * WebGL-based toroidal plasma containment field visualization
 * 
 * Represents data circulation through Rodin coil topology (1-2-4-5-7-8)
 * with 3-6-9 magnetic axis governance
 */

class TorusEngine {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`TorusEngine: Container #${containerId} not found`);
            return;
        }
        
        // Scene components
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.torusMesh = null;
        this.particles = [];
        this.nodes = [];
        this.magneticAxis = [];
        
        // Hexadic colors (station mapping)
        this.STATION_COLORS = {
            1: 0xADEBB3,  // Unity - Mint
            2: 0x20B2AA,  // Duality - Teal
            4: 0x6B8DD6,  // Structure - Blue
            5: 0xC084FC,  // Change - Magenta
            7: 0xD4AF37,  // Mystery - Golden
            8: 0xF4E4C1   // Infinity - Light Gold
        };
        
        // Animation state
        this.time = 0;
        this.systemLoad = 0.5;  // 0.0 - 1.0
        this.animationId = null;
        
        // Data state
        this.hexadicData = {
            nodes: [],
            events: [],
            currentAnchor: null
        };
        
        this.init();
    }
    
    init() {
        this.setupScene();
        this.createTorus();
        this.createLighting();
        this.setupControls();
        this.animate();
        this.startDataPolling();
        
        console.log('✓ TorusEngine initialized');
    }
    
    setupScene() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0b0d);
        
        // Camera
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
        this.camera.position.set(0, 5, 10);
        this.camera.lookAt(0, 0, 0);
        
        // Renderer
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true,
            alpha: true
        });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);
        
        // Handle resize
        window.addEventListener('resize', () => this.onWindowResize());
    }
    
    createTorus() {
        // Torus Knot Geometry (Rodin coil shape)
        const geometry = new THREE.TorusKnotGeometry(
            3,      // radius
            1,      // tube
            256,    // tubularSegments (high detail)
            32,     // radialSegments
            2,      // p (twist parameter)
            3       // q (twist parameter)
        );
        
        // Shader Material for Fresnel glow effect
        const material = new THREE.ShaderMaterial({
            uniforms: {
                time: { value: 0 },
                glowColor: { value: new THREE.Color(0xD4AF37) },  // Gold
                glowIntensity: { value: 1.0 },
                systemLoad: { value: 0.5 }
            },
            vertexShader: this.getFresnelVertexShader(),
            fragmentShader: this.getFresnelFragmentShader(),
            transparent: true,
            side: THREE.DoubleSide
        });
        
        this.torusMesh = new THREE.Mesh(geometry, material);
        this.scene.add(this.torusMesh);
    }
    
    getFresnelVertexShader() {
        return `
            varying vec3 vNormal;
            varying vec3 vViewPosition;
            varying vec2 vUv;
            
            void main() {
                vNormal = normalize(normalMatrix * normal);
                vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                vViewPosition = -mvPosition.xyz;
                vUv = uv;
                gl_Position = projectionMatrix * mvPosition;
            }
        `;
    }
    
    getFresnelFragmentShader() {
        return `
            uniform float time;
            uniform vec3 glowColor;
            uniform float glowIntensity;
            uniform float systemLoad;
            
            varying vec3 vNormal;
            varying vec3 vViewPosition;
            varying vec2 vUv;
            
            void main() {
                // Fresnel calculation (rim light)
                vec3 viewDir = normalize(vViewPosition);
                float fresnelTerm = pow(1.0 - abs(dot(viewDir, vNormal)), 3.0);
                
                // Pulsing effect (speed based on systemLoad)
                float pulseSpeed = 2.0 + systemLoad * 3.0;
                float pulse = 0.8 + 0.2 * sin(time * pulseSpeed);
                
                // Edge glow
                vec3 glow = glowColor * fresnelTerm * pulse * glowIntensity;
                
                // Inner transparency (plasma effect)
                float alpha = fresnelTerm * 0.7;
                
                gl_FragColor = vec4(glow, alpha);
            }
        `;
    }
    
    createLighting() {
        // Ambient light
        const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
        this.scene.add(ambientLight);
        
        // Point lights (3 for depth)
        const light1 = new THREE.PointLight(0xADEBB3, 1, 50);  // Mint
        light1.position.set(5, 5, 5);
        this.scene.add(light1);
        
        const light2 = new THREE.PointLight(0x20B2AA, 0.8, 50);  // Teal
        light2.position.set(-5, 3, -5);
        this.scene.add(light2);
        
        const light3 = new THREE.PointLight(0xC084FC, 0.6, 50);  // Magenta
        light3.position.set(0, -5, 5);
        this.scene.add(light3);
    }
    
    setupControls() {
        // Mouse controls for rotation
        let isDragging = false;
        let previousMousePosition = { x: 0, y: 0 };
        
        this.container.addEventListener('mousedown', (e) => {
            isDragging = true;
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });
        
        this.container.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            const deltaX = e.clientX - previousMousePosition.x;
            const deltaY = e.clientY - previousMousePosition.y;
            
            this.torusMesh.rotation.y += deltaX * 0.01;
            this.torusMesh.rotation.x += deltaY * 0.01;
            
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });
        
        this.container.addEventListener('mouseup', () => {
            isDragging = false;
        });
        
        this.container.addEventListener('mouseleave', () => {
            isDragging = false;
        });
    }
    
    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());
        
        this.time += 0.016;  // ~60fps
        
        // Update torus shader uniforms
        if (this.torusMesh && this.torusMesh.material.uniforms) {
            this.torusMesh.material.uniforms.time.value = this.time;
            this.torusMesh.material.uniforms.systemLoad.value = this.systemLoad;
            
            // Breathing animation (scale pulse)
            const breathe = 1.0 + Math.sin(this.time * 0.5) * 0.02;
            this.torusMesh.scale.set(breathe, breathe, breathe);
        }
        
        // Auto-rotate slowly
        if (this.torusMesh) {
            this.torusMesh.rotation.y += 0.001;
        }
        
        this.renderer.render(this.scene, this.camera);
    }
    
    startDataPolling() {
        // Poll hexadic API every second
        setInterval(() => {
            this.fetchHexadicData();
        }, 1000);
        
        // Initial fetch
        this.fetchHexadicData();
    }
    
    async fetchHexadicData() {
        try {
            // Fetch visualization data
            const response = await fetch('/api/metatron/circulation/visualization?limit=200');
            const data = await response.json();
            
            if (data.success) {
                this.hexadicData.events = data.events_by_type || {};
                this.hexadicData.activeStations = data.active_stations || [];
                
                // Update systemLoad based on recent activity
                const totalEvents = Object.values(this.hexadicData.events)
                    .reduce((sum, arr) => sum + arr.length, 0);
                this.systemLoad = Math.min(totalEvents / 100, 1.0);
                
                this.updateVisualization();
            }
        } catch (error) {
            console.warn('TorusEngine: Failed to fetch hexadic data', error);
        }
    }
    
    updateVisualization() {
        // This will be enhanced with particles and nodes
        // For now, just update glow intensity based on activity
        if (this.torusMesh && this.torusMesh.material.uniforms) {
            const intensity = 0.7 + (this.systemLoad * 0.3);
            this.torusMesh.material.uniforms.glowIntensity.value = intensity;
        }
    }
    
    onWindowResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        
        this.renderer.setSize(width, height);
    }
    
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        if (this.renderer) {
            this.renderer.dispose();
            this.container.removeChild(this.renderer.domElement);
        }
        
        console.log('✓ TorusEngine destroyed');
    }
}

// Auto-initialize if torus-canvas exists
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('torus-canvas');
    if (canvas) {
        window.torusEngine = new TorusEngine('torus-canvas');
        console.log('✓ TorusEngine auto-initialized');
    }
});
