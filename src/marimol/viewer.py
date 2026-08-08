import anywidget
import traitlets
import marimo as mo
from .color_utils import resolve_color

class MoleculeViewerWidget(anywidget.AnyWidget):
    _esm = """
    import * as THREE from 'https://esm.sh/three@0.160.0';
    import { OrbitControls } from 'https://esm.sh/three@0.160.0/addons/controls/OrbitControls.js';

    export default {
        render({ model, el }) {
            // Container setup
            const container = document.createElement('div');
            container.style.width = '100%';
            container.style.height = '400px';
            container.style.display = 'block';
            container.style.backgroundColor = model.get('background_color') || '#ffffff';
            container.style.overflow = 'hidden';
            el.appendChild(container);

            // Three.js setup
            const scene = new THREE.Scene();
            
            // Add lighting
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            scene.add(ambientLight);
            const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight.position.set(10, 20, 10);
            scene.add(dirLight);

            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
            
            const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);

            const controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.1;

            // Geometry and Material for Atoms
            // We use a high segment count for smooth spheres, but InstancedMesh keeps it incredibly fast
            const sphereGeometry = new THREE.SphereGeometry(1, 32, 32);
            const sphereMaterial = new THREE.MeshPhongMaterial({ 
                color: 0xffffff,
                shininess: 60
            });
            
            let atomMesh = null; // Will hold the InstancedMesh
            
            // Reusable objects for instancing and raycasting
            const dummy = new THREE.Object3D();
            const colorObj = new THREE.Color();
            const raycaster = new THREE.Raycaster();
            const mouse = new THREE.Vector2();

            function updateScene() {
                const atoms = model.get('atoms') || [];
                const numAtoms = atoms.length;
                
                // Clear old mesh
                if (atomMesh) {
                    scene.remove(atomMesh);
                    atomMesh.dispose();
                    atomMesh = null;
                }

                if (numAtoms === 0) return;

                // Create new InstancedMesh
                atomMesh = new THREE.InstancedMesh(sphereGeometry, sphereMaterial, numAtoms);
                
                let centerSum = new THREE.Vector3(0, 0, 0);

                for (let i = 0; i < numAtoms; i++) {
                    const a = atoms[i];
                    const pos = a.position || [0, 0, 0];
                    const col = a.color || [1, 1, 1];
                    const rad = a.radius || 1.0;

                    // Set position and scale (radius)
                    dummy.position.set(pos[0], pos[1], pos[2]);
                    dummy.scale.set(rad, rad, rad);
                    dummy.updateMatrix();
                    atomMesh.setMatrixAt(i, dummy.matrix);

                    // Set color
                    colorObj.setRGB(col[0], col[1], col[2]);
                    atomMesh.setColorAt(i, colorObj);
                    
                    // Accumulate center
                    centerSum.add(dummy.position);
                }
                
                atomMesh.instanceMatrix.needsUpdate = true;
                if (atomMesh.instanceColor) atomMesh.instanceColor.needsUpdate = true;
                scene.add(atomMesh);

                // Auto-center and fit camera
                centerSum.divideScalar(numAtoms);
                controls.target.copy(centerSum);
                
                let maxDist = 0;
                for (let i = 0; i < numAtoms; i++) {
                    const pos = new THREE.Vector3().fromArray(atoms[i].position);
                    const dist = pos.distanceTo(centerSum);
                    if (dist > maxDist) maxDist = dist;
                }
                
                const cameraDist = Math.max(10, maxDist * 3);
                camera.position.set(centerSum.x, centerSum.y, centerSum.z + cameraDist);
                controls.update();
            }

            // Watch for changes from Python
            model.on("change:atoms", updateScene);
            model.on("change:background_color", () => {
                container.style.backgroundColor = model.get('background_color');
            });
            updateScene();

            // Handle Resize
            const resizeObserver = new ResizeObserver(() => {
                if (container.clientWidth === 0 || container.clientHeight === 0) return;
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            });
            resizeObserver.observe(container);

            // Handle Click (Picking)
            container.addEventListener('click', (event) => {
                const rect = container.getBoundingClientRect();
                mouse.x = ((event.clientX - rect.left) / container.clientWidth) * 2 - 1;
                mouse.y = -((event.clientY - rect.top) / container.clientHeight) * 2 + 1;

                raycaster.setFromCamera(mouse, camera);

                if (atomMesh) {
                    const intersects = raycaster.intersectObject(atomMesh);
                    if (intersects.length > 0) {
                        // The instanceId tells us which atom was clicked
                        const instanceId = intersects[0].instanceId;
                        model.set("selected_atom_index", instanceId);
                        model.save_changes();
                    } else {
                        model.set("selected_atom_index", -1);
                        model.save_changes();
                    }
                }
            });

            // Render Loop
            let animationId;
            function animate() {
                animationId = requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }
            animate();

            // Cleanup when cell is deleted or widget is destroyed
            return () => {
                cancelAnimationFrame(animationId);
                resizeObserver.disconnect();
                if (atomMesh) {
                    atomMesh.dispose();
                    scene.remove(atomMesh);
                }
                renderer.dispose();
            };
        }
    }
    """
    atoms = traitlets.List().tag(sync=True)
    selected_atom_index = traitlets.Int(-1).tag(sync=True)
    background_color = traitlets.Unicode('#ffffff').tag(sync=True)

def view_molecule(atoms, background_color="white"):
    """
    Visualize a list of atoms using WebGL (Three.js).
    atoms format: [{"position": [x, y, z], "color": [r, g, b], "radius": r}, ...]
    """
    resolved_bg = resolve_color(background_color)
    widget = MoleculeViewerWidget(atoms=atoms, background_color=resolved_bg)
    return mo.ui.anywidget(widget)
